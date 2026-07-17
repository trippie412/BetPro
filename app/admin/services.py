"""Service layer for admin panel operations."""
from datetime import datetime, timezone, timedelta
from flask import current_app, request
from flask_login import current_user
from sqlalchemy import func, extract
from app import db
from app.models import (
    User, Wallet, Deposit, Withdrawal, Bet, BetSelection,
    Match, Odds, Sport, League, Notification, Bonus,
    Announcement, AuditLog, AdminLog, WalletTransaction,
    SystemSettings
)
from app.constants import *
from app.services import WalletService, NotificationService


class AdminDashboardService:
    """Service class for admin dashboard data aggregation."""

    @staticmethod
    def get_dashboard_stats():
        """Get all dashboard statistics."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)
        month_start = today_start.replace(day=1)

        # User stats
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True, is_suspended=False).count()
        suspended_users = User.query.filter_by(is_suspended=True).count()
        new_users_today = User.query.filter(User.created_at >= today_start).count()
        new_users_week = User.query.filter(User.created_at >= week_start).count()
        new_users_month = User.query.filter(User.created_at >= month_start).count()

        # Match stats
        total_matches = Match.query.count()
        live_matches = Match.query.filter_by(is_live=True).count()
        featured_matches = Match.query.filter_by(is_featured=True).count()
        scheduled_matches = Match.query.filter_by(status=MATCH_SCHEDULED).count()
        finished_matches = Match.query.filter_by(status=MATCH_FINISHED).count()

        # Bet stats
        total_bets = Bet.query.count()
        pending_bets = Bet.query.filter_by(status=BET_PENDING).count()
        won_bets = Bet.query.filter_by(status=BET_WON).count()
        lost_bets = Bet.query.filter_by(status=BET_LOST).count()
        total_stake = db.session.query(
            func.coalesce(func.sum(Bet.stake), 0)
        ).scalar()
        total_payout = db.session.query(
            func.coalesce(func.sum(Bet.winnings), 0)
        ).filter(Bet.status.in_([BET_WON])).scalar()

        # Today's bets
        today_bets = Bet.query.filter(Bet.created_at >= today_start).count()
        today_stake = db.session.query(
            func.coalesce(func.sum(Bet.stake), 0)
        ).filter(Bet.created_at >= today_start).scalar()

        # Revenue
        total_deposits = db.session.query(
            func.coalesce(func.sum(Deposit.amount), 0)
        ).filter(Deposit.status == REQUEST_APPROVED).scalar()

        total_withdrawals = db.session.query(
            func.coalesce(func.sum(Withdrawal.amount), 0)
        ).filter(Withdrawal.status == REQUEST_APPROVED).scalar()

        total_revenue = float(total_deposits) - float(total_withdrawals)

        today_deposits = db.session.query(
            func.coalesce(func.sum(Deposit.amount), 0)
        ).filter(Deposit.status == REQUEST_APPROVED, Deposit.created_at >= today_start).scalar()

        today_withdrawals = db.session.query(
            func.coalesce(func.sum(Withdrawal.amount), 0)
        ).filter(Withdrawal.status == REQUEST_APPROVED, Withdrawal.created_at >= today_start).scalar()

        # Pending requests
        pending_deposits = Deposit.query.filter_by(status=REQUEST_PENDING).count()
        pending_withdrawals = Withdrawal.query.filter_by(status=REQUEST_PENDING).count()

        # Wallet stats
        total_balance = db.session.query(
            func.coalesce(func.sum(Wallet.balance), 0)
        ).scalar()
        total_bonus = db.session.query(
            func.coalesce(func.sum(Wallet.bonus_balance), 0)
        ).scalar()

        return {
            'total_users': total_users,
            'active_users': active_users,
            'suspended_users': suspended_users,
            'new_users_today': new_users_today,
            'new_users_week': new_users_week,
            'new_users_month': new_users_month,
            'total_matches': total_matches,
            'live_matches': live_matches,
            'featured_matches': featured_matches,
            'scheduled_matches': scheduled_matches,
            'finished_matches': finished_matches,
            'total_bets': total_bets,
            'pending_bets': pending_bets,
            'won_bets': won_bets,
            'lost_bets': lost_bets,
            'total_stake': float(total_stake),
            'total_payout': float(total_payout),
            'today_bets': today_bets,
            'today_stake': float(today_stake),
            'total_deposits': float(total_deposits),
            'total_withdrawals': float(total_withdrawals),
            'total_revenue': total_revenue,
            'today_deposits': float(today_deposits),
            'today_withdrawals': float(today_withdrawals),
            'pending_deposits': pending_deposits,
            'pending_withdrawals': pending_withdrawals,
            'total_balance': float(total_balance),
            'total_bonus': float(total_bonus),
        }

    @staticmethod
    def get_recent_bets(limit=10):
        """Get most recent bets with user info."""
        return Bet.query.order_by(Bet.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_recent_users(limit=10):
        """Get most recently registered users."""
        return User.query.order_by(User.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_recent_transactions(limit=10):
        """Get most recent wallet transactions."""
        return WalletTransaction.query.order_by(WalletTransaction.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_recent_deposits(limit=5):
        """Get most recent pending deposits."""
        return Deposit.query.filter_by(status=REQUEST_PENDING)\
            .order_by(Deposit.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_recent_withdrawals(limit=5):
        """Get most recent pending withdrawals."""
        return Withdrawal.query.filter_by(status=REQUEST_PENDING)\
            .order_by(Withdrawal.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_sport_summary():
        """Get match counts by sport."""
        results = db.session.query(
            Sport.name,
            Sport.icon,
            func.count(Match.id).label('total'),
            func.sum(func.cast(Match.is_live, db.Integer)).label('live'),
        ).outerjoin(Match, Match.sport_id == Sport.id)\
         .group_by(Sport.id, Sport.name, Sport.icon).all()
        return results

    @staticmethod
    def get_revenue_data(days=30):
        """Get daily revenue data for charts."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        dates = []
        deposits_data = []
        withdrawals_data = []

        for i in range(days):
            day = start_date + timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            day_deposits = db.session.query(
                func.coalesce(func.sum(Deposit.amount), 0)
            ).filter(
                Deposit.status == REQUEST_APPROVED,
                Deposit.created_at >= day_start,
                Deposit.created_at < day_end
            ).scalar()

            day_withdrawals = db.session.query(
                func.coalesce(func.sum(Withdrawal.amount), 0)
            ).filter(
                Withdrawal.status == REQUEST_APPROVED,
                Withdrawal.created_at >= day_start,
                Withdrawal.created_at < day_end
            ).scalar()

            dates.append(day.strftime('%Y-%m-%d'))
            deposits_data.append(float(day_deposits))
            withdrawals_data.append(float(day_withdrawals))

        return {
            'dates': dates,
            'deposits': deposits_data,
            'withdrawals': withdrawals_data,
        }


class AdminLogService:
    """Service for logging admin actions."""

    @staticmethod
    def log(admin_id, action, target_user_id=None, details=None, ip_address=None):
        """Create an admin log entry."""
        log_entry = AdminLog(
            admin_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            details=details,
            ip_address=ip_address,
        )
        db.session.add(log_entry)

    @staticmethod
    def get_logs(page=1, per_page=30, action=None, admin_id=None):
        """Get paginated admin logs with optional filters."""
        query = AdminLog.query
        if action:
            query = query.filter(AdminLog.action.ilike(f'%{action}%'))
        if admin_id:
            query = query.filter(AdminLog.admin_id == admin_id)
        return query.order_by(AdminLog.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_recent_logs(limit=20):
        """Get most recent admin logs."""
        return AdminLog.query.order_by(AdminLog.created_at.desc()).limit(limit).all()


class AdminReportService:
    """Service for generating admin reports."""

    @staticmethod
    def get_revenue_report(period='daily'):
        """Generate revenue report for the given period."""
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        if period == 'daily':
            start_date = today
        elif period == 'weekly':
            start_date = today - timedelta(days=7)
        elif period == 'monthly':
            start_date = today.replace(day=1)
        elif period == 'yearly':
            start_date = today.replace(month=1, day=1)
        else:
            start_date = today - timedelta(days=30)

        deposits = db.session.query(
            func.coalesce(func.sum(Deposit.amount), 0)
        ).filter(
            Deposit.status == REQUEST_APPROVED,
            Deposit.created_at >= start_date
        ).scalar()

        withdrawals = db.session.query(
            func.coalesce(func.sum(Withdrawal.amount), 0)
        ).filter(
            Withdrawal.status == REQUEST_APPROVED,
            Withdrawal.created_at >= start_date
        ).scalar()

        bets_placed = Bet.query.filter(Bet.created_at >= start_date).count()
        bets_won = Bet.query.filter(
            Bet.status == BET_WON,
            Bet.created_at >= start_date
        ).count()

        stake_total = db.session.query(
            func.coalesce(func.sum(Bet.stake), 0)
        ).filter(Bet.created_at >= start_date).scalar()

        payout_total = db.session.query(
            func.coalesce(func.sum(Bet.winnings), 0)
        ).filter(
            Bet.status == BET_WON,
            Bet.created_at >= start_date
        ).scalar()

        new_users = User.query.filter(User.created_at >= start_date).count()

        return {
            'period': period,
            'start_date': start_date,
            'deposits': float(deposits),
            'withdrawals': float(withdrawals),
            'net_revenue': float(deposits) - float(withdrawals),
            'bets_placed': bets_placed,
            'bets_won': bets_won,
            'total_stake': float(stake_total),
            'total_payout': float(payout_total),
            'profit_loss': float(stake_total) - float(payout_total),
            'new_users': new_users,
        }

    @staticmethod
    def get_most_popular_matches(limit=10):
        """Get matches with the most bets placed."""
        results = db.session.query(
            Match.id,
            Match.home_team,
            Match.away_team,
            func.count(BetSelection.id).label('bet_count'),
            func.coalesce(func.sum(Bet.stake), 0).label('total_stake'),
        ).join(BetSelection, BetSelection.match_id == Match.id)\
         .join(Bet, Bet.id == BetSelection.bet_id)\
         .group_by(Match.id, Match.home_team, Match.away_team)\
         .order_by(func.count(BetSelection.id).desc())\
         .limit(limit).all()
        return results

    @staticmethod
    def get_top_users(limit=10, sort_by='deposits'):
        """Get top users by deposits, bets, or winnings."""
        if sort_by == 'deposits':
            results = db.session.query(
                User.id, User.username, User.full_name,
                func.coalesce(func.sum(Deposit.amount), 0).label('total_deposits'),
                func.count(Deposit.id).label('deposit_count'),
            ).outerjoin(Deposit, (Deposit.user_id == User.id) & (Deposit.status == REQUEST_APPROVED))\
             .group_by(User.id, User.username, User.full_name)\
             .order_by(func.coalesce(func.sum(Deposit.amount), 0).desc())\
             .limit(limit).all()
        elif sort_by == 'bets':
            results = db.session.query(
                User.id, User.username, User.full_name,
                func.count(Bet.id).label('total_bets'),
                func.coalesce(func.sum(Bet.stake), 0).label('total_stake'),
            ).outerjoin(Bet, Bet.user_id == User.id)\
             .group_by(User.id, User.username, User.full_name)\
             .order_by(func.count(Bet.id).desc())\
             .limit(limit).all()
        elif sort_by == 'winnings':
            results = db.session.query(
                User.id, User.username, User.full_name,
                func.coalesce(func.sum(Bet.winnings), 0).label('total_won'),
                func.count(Bet.id).filter(Bet.status == BET_WON).label('wins'),
            ).outerjoin(Bet, (Bet.user_id == User.id) & (Bet.status == BET_WON))\
             .group_by(User.id, User.username, User.full_name)\
             .order_by(func.coalesce(func.sum(Bet.winnings), 0).desc())\
             .limit(limit).all()
        else:
            results = []
        return results


class AdminBettingService:
    """Service for admin betting operations."""

    @staticmethod
    def close_betting(match_id):
        """Close betting for a specific match."""
        match = Match.query.get(match_id)
        if not match:
            return False, 'Match not found'
        from app.services import BettingService
        BettingService.close_betting(match)
        return True, 'Betting closed'

    @staticmethod
    def open_betting(match_id):
        """Open betting for a specific match."""
        match = Match.query.get(match_id)
        if not match:
            return False, 'Match not found'
        match.status = MATCH_SCHEDULED
        db.session.commit()
        return True, 'Betting opened'

    @staticmethod
    def settle_match(match_id, home_score, away_score):
        """Settle all bets for a finished match."""
        match = Match.query.get(match_id)
        if not match:
            return False, 'Match not found'

        match.home_score = home_score
        match.away_score = away_score
        match.status = MATCH_FINISHED
        match.is_live = False

        from app.services import BettingService
        selections = BetSelection.query.filter_by(match_id=match.id, is_settled=False).all()
        for sel in selections:
            bet = Bet.query.get(sel.bet_id)
            if bet and bet.status == BET_PENDING:
                BettingService.settle_bet(bet, {
                    'home_score': home_score,
                    'away_score': away_score,
                })

        db.session.commit()
        return True, 'Match settled successfully'