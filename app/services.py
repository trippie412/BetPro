"""Business logic services layer."""
import random
import base64
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import requests
from flask import current_app
from app import db
from app.models import (User, Wallet, WalletTransaction, Deposit, Withdrawal, Bet,
                        BetSelection, Match, Odds, Bonus, Notification, AuditLog,
                        Announcement, SystemSettings, Sport, League, AdminLog)
from app.constants import *

logger = logging.getLogger(__name__)


# =============================================================================
# MPESA ERROR
# =============================================================================

class MpesaError(Exception):
    """Custom exception for M-Pesa API errors."""
    pass


# =============================================================================
# WALLET SERVICE
# =============================================================================

class WalletService:
    """Handle wallet operations."""

    @staticmethod
    def get_or_create_wallet(user):
        if user.wallet:
            return user.wallet
        wallet = Wallet(user_id=user.id, balance=0.0, bonus_balance=0.0)
        db.session.add(wallet)
        db.session.commit()
        return wallet

    @staticmethod
    def add_funds(user, amount, description='Deposit', transaction_type=TRANSACTION_DEPOSIT):
        wallet = WalletService.get_or_create_wallet(user)
        balance_before = wallet.balance
        wallet.add_balance(amount)
        db.session.commit()

        txn = WalletTransaction(
            user_id=user.id, transaction_type=transaction_type,
            amount=amount, balance_before=balance_before,
            balance_after=wallet.balance, description=description,
            status=TRANSACTION_COMPLETED
        )
        db.session.add(txn)
        db.session.commit()
        return txn

    @staticmethod
    def add_bonus(user, amount, description='Bonus Awarded'):
        wallet = WalletService.get_or_create_wallet(user)
        balance_before = wallet.bonus_balance
        wallet.add_bonus(amount)
        db.session.commit()

        txn = WalletTransaction(
            user_id=user.id, transaction_type=TRANSACTION_BONUS,
            amount=amount, balance_before=balance_before,
            balance_after=wallet.bonus_balance, description=description,
            status=TRANSACTION_COMPLETED
        )
        db.session.add(txn)
        db.session.commit()
        return txn

    @staticmethod
    def deduct_funds(user, amount, description='Bet Placed', from_bonus=False):
        wallet = WalletService.get_or_create_wallet(user)
        balance_before = wallet.balance
        bonus_before = wallet.bonus_balance

        if from_bonus:
            if not wallet.deduct_balance(amount, from_bonus=True):
                return None
        else:
            if not wallet.deduct_balance(amount):
                return None

        db.session.commit()

        txn = WalletTransaction(
            user_id=user.id, transaction_type=TRANSACTION_BET_PLACED,
            amount=amount, balance_before=balance_before,
            balance_after=wallet.balance, description=description,
            status=TRANSACTION_COMPLETED
        )
        db.session.add(txn)
        db.session.commit()
        return txn


# =============================================================================
# BONUS SERVICE
# =============================================================================

class BonusService:
    """Handle bonus operations."""

    @staticmethod
    def check_welcome_bonus(user, deposit_amount):
        wallet = WalletService.get_or_create_wallet(user)
        if wallet.welcome_bonus_claimed:
            return False, 'Welcome bonus already claimed'

        min_deposit = current_app.config.get('WELCOME_BONUS_MIN_DEPOSIT', 500)
        bonus_amount = current_app.config.get('WELCOME_BONUS_AMOUNT', 1000)

        if deposit_amount < min_deposit:
            return False, f'Minimum deposit of {min_deposit} required for welcome bonus'

        WalletService.add_bonus(user, bonus_amount, f'Welcome Bonus - Deposit KES {deposit_amount:,.2f}')
        wallet.welcome_bonus_claimed = True

        bonus = Bonus(
            user_id=user.id, bonus_type='welcome', amount=bonus_amount,
            min_deposit=min_deposit, wagering_requirement=bonus_amount * 10,
            is_active=True
        )
        db.session.add(bonus)

        NotificationService.send(user.id, '🎉 Welcome Bonus Awarded!',
                                 f'You have received KES {bonus_amount:,.2f} welcome bonus!',
                                 NOTIFICATION_BONUS)

        db.session.commit()
        return True, f'Welcome bonus of KES {bonus_amount:,.2f} awarded!'


# =============================================================================
# BETTING SERVICE
# =============================================================================

class BettingService:
    """Handle bet placement and settlement."""

    @staticmethod
    def place_bet(user, selections_data, stake, is_bonus_bet=False):
        if len(selections_data) == 0:
            return False, 'No selections provided'

        if stake < current_app.config.get('MINIMUM_STAKE', 10):
            return False, f'Minimum stake is KES {current_app.config.get("MINIMUM_STAKE", 10)}'

        if stake > current_app.config.get('MAXIMUM_STAKE', 100000):
            return False, f'Maximum stake is KES {current_app.config.get("MAXIMUM_STAKE", 100000)}'

        wallet = WalletService.get_or_create_wallet(user)

        if is_bonus_bet:
            if wallet.bonus_balance < stake:
                return False, 'Insufficient bonus balance'
        else:
            if wallet.balance < stake:
                return False, 'Insufficient balance'

        bet_type = 'accumulator' if len(selections_data) > 1 else 'single'
        bet = Bet(
            user_id=user.id, bet_type=bet_type, stake=stake,
            is_bonus_bet=is_bonus_bet, status=BET_PENDING
        )
        db.session.add(bet)
        db.session.flush()

        total_odds = 1.0
        for sel_data in selections_data:
            match = Match.query.get(sel_data['match_id'])
            if not match:
                db.session.rollback()
                return False, f'Match {sel_data["match_id"]} not found'

            odds_obj = match.main_odds
            if not odds_obj:
                db.session.rollback()
                return False, f'No odds available for match {match.display_name}'

            odds_value = getattr(odds_obj, sel_data['selection_type'], None)
            if not odds_value:
                db.session.rollback()
                return False, f'Invalid selection type {sel_data["selection_type"]}'

            selection = BetSelection(
                bet_id=bet.id, match_id=match.id,
                selection_type=sel_data['selection_type'],
                odds_at_time=odds_value
            )
            db.session.add(selection)
            total_odds *= odds_value

        bet.total_odds = round(total_odds, 2)
        bet.potential_winnings = round(stake * total_odds, 2)

        deduction = WalletService.deduct_funds(user, stake, f'Bet #{bet.bet_reference}', is_bonus_bet)
        if not deduction:
            db.session.rollback()
            return False, 'Failed to deduct stake'

        db.session.commit()

        NotificationService.send(user.id, '✅ Bet Placed',
                                 f'Bet #{bet.bet_reference} placed successfully. Potential win: KES {bet.potential_winnings:,.2f}',
                                 NOTIFICATION_BET, bet.id)

        return True, bet

    @staticmethod
    def settle_bet(bet, result_data):
        """Settle a bet based on match results."""
        all_won = True
        any_lost = False

        for selection in bet.selections.all():
            match = selection.match
            if match.status != MATCH_FINISHED:
                continue

            if match.home_score is None or match.away_score is None:
                continue

            home_win = match.home_score > match.away_score
            draw = match.home_score == match.away_score
            away_win = match.away_score > match.home_score

            won = False
            if selection.selection_type == 'home_win' and home_win:
                won = True
            elif selection.selection_type == 'draw' and draw:
                won = True
            elif selection.selection_type == 'away_win' and away_win:
                won = True
            elif selection.selection_type == 'double_chance_1x' and (home_win or draw):
                won = True
            elif selection.selection_type == 'double_chance_12' and (home_win or away_win):
                won = True
            elif selection.selection_type == 'double_chance_2x' and (away_win or draw):
                won = True
            elif selection.selection_type == 'btts_yes' and match.home_score > 0 and match.away_score > 0:
                won = True
            elif selection.selection_type == 'btts_no' and (match.home_score == 0 or match.away_score == 0):
                won = True

            selection.is_settled = True
            selection.is_won = won
            selection.settled_at = datetime.now(timezone.utc)

            if not won:
                any_lost = True

        if any_lost:
            bet.status = BET_LOST
            bet.settled_at = datetime.now(timezone.utc)
            NotificationService.send(bet.user_id, '❌ Bet Lost',
                                     f'Bet #{bet.bet_reference} has lost. Better luck next time!',
                                     NOTIFICATION_BET, bet.id)
        else:
            bet.status = BET_WON
            bet.winnings = bet.potential_winnings
            bet.settled_at = datetime.now(timezone.utc)
            WalletService.add_funds(bet.user, bet.winnings,
                                    f'Bet #{bet.bet_reference} won!',
                                    TRANSACTION_BET_WON)
            NotificationService.send(bet.user_id, '🎉 Bet Won!',
                                     f'Bet #{bet.bet_reference} won! KES {bet.winnings:,.2f} credited.',
                                     NOTIFICATION_BET, bet.id)

        db.session.commit()
        return True


# =============================================================================
# NOTIFICATION SERVICE
# =============================================================================

class NotificationService:
    """Handle notifications."""

    @staticmethod
    def send(user_id, title, message, ntype='general', ref_id=None):
        notification = Notification(
            user_id=user_id, title=title, message=message,
            notification_type=ntype, reference_id=ref_id
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def send_global(title, message, ntype=NOTIFICATION_ANNOUNCEMENT):
        notification = Notification(
            user_id=None, title=title, message=message,
            notification_type=ntype, is_global=True
        )
        db.session.add(notification)
        db.session.commit()

        announcement = Announcement(title=title, content=message, priority='normal')
        db.session.add(announcement)
        db.session.commit()
        return notification

    @staticmethod
    def get_unread_count(user_id):
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()


# =============================================================================
# AUDIT SERVICE
# =============================================================================

class AuditService:
    """Handle audit logging."""

    @staticmethod
    def log(user_id, action, resource_type=None, resource_id=None, details=None, ip_address=None, user_agent=None):
        log = AuditLog(
            user_id=user_id, action=action,
            resource_type=resource_type, resource_id=resource_id,
            details=details, ip_address=ip_address, user_agent=user_agent
        )
        db.session.add(log)
        db.session.commit()
        return log


# =============================================================================
# ADMIN LOG SERVICE
# =============================================================================

class AdminLogService:
    @staticmethod
    def log(admin_id, action, target_user_id=None, details=None, ip_address=None):
        try:
            log = AdminLog(
                admin_id=admin_id,
                action=action,
                target_user_id=target_user_id,
                details=details,
                ip_address=ip_address
            )
            db.session.add(log)
            db.session.commit()
            return log

        except Exception:
            db.session.rollback()
            raise

# =============================================================================
# PAYMENT SERVICE
# =============================================================================

class PaymentService:
    """Abstract payment gateway service layer."""

    @staticmethod
    def process_deposit(deposit):
        """Process a deposit via M-Pesa STK Push."""
        from app.services import MpesaService, MpesaError

        user = deposit.user

        # ===== DEBUG: Print deposit info =====
        print("\n" + "=" * 60)
        print("📝 PROCESSING DEPOSIT")
        print(f"   Deposit ID: {deposit.id}")
        print(f"   Amount: {deposit.amount}")
        print(f"   User ID: {user.id}")
        print(f"   User object: {user}")
        # =====================================

        phone = deposit.phone_number or getattr(user, "phone", None) or getattr(user, "phone_number", None)

        # ===== DEBUG: Print phone number =====
        print(f"📞 Phone from DB: '{phone}'")
        # =====================================

        if not phone:
            print("❌ NO PHONE NUMBER FOUND ON USER!")
            return {
                'success': False,
                'message': 'Phone number is required for M-Pesa deposit'
            }

        account_ref = f'DEP-{deposit.id}'[:12]
        description = 'Wallet Deposit'

        # ===== DEBUG: Show what we're sending =====
        print(f"   Account Ref: {account_ref}")
        print(f"   Calling MpesaService.stk_push()...")
        # ==========================================

        try:
            result = MpesaService.stk_push(
                phone=phone,
                amount=int(deposit.amount),
                account_reference=account_ref,
                transaction_desc=description,
                callback_url=current_app.config.get(
                    'MPESA_CALLBACK_URL',
                    'https://your-domain.com/api/mpesa/callback'
                ),
            )

            # ===== DEBUG: Show result =====
            print(f"   STK Push result: {result}")
            # ===============================

            if result['success']:
                deposit.checkout_request_id = result['CheckoutRequestID']
                deposit.status = REQUEST_PENDING
                db.session.commit()

                print("✅ STK Push sent successfully!")
                return {
                    'success': True,
                    'transaction_id': result['CheckoutRequestID'],
                    'merchant_request_id': result['MerchantRequestID'],
                    'message': 'STK Push sent. Check your phone to complete payment.',
                    'checkout_request_id': result['CheckoutRequestID'],
                }
            else:
                print(f"❌ STK Push failed: {result.get('ResponseDescription')}")
                return {
                    'success': False,
                    'message': result.get('ResponseDescription', 'STK Push failed'),
                    'response_code': result.get('ResponseCode'),
                }

        except MpesaError as e:
            print(f"❌ M-Pesa Error: {e}")
            logger.error(f'M-Pesa deposit failed for deposit #{deposit.id}: {e}')
            return {
                'success': False,
                'message': f'M-Pesa error: {e}',
            }

    @staticmethod
    def process_withdrawal(withdrawal):
        """Process a withdrawal."""
        withdrawal.status = WITHDRAWAL_PENDING
        db.session.commit()
        return {
            'success': True,
            'transaction_id': f'WD-{withdrawal.reference}',
            'message': 'Withdrawal queued for processing.',
        }

    @staticmethod
    def validate_phone(phone, country='KE'):
        """Validate phone number format for M-Pesa."""
        from app.services import MpesaService
        normalized = MpesaService._format_phone(phone)
        return normalized is not None


# =============================================================================
# LIVE DATA SERVICE
# =============================================================================

class LiveDataService:
    """Service layer for live sports data integration."""

    SAMPLE_MATCHES = [
        {
            'sport': 'Football', 'league': 'English Premier League',
            'home_team': 'Manchester United', 'away_team': 'Liverpool',
            'match_date': '2026-07-20 17:00', 'home_win': 2.10, 'draw': 3.40, 'away_win': 3.50,
            'is_featured': True, 'is_live': False
        },
        {
            'sport': 'Football', 'league': 'La Liga',
            'home_team': 'Barcelona', 'away_team': 'Real Madrid',
            'match_date': '2026-07-20 20:00', 'home_win': 2.50, 'draw': 3.30, 'away_win': 2.80,
            'is_featured': True, 'is_live': False
        },
        {
            'sport': 'Basketball', 'league': 'NBA',
            'home_team': 'LA Lakers', 'away_team': 'Golden State Warriors',
            'match_date': '2026-07-21 03:00', 'home_win': 1.85, 'draw': None, 'away_win': 1.95,
            'is_featured': False, 'is_live': False
        },
        {
            'sport': 'Tennis', 'league': 'Wimbledon',
            'home_team': 'C. Alcaraz', 'away_team': 'N. Djokovic',
            'match_date': '2026-07-21 15:00', 'home_win': 2.20, 'draw': None, 'away_win': 1.70,
            'is_featured': False, 'is_live': False
        },
        {
            'sport': 'Football', 'league': 'Kenyan Premier League',
            'home_team': 'Gor Mahia', 'away_team': 'AFC Leopards',
            'match_date': '2026-07-19 15:00', 'home_win': 1.90, 'draw': 3.20, 'away_win': 4.50,
            'is_featured': True, 'is_live': True
        },
        {
            'sport': 'Rugby', 'league': 'Kenya Cup',
            'home_team': 'KCB Rugby', 'away_team': 'Kabras Sugar',
            'match_date': '2026-07-22 14:00', 'home_win': 1.75, 'draw': None, 'away_win': 2.10,
            'is_featured': False, 'is_live': False
        },
        {
            'sport': 'eSports', 'league': 'League of Legends World Championship',
            'home_team': 'T1', 'away_team': 'Gen.G',
            'match_date': '2026-07-23 12:00', 'home_win': 1.60, 'draw': None, 'away_win': 2.30,
            'is_featured': False, 'is_live': False
        },
        {
            'sport': 'Volleyball', 'league': 'Italian Serie A1',
            'home_team': 'Perugia', 'away_team': 'Lube Civitanova',
            'match_date': '2026-07-24 18:00', 'home_win': 1.80, 'draw': None, 'away_win': 2.00,
            'is_featured': False, 'is_live': False
        },
    ]

    @staticmethod
    def fetch_live_matches():
        headers = {
            "x-apisports-key": current_app.config["API_FOOTBALL_KEY"]
        }

        response = requests.get(
            current_app.config["API_FOOTBALL_URL"] + "/fixtures",
            headers=headers,
            params={"live": "all"},
            timeout=30
        )

        response.raise_for_status()

        return response.json()["response"]

    @staticmethod
    def fetch_upcoming_matches(sport=None, league=None):
        headers = {
            "x-apisports-key": current_app.config["API_FOOTBALL_KEY"]
        }

        params = {
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        response = requests.get(
            current_app.config["API_FOOTBALL_URL"] + "/fixtures",
            headers=headers,
            params=params,
            timeout=30
        )

        print("=" * 60)
        print("STATUS:", response.status_code)
        print(response.text[:2000])
        print("=" * 60)

        response.raise_for_status()

        data = response.json()

        print("Results:", data.get("results"))
        print("Errors:", data.get("errors"))
        print("Response length:", len(data.get("response", [])))

        return data.get("response", [])

    @staticmethod
    def sync_matches_to_db():
        fixtures = LiveDataService.fetch_upcoming_matches()

        print("=" * 60)
        print(f"Fetched {len(fixtures)} fixtures")
        if fixtures:
            print(fixtures[0])
        print("=" * 60)

        imported = 0

        for item in fixtures:

            sport_name = "Football"

            league_name = item["league"]["name"]

            home_team = item["teams"]["home"]["name"]
            away_team = item["teams"]["away"]["name"]

            match_date = datetime.fromisoformat(
                item["fixture"]["date"].replace("Z", "+00:00")
            )

            is_live = item["fixture"]["status"]["short"] == "LIVE"

            # ------------------------
            # Sport
            # ------------------------

            sport = Sport.query.filter_by(name=sport_name).first()

            if not sport:
                sport = Sport(
                    name=sport_name,
                    slug="football"
                )
                db.session.add(sport)
                db.session.flush()

            # ------------------------
            # League
            # ------------------------

            league = League.query.filter_by(
                name=league_name,
                sport_id=sport.id
            ).first()

            if not league:
                league = League(
                    name=league_name,
                    slug=league_name.lower().replace(" ", "-"),
                    sport_id=sport.id
                )

                db.session.add(league)
                db.session.flush()

            # ------------------------
            # Existing Match?
            # ------------------------

            existing = Match.query.filter_by(
                home_team=home_team,
                away_team=away_team,
                match_date=match_date
            ).first()

            if existing:
                match = existing
            else:
                match = Match(
                    sport_id=sport.id,
                    league_id=league.id,
                    home_team=home_team,
                    away_team=away_team,
                    match_date=match_date,
                    status=MATCH_SCHEDULED,
                    is_live=is_live,
                    is_featured=False
                )
                db.session.add(match)
                db.session.flush()
                imported += 1

            # Create odds if they don't already exist
            existing_odds = Odds.query.filter_by(match_id=match.id).first()

            print(f"Match {match.id}: existing_odds = {existing_odds}")

            if existing_odds is None:
                print(f"Creating odds for match {match.id}")

                odds = Odds(
                    match_id=match.id,
                    home_win=round(random.uniform(1.50, 3.50), 2),
                    draw=round(random.uniform(2.80, 4.20), 2),
                    away_win=round(random.uniform(1.50, 3.50), 2),
                    over_under_line=2.5,
                    over=1.90,
                    under=1.90,
                    btts_yes=1.85,
                    btts_no=1.95,
                    double_chance_1x=1.30,
                    double_chance_12=1.25,
                    double_chance_2x=1.45,
                )

                db.session.add(odds)
                print(f"Added odds for match {match.id}")

                print("About to commit...")
                print(db.session.new)

        db.session.commit()

        return imported


# =============================================================================
# MPESA SERVICE
# =============================================================================

class MpesaService:
    """
    Safaricom Daraja API integration for Lipa na M-Pesa Online (STK Push).

    Handles:
    - OAuth token generation
    - STK Push initiation
    - Callback validation and processing
    - Transaction status querying
    """

    SANDBOX_TEST_PHONE = '254708374149'

    @staticmethod
    def _get_base_url() -> str:
        env = current_app.config.get('MPESA_ENV', 'sandbox')
        if env == 'production':
            return 'https://api.safaricom.co.ke'
        return 'https://sandbox.safaricom.co.ke'

    @staticmethod
    def _get_credentials() -> Tuple[str, str, str, str]:
        return (
            current_app.config['MPESA_CONSUMER_KEY'],
            current_app.config['MPESA_CONSUMER_SECRET'],
            current_app.config['MPESA_PASSKEY'],
            current_app.config['MPESA_SHORTCODE'],
        )

    @staticmethod
    def _get_timestamp() -> str:
        eat_now = datetime.utcnow() + timedelta(hours=3)
        return eat_now.strftime('%Y%m%d%H%M%S')

    @staticmethod
    def _generate_password(shortcode: str, passkey: str, timestamp: str) -> str:
        raw = f'{shortcode}{passkey}{timestamp}'
        return base64.b64encode(raw.encode()).decode()

    @staticmethod
    def _format_phone(phone: str) -> Optional[str]:
        if not phone:
            return None
        cleaned = ''.join(filter(str.isdigit, phone))
        if cleaned.startswith('0') and len(cleaned) == 10:
            return '254' + cleaned[1:]
        elif cleaned.startswith('254') and len(cleaned) == 12:
            return cleaned
        elif cleaned.startswith('7') and len(cleaned) == 9:
            return '254' + cleaned
        elif cleaned.startswith('1') and len(cleaned) == 9:
            return '254' + cleaned
        elif cleaned.startswith('254') and len(cleaned) > 12:
            return cleaned[:12]
        return None

    @staticmethod
    def get_access_token() -> str:
        consumer_key, consumer_secret, _, _ = MpesaService._get_credentials()
        base_url = MpesaService._get_base_url()
        print("\n" + "=" * 60)
        print("GETTING MPESA ACCESS TOKEN")
        print("Environment:", current_app.config.get("MPESA_ENV"))
        print("Base URL:", base_url)
        print("Consumer Key exists:", bool(consumer_key))
        print("Consumer Secret exists:", bool(consumer_secret))
        print("Consumer Key (first 10 chars):", consumer_key[:10] if consumer_key else "None")
        print("=" * 60)
        auth_string = f'{consumer_key}:{consumer_secret}'
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        headers = {
            'Authorization': f'Basic {encoded_auth}',
            'Content-Type': 'application/json',
        }
        url = f'{base_url}/oauth/v1/generate?grant_type=client_credentials'
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            if 'access_token' not in data:
                raise MpesaError(f'OAuth token missing in response: {data}')
            token = data['access_token']
            expires_in = data.get('expires_in', 3600)
            logger.info(f'M-Pesa OAuth token obtained successfully. Expires in {expires_in}s')
            return token
        except requests.exceptions.RequestException as e:
            logger.error(f'M-Pesa OAuth request failed: {e}')
            raise MpesaError(f'Failed to get access token: {e}')

    @staticmethod
    def stk_push(
        phone: str,
        amount: int,
        account_reference: str,
        transaction_desc: str = 'Payment',
        callback_url: Optional[str] = None,
    ) -> dict:
        # ===== DEBUG: Show entry =====
        print("\n" + "=" * 60)
        print("🚀 STK PUSH CALLED")
        print(f"   Raw phone: {phone}")
        print(f"   Amount: {amount}")
        print(f"   Account Ref: {account_reference}")
        print(f"   Description: {transaction_desc}")
        print("=" * 60)
        # =============================

        normalized_phone = MpesaService._format_phone(phone)

        # ===== DEBUG: Show normalized phone =====
        print(f"📞 Normalized phone: {normalized_phone}")
        # ========================================

        if not normalized_phone:
            print("❌ PHONE NUMBER REJECTED BY _format_phone!")
            raise MpesaError(f'Invalid phone number format: {phone}')

        if not isinstance(amount, int):
            amount = int(amount)

        if amount <= 0:
            raise MpesaError(f'Amount must be positive: {amount}')

        account_reference = str(account_reference)[:12]
        transaction_desc = str(transaction_desc)[:13]

        consumer_key, consumer_secret, passkey, shortcode = MpesaService._get_credentials()
        shortcode = str(shortcode)

        print(f"🏢 Shortcode: {shortcode}")
        print(f"🔄 Getting access token...")

        token = MpesaService.get_access_token()
        print(f"✅ Token obtained: {token[:20]}...")

        timestamp = MpesaService._get_timestamp()
        password = MpesaService._generate_password(shortcode, passkey, timestamp)
        base_url = MpesaService._get_base_url()

        print(f"🌐 Base URL: {base_url}")
        print(f"⏰ Timestamp: {timestamp}")

        callback = callback_url or current_app.config.get(
            'MPESA_CALLBACK_URL',
            'https://your-domain.com/api/mpesa/callback'
        )

        print(f"📞 Callback URL: {callback}")

        payload = {
            'BusinessShortCode': shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'TransactionType': current_app.config.get(
                'MPESA_TRANSACTION_TYPE',
                'CustomerPayBillOnline'
            ),
            'Amount': amount,
            'PartyA': normalized_phone,
            'PartyB': shortcode,
            'PhoneNumber': normalized_phone,
            'CallBackURL': callback,
            'AccountReference': account_reference,
            'TransactionDesc': transaction_desc,
        }

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        url = f'{base_url}/mpesa/stkpush/v1/processrequest'

        logger.info(
            f'Initiating STK Push: phone={normalized_phone}, amount={amount}, ref={account_reference}'
        )

        try:
            print("📡 Sending STK Push request to Safaricom...")

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )

            # ===== CRITICAL DEBUG: Show raw response =====
            print("\n" + "=" * 60)
            print("📡 SAFARICOM RESPONSE")
            print(f"   HTTP Status: {response.status_code}")
            print(f"   Raw Body: {response.text}")
            print("=" * 60)
            # =============================================

            response.raise_for_status()

            data = response.json()

            print(f"   ResponseCode: {data.get('ResponseCode')}")
            print(f"   ResponseDescription: {data.get('ResponseDescription')}")
            print(f"   CheckoutRequestID: {data.get('CheckoutRequestID')}")
            print(f"   MerchantRequestID: {data.get('MerchantRequestID')}")

            result = {
                'success': data.get('ResponseCode') == '0',
                'CheckoutRequestID': data.get('CheckoutRequestID'),
                'MerchantRequestID': data.get('MerchantRequestID'),
                'ResponseCode': data.get('ResponseCode'),
                'ResponseDescription': data.get('ResponseDescription'),
                'raw_response': data,
            }

            if result['success']:
                print("✅ STK PUSH ACCEPTED BY SAFARICOM!")
                logger.info(
                    f'STK Push accepted. CheckoutRequestID: {result["CheckoutRequestID"]}'
                )
            else:
                print(f"❌ STK PUSH REJECTED: {result['ResponseDescription']}")
                logger.warning(
                    f'STK Push rejected: {result["ResponseDescription"]}'
                )

            return result

        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP REQUEST FAILED: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response status: {e.response.status_code}")
                print(f"   Response body: {e.response.text}")
            logger.exception("STK Push request failed")
            raise MpesaError(f'STK Push request failed: {e}')

    @staticmethod
    def query_status(checkout_request_id: str) -> dict:
        consumer_key, consumer_secret, passkey, shortcode = MpesaService._get_credentials()
        shortcode = str(shortcode)
        token = MpesaService.get_access_token()
        timestamp = MpesaService._get_timestamp()
        password = MpesaService._generate_password(shortcode, passkey, timestamp)
        base_url = MpesaService._get_base_url()
        payload = {
            'BusinessShortCode': shortcode,
            'Password': password,
            'Timestamp': timestamp,
            'CheckoutRequestID': checkout_request_id,
        }
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        url = f'{base_url}/mpesa/stkpushquery/v1/query'
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return {
                'success': data.get('ResultCode') == '0',
                'ResultCode': data.get('ResultCode'),
                'ResultDesc': data.get('ResultDesc'),
                'raw_response': data,
            }
        except requests.exceptions.RequestException as e:
            logger.error(f'STK Push query failed: {e}')
            raise MpesaError(f'STK Push query failed: {e}')

    @staticmethod
    def process_callback(callback_data: dict) -> dict:
        try:
            body = callback_data.get('Body', {})
            stk_callback = body.get('stkCallback', {})
            checkout_id = stk_callback.get('CheckoutRequestID', '')
            result_code = stk_callback.get('ResultCode', -1)
            result_desc = stk_callback.get('ResultDesc', '')
            result = {
                'success': result_code == 0,
                'CheckoutRequestID': checkout_id,
                'ResultCode': result_code,
                'ResultDesc': result_desc,
                'amount': None,
                'receipt': None,
                'phone': None,
                'raw': callback_data,
            }
            if result_code == 0:
                metadata = stk_callback.get('CallbackMetadata', {})
                items = metadata.get('Item', [])
                for item in items:
                    name = item.get('Name', '')
                    value = item.get('Value')
                    if name == 'Amount':
                        result['amount'] = value
                    elif name == 'MpesaReceiptNumber':
                        result['receipt'] = value
                    elif name == 'PhoneNumber':
                        result['phone'] = str(value)
                    elif name == 'TransactionDate':
                        result['transaction_date'] = value
                logger.info(
                    f'M-Pesa payment confirmed: Receipt={result["receipt"]}, '
                    f'Amount={result["amount"]}, Phone={result["phone"]}'
                )
            else:
                result_code_map = {
                    1032: 'Customer cancelled the request',
                    1037: 'Request timed out (customer did not enter PIN)',
                    1: 'Insufficient balance or other error',
                }
                human_readable = result_code_map.get(result_code, 'Unknown error')
                logger.warning(
                    f'M-Pesa callback error: Code={result_code} ({human_readable}), '
                    f'Desc={result_desc}'
                )
            return result
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f'Failed to parse M-Pesa callback: {e}')
            return {
                'success': False,
                'CheckoutRequestID': '',
                'ResultCode': -1,
                'ResultDesc': f'Callback parsing error: {e}',
                'amount': None,
                'receipt': None,
                'phone': None,
                'raw': callback_data,
            }

    @staticmethod
    def validate_callback_signature(callback_data: dict, expected_checkout_id: str) -> bool:
        try:
            actual_id = callback_data.get('Body', {}).get('stkCallback', {}).get('CheckoutRequestID', '')
            return actual_id == expected_checkout_id
        except (AttributeError, TypeError):
            return False