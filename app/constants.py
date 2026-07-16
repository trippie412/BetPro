"""Application-wide constants and enums."""

# Bet Status
BET_PENDING = 'pending'
BET_WON = 'won'
BET_LOST = 'lost'
BET_CANCELLED = 'cancelled'
BET_SETTLED = 'settled'
BET_STATUSES = [BET_PENDING, BET_WON, BET_LOST, BET_CANCELLED, BET_SETTLED]

# Transaction Types
TRANSACTION_DEPOSIT = 'deposit'
TRANSACTION_WITHDRAWAL = 'withdrawal'
TRANSACTION_BET_PLACED = 'bet_placed'
TRANSACTION_BET_WON = 'bet_won'
TRANSACTION_BONUS = 'bonus'
TRANSACTION_ADJUSTMENT = 'adjustment'
TRANSACTION_TYPES = [TRANSACTION_DEPOSIT, TRANSACTION_WITHDRAWAL, TRANSACTION_BET_PLACED,
                     TRANSACTION_BET_WON, TRANSACTION_BONUS, TRANSACTION_ADJUSTMENT]

# Transaction Status
TRANSACTION_PENDING = 'pending'
TRANSACTION_COMPLETED = 'completed'
TRANSACTION_REJECTED = 'rejected'
TRANSACTION_STATUSES = [TRANSACTION_PENDING, TRANSACTION_COMPLETED, TRANSACTION_REJECTED]

# Deposit/Withdrawal Status
REQUEST_PENDING = 'pending'
REQUEST_APPROVED = 'approved'
REQUEST_REJECTED = 'rejected'
REQUEST_STATUSES = [REQUEST_PENDING, REQUEST_APPROVED, REQUEST_REJECTED]

# User Roles
ROLE_USER = 'user'
ROLE_ADMIN = 'admin'
ROLE_SUPER_ADMIN = 'super_admin'
ROLES = [ROLE_USER, ROLE_ADMIN, ROLE_SUPER_ADMIN]

# Match Status
MATCH_SCHEDULED = 'scheduled'
MATCH_LIVE = 'live'
MATCH_FINISHED = 'finished'
MATCH_CANCELLED = 'cancelled'
MATCH_POSTPONED = 'postponed'
MATCH_STATUSES = [MATCH_SCHEDULED, MATCH_LIVE, MATCH_FINISHED, MATCH_CANCELLED, MATCH_POSTPONED]

# Sports
SPORTS = [
    {'id': 'football', 'name': 'Football', 'icon': 'fa-futbol'},
    {'id': 'basketball', 'name': 'Basketball', 'icon': 'fa-basketball-ball'},
    {'id': 'tennis', 'name': 'Tennis', 'icon': 'fa-table-tennis'},
    {'id': 'volleyball', 'name': 'Volleyball', 'icon': 'fa-volleyball-ball'},
    {'id': 'rugby', 'name': 'Rugby', 'icon': 'fa-football-ball'},
    {'id': 'esports', 'name': 'eSports', 'icon': 'fa-gamepad'},
    {'id': 'virtual', 'name': 'Virtual Games', 'icon': 'fa-robot'},
]

# Notification Types
NOTIFICATION_DEPOSIT = 'deposit'
NOTIFICATION_WITHDRAWAL = 'withdrawal'
NOTIFICATION_BET = 'bet'
NOTIFICATION_BONUS = 'bonus'
NOTIFICATION_ANNOUNCEMENT = 'announcement'
NOTIFICATION_TYPES = [NOTIFICATION_DEPOSIT, NOTIFICATION_WITHDRAWAL,
                      NOTIFICATION_BET, NOTIFICATION_BONUS, NOTIFICATION_ANNOUNCEMENT]

# Countries
COUNTRIES = [
    'Kenya', 'Uganda', 'Tanzania', 'Rwanda', 'Burundi', 'South Sudan',
    'Ethiopia', 'Nigeria', 'Ghana', 'South Africa', 'Other'
]

# Currency
CURRENCY = 'KES'
CURRENCY_SYMBOL = 'KSh'