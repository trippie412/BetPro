"""Database models for BetPro platform."""
import uuid
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.constants import *


def generate_uuid():
    return str(uuid.uuid4())


def kenya_time():
    return datetime.now(timezone.utc)


# Association table for user roles
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=kenya_time)

    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(64), unique=True, default=generate_uuid)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(60), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    profile_picture = db.Column(db.String(256), nullable=True, default='default.png')
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_suspended = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=kenya_time)
    updated_at = db.Column(db.DateTime, default=kenya_time, onupdate=kenya_time)

    # Relationships
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                            backref=db.backref('users', lazy=True))
    wallet = db.relationship('Wallet', uselist=False, back_populates='user', cascade='all, delete-orphan')
    bets = db.relationship('Bet', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    deposits = db.relationship(
    'Deposit',
    foreign_keys='Deposit.user_id',
    back_populates='user',
    lazy='dynamic',
    cascade='all, delete-orphan'
)

    withdrawals = db.relationship(
    'Withdrawal',
    foreign_keys='Withdrawal.user_id',
    back_populates='user',
    lazy='dynamic',
    cascade='all, delete-orphan'
)
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    transactions = db.relationship('WalletTransaction', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)

    def get_wallet_balance(self):
        if self.wallet:
            return self.wallet.balance
        return 0.0

    def get_bonus_balance(self):
        if self.wallet:
            return self.wallet.bonus_balance
        return 0.0

    @property
    def total_deposits(self):
        return db.session.query(db.func.coalesce(db.func.sum(Deposit.amount), 0))\
            .filter(Deposit.user_id == self.id, Deposit.status == REQUEST_APPROVED).scalar()

    @property
    def total_withdrawals(self):
        return db.session.query(db.func.coalesce(db.func.sum(Withdrawal.amount), 0))\
            .filter(Withdrawal.user_id == self.id, Withdrawal.status == REQUEST_APPROVED).scalar()

    @property
    def total_bets(self):
        return self.bets.count()

    @property
    def total_won_bets(self):
        return self.bets.filter(Bet.status == BET_WON).count()

    @property
    def total_lost_bets(self):
        return self.bets.filter(Bet.status == BET_LOST).count()

    @property
    def win_rate(self):
        total = self.total_bets
        if total == 0:
            return 0
        return round((self.total_won_bets / total) * 100, 2)

    def __repr__(self):
        return f'<User {self.username}>'


class Wallet(db.Model):
    __tablename__ = 'wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0.0)
    bonus_balance = db.Column(db.Float, default=0.0)
    total_deposited = db.Column(db.Float, default=0.0)
    total_withdrawn = db.Column(db.Float, default=0.0)
    total_bet = db.Column(db.Float, default=0.0)
    total_won = db.Column(db.Float, default=0.0)
    bonus_received = db.Column(db.Float, default=0.0)
    welcome_bonus_claimed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=kenya_time)
    updated_at = db.Column(db.DateTime, default=kenya_time, onupdate=kenya_time)

    user = db.relationship('User', back_populates='wallet')

    @property
    def total_balance(self):
        return self.balance + self.bonus_balance

    def add_balance(self, amount):
        self.balance += amount
        self.total_deposited += amount

    def add_bonus(self, amount):
        self.bonus_balance += amount
        self.bonus_received += amount

    def deduct_balance(self, amount, from_bonus=False):
        if from_bonus:
            if self.bonus_balance >= amount:
                self.bonus_balance -= amount
                return True
            return False
        if self.balance >= amount:
            self.balance -= amount
            return True
        return False

    def __repr__(self):
        return f'<Wallet User:{self.user_id} Bal:{self.balance} Bonus:{self.bonus_balance}>'


class WalletTransaction(db.Model):
    __tablename__ = 'wallet_transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    transaction_type = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    balance_before = db.Column(db.Float, default=0.0)
    balance_after = db.Column(db.Float, default=0.0)
    description = db.Column(db.String(200), nullable=True)
    reference = db.Column(db.String(64), unique=True, default=generate_uuid)
    status = db.Column(db.String(20), default=TRANSACTION_COMPLETED)
    created_at = db.Column(db.DateTime, default=kenya_time)

    user = db.relationship('User', back_populates='transactions')

    def __repr__(self):
        return f'<Transaction {self.transaction_type} {self.amount} User:{self.user_id}>'


class Deposit(db.Model):
    __tablename__ = 'deposits'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    transaction_code = db.Column(db.String(100), nullable=True)
    receipt_number = db.Column(db.String(100), nullable=True, unique=True)

    # M-Pesa callback tracking
    checkout_request_id = db.Column(db.String(100), unique=True, nullable=True)
    merchant_request_id = db.Column(db.String(100), nullable=True)
    callback_data = db.Column(db.Text, nullable=True)
    
    # Pesapal fields
    pesapal_order_tracking_id = db.Column(db.String(100), nullable=True, unique=True)
    pesapal_merchant_reference = db.Column(db.String(100), nullable=True)

    reference = db.Column(db.String(64), unique=True, default=generate_uuid)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default=REQUEST_PENDING)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=kenya_time)
    updated_at = db.Column(db.DateTime, default=kenya_time, onupdate=kenya_time)

    user = db.relationship('User', back_populates='deposits', foreign_keys=[user_id])
    approver = db.relationship('User', foreign_keys=[approved_by])

    def __repr__(self):
        return f'<Deposit {self.amount} User:{self.user_id} Status:{self.status}>'


class Withdrawal(db.Model):
    __tablename__ = 'withdrawals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    account_name = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(100), nullable=True)
    reference = db.Column(db.String(64), unique=True, default=generate_uuid)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default=REQUEST_PENDING)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=kenya_time)
    updated_at = db.Column(db.DateTime, default=kenya_time, onupdate=kenya_time)

    user = db.relationship('User', back_populates='withdrawals', foreign_keys=[user_id])
    approver = db.relationship('User', foreign_keys=[approved_by])

    def __repr__(self):
        return f'<Withdrawal {self.amount} User:{self.user_id} Status:{self.status}>'


class Sport(db.Model):
    __tablename__ = 'sports'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    icon = db.Column(db.String(50), default='fa-sports')
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=kenya_time)

    leagues = db.relationship('League', back_populates='sport', lazy='dynamic', cascade='all, delete-orphan')
    matches = db.relationship('Match', back_populates='sport', lazy='dynamic')

    def __repr__(self):
        return f'<Sport {self.name}>'


class League(db.Model):
    __tablename__ = 'leagues'

    id = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey('sports.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(120), nullable=True)
    country = db.Column(db.String(60), nullable=True)
    logo = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=kenya_time)

    sport = db.relationship('Sport', back_populates='leagues')
    matches = db.relationship('Match', back_populates='league', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<League {self.name}>'


class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey('sports.id'), nullable=False)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=False)
    home_team = db.Column(db.String(120), nullable=False)
    away_team = db.Column(db.String(120), nullable=False)
    home_score = db.Column(db.Integer, nullable=True)
    away_score = db.Column(db.Integer, nullable=True)
    match_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default=MATCH_SCHEDULED)
    is_featured = db.Column(db.Boolean, default=False)
    is_live = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    external_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=kenya_time)
    updated_at = db.Column(db.DateTime, default=kenya_time, onupdate=kenya_time)

    sport = db.relationship('Sport', back_populates='matches')
    league = db.relationship('League', back_populates='matches')
    odds = db.relationship('Odds', back_populates='match', uselist=False, cascade='all, delete-orphan')
    bet_selections = db.relationship('BetSelection', back_populates='match', lazy='dynamic')

    @property
    def display_name(self):
        return f'{self.home_team} vs {self.away_team}'

    @property
    def main_odds(self):
        if self.odds:
            return self.odds
        return None

    def __repr__(self):
        return f'<Match {self.home_team} vs {self.away_team}>'


class Odds(db.Model):
    __tablename__ = 'odds'

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), unique=True, nullable=False)
    home_win = db.Column(db.Float, nullable=False, default=1.50)
    draw = db.Column(db.Float, nullable=True)
    away_win = db.Column(db.Float, nullable=False, default=1.50)
    over_under_line = db.Column(db.Float, nullable=True)
    over = db.Column(db.Float, nullable=True)
    under = db.Column(db.Float, nullable=True)
    btts_yes = db.Column(db.Float, nullable=True)
    btts_no = db.Column(db.Float, nullable=True)
    double_chance_1x = db.Column(db.Float, nullable=True)
    double_chance_12 = db.Column(db.Float, nullable=True)
    double_chance_2x = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=kenya_time)
    updated_at = db.Column(db.DateTime, default=kenya_time, onupdate=kenya_time)

    match = db.relationship('Match', back_populates='odds')

    def __repr__(self):
        return f'<Odds Match:{self.match_id}>'


class Bet(db.Model):
    __tablename__ = 'bets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    bet_reference = db.Column(db.String(64), unique=True, nullable=False, default=generate_uuid)
    bet_type = db.Column(db.String(20), default='single')  # single or accumulator
    stake = db.Column(db.Float, nullable=False)
    total_odds = db.Column(db.Float, nullable=False, default=1.0)
    potential_winnings = db.Column(db.Float, nullable=False, default=0.0)
    winnings = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default=BET_PENDING)
    is_bonus_bet = db.Column(db.Boolean, default=False)
    settled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=kenya_time)
    updated_at = db.Column(db.DateTime, default=kenya_time, onupdate=kenya_time)

    user = db.relationship('User', back_populates='bets')
    selections = db.relationship('BetSelection', back_populates='bet', lazy='dynamic', cascade='all, delete-orphan')

    def calculate_potential(self):
        """Calculate potential winnings based on selections."""
        self.total_odds = 1.0
        for sel in self.selections.all():
            self.total_odds *= sel.odds_at_time
        self.total_odds = round(self.total_odds, 2)
        self.potential_winnings = round(self.stake * self.total_odds, 2)

    def __repr__(self):
        return f'<Bet {self.bet_reference} User:{self.user_id} Status:{self.status}>'


class BetSelection(db.Model):
    __tablename__ = 'bet_selections'

    id = db.Column(db.Integer, primary_key=True)
    bet_id = db.Column(db.Integer, db.ForeignKey('bets.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    selection_type = db.Column(db.String(50), nullable=False)  # home_win, draw, away_win, etc.
    odds_at_time = db.Column(db.Float, nullable=False)
    is_settled = db.Column(db.Boolean, default=False)
    is_won = db.Column(db.Boolean, nullable=True)
    settled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=kenya_time)

    bet = db.relationship('Bet', back_populates='selections')
    match = db.relationship('Match', back_populates='bet_selections')

    def __repr__(self):
        return f'<BetSelection Bet:{self.bet_id} Match:{self.match_id} Type:{self.selection_type}>'


class Bonus(db.Model):
    __tablename__ = 'bonuses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    bonus_type = db.Column(db.String(50), nullable=False)  # welcome, deposit, promo
    amount = db.Column(db.Float, nullable=False)
    min_deposit = db.Column(db.Float, default=0.0)
    wagering_requirement = db.Column(db.Float, default=0.0)
    wagering_met = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    is_expired = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    claimed_at = db.Column(db.DateTime, default=kenya_time)
    created_at = db.Column(db.DateTime, default=kenya_time)

    user = db.relationship('User')

    def __repr__(self):
        return f'<Bonus {self.bonus_type} {self.amount} User:{self.user_id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=True)
    notification_type = db.Column(db.String(30), default='general')
    reference_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    is_global = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=kenya_time)

    user = db.relationship('User', back_populates='notifications')

    def __repr__(self):
        return f'<Notification {self.title} User:{self.user_id}>'


class Announcement(db.Model):
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=kenya_time)
    updated_at = db.Column(db.DateTime, default=kenya_time, onupdate=kenya_time)

    creator = db.relationship('User', foreign_keys=[created_by])

    def __repr__(self):
        return f'<Announcement {self.title}>'
    
class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)

    phone_number = db.Column(db.String(20), nullable=False)

    message = db.Column(db.Text, nullable=False)

    rating = db.Column(db.Integer, default=5)

    is_visible = db.Column(db.Boolean, default=True)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    created_at = db.Column(db.DateTime, default=kenya_time)

    creator = db.relationship("User", foreign_keys=[created_by])

    @property
    def masked_phone(self):
        phone = self.phone_number or ""
        if len(phone) >= 10:
            return phone[:4] + "*****" + phone[-2:]
        return phone

    def __repr__(self):
        return f"<Review {self.id}>"


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    action = db.Column(db.String(200), nullable=False)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=kenya_time)

    user = db.relationship('User', back_populates='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.action} User:{self.user_id}>'


class AdminLog(db.Model):
    __tablename__ = 'admin_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    target_user_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=kenya_time)

    admin = db.relationship('User', foreign_keys=[admin_id])

    def __repr__(self):
        return f'<AdminLog {self.action}>'


class SystemSettings(db.Model):
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(200), nullable=True)
    updated_at = db.Column(db.DateTime, default=kenya_time, onupdate=kenya_time)

    def __repr__(self):
        return f'<SystemSettings {self.key}>'