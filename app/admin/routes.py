"""Admin panel routes."""
from datetime import datetime, timezone, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import (User, Wallet, Deposit, Withdrawal, Bet, BetSelection,
                        Match, Odds, Sport, League, Notification, Bonus,
                        Announcement, AuditLog, AdminLog, WalletTransaction,
                        SystemSettings)
from app.admin import admin_bp
from app.admin.forms import (UserEditForm, MatchForm, OddsForm, SportForm,
                              LeagueForm, AnnouncementForm, SystemSettingsForm,
                              AdminDepositForm, AdminWithdrawalForm)
from app.decorators import admin_required
from app.constants import *
from app.services import WalletService, NotificationService, AdminLogService


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard."""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True, is_suspended=False).count()
    total_deposits = db.session.query(db.func.coalesce(db.func.sum(Deposit.amount), 0))\
        .filter(Deposit.status == REQUEST_APPROVED).scalar()
    total_withdrawals = db.session.query(db.func.coalesce(db.func.sum(Withdrawal.amount), 0))\
        .filter(Withdrawal.status == REQUEST_APPROVED).scalar()
    total_bets = Bet.query.count()
    pending_bets = Bet.query.filter_by(status=BET_PENDING).count()
    pending_deposits = Deposit.query.filter_by(status=REQUEST_PENDING).count()
    pending_withdrawals = Withdrawal.query.filter_by(status=REQUEST_PENDING).count()

    # Recent registrations
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    # Revenue today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_deposits = db.session.query(db.func.coalesce(db.func.sum(Deposit.amount), 0))\
        .filter(Deposit.status == REQUEST_APPROVED, Deposit.created_at >= today_start).scalar()

    return render_template('admin/index.html',
                         total_users=total_users, active_users=active_users,
                         total_deposits=float(total_deposits),
                         total_withdrawals=float(total_withdrawals),
                         total_bets=total_bets, pending_bets=pending_bets,
                         pending_deposits=pending_deposits,
                         pending_withdrawals=pending_withdrawals,
                         recent_users=recent_users,
                         today_deposits=float(today_deposits))


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    query = User.query
    if search:
        query = query.filter(
            User.username.ilike(f'%{search}%') |
            User.email.ilike(f'%{search}%') |
            User.full_name.ilike(f'%{search}%') |
            User.phone.ilike(f'%{search}%')
        )

    users = query.order_by(User.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=users, search=search)


@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    bets = Bet.query.filter_by(user_id=user.id).order_by(Bet.created_at.desc()).limit(10).all()
    deposits = Deposit.query.filter_by(user_id=user.id).order_by(Deposit.created_at.desc()).limit(10).all()
    withdrawals = Withdrawal.query.filter_by(user_id=user.id).order_by(Withdrawal.created_at.desc()).limit(10).all()
    return render_template('admin/user_detail.html', user=user,
                         bets=bets, deposits=deposits, withdrawals=withdrawals)


@admin_bp.route('/users/<int:user_id>/toggle-suspend', methods=['POST'])
@login_required
@admin_required
def toggle_suspend(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot suspend yourself.', 'warning')
        return redirect(url_for('admin.users'))

    user.is_suspended = not user.is_suspended
    action = 'suspended' if user.is_suspended else 'activated'

    AdminLogService.log(current_user.id, f'User {action}',
                       user.id, f'User {user.username} {action} by {current_user.username}',
                       request.remote_addr)

    NotificationService.send(user.id, f'Account {"Suspended" if user.is_suspended else "Activated"}',
                            f'Your account has been {action} by an administrator.',
                            NOTIFICATION_ANNOUNCEMENT)

    db.session.commit()
    flash(f'User {user.username} has been {action}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/deposits')
@login_required
@admin_required
def deposits():
    status = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)

    query = Deposit.query
    if status != 'all':
        query = query.filter_by(status=status)

    deposits = query.order_by(Deposit.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/deposits.html', deposits=deposits, current_status=status)


@admin_bp.route('/deposits/<int:deposit_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_deposit(deposit_id):
    deposit = Deposit.query.get_or_404(deposit_id)
    if deposit.status != REQUEST_PENDING:
        flash('Deposit already processed.', 'warning')
        return redirect(url_for('admin.deposits'))

    deposit.status = REQUEST_APPROVED
    deposit.approved_by = current_user.id
    deposit.approved_at = datetime.now(timezone.utc)
    deposit.receipt_number = f'RCT-ADM-{deposit.id:06d}'

    WalletService.add_funds(deposit.user, deposit.amount,
                           f'Deposit approved by admin. Ref: {deposit.receipt_number}')

    # Check welcome bonus
    from app.services import BonusService
    BonusService.check_welcome_bonus(deposit.user, deposit.amount)

    AdminLogService.log(current_user.id, 'Deposit approved',
                       deposit.user_id,
                       f'KES {deposit.amount:,.2f} deposit approved for {deposit.user.username}',
                       request.remote_addr)

    NotificationService.send(deposit.user_id, '✅ Deposit Approved',
                           f'Your deposit of KES {deposit.amount:,.2f} has been approved.',
                           NOTIFICATION_DEPOSIT, deposit.id)

    db.session.commit()
    flash(f'KES {deposit.amount:,.2f} deposit approved.', 'success')
    return redirect(url_for('admin.deposits'))


@admin_bp.route('/deposits/<int:deposit_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_deposit(deposit_id):
    deposit = Deposit.query.get_or_404(deposit_id)
    if deposit.status != REQUEST_PENDING:
        flash('Deposit already processed.', 'warning')
        return redirect(url_for('admin.deposits'))

    deposit.status = REQUEST_REJECTED
    deposit.approved_by = current_user.id
    deposit.approved_at = datetime.now(timezone.utc)

    AdminLogService.log(current_user.id, 'Deposit rejected',
                       deposit.user_id,
                       f'KES {deposit.amount:,.2f} deposit rejected for {deposit.user.username}',
                       request.remote_addr)

    NotificationService.send(deposit.user_id, '❌ Deposit Rejected',
                           f'Your deposit of KES {deposit.amount:,.2f} has been rejected.',
                           NOTIFICATION_DEPOSIT, deposit.id)

    db.session.commit()
    flash('Deposit rejected.', 'info')
    return redirect(url_for('admin.deposits'))


@admin_bp.route('/withdrawals')
@login_required
@admin_required
def withdrawals():
    status = request.args.get('status', 'pending')
    page = request.args.get('page', 1, type=int)

    query = Withdrawal.query
    if status != 'all':
        query = query.filter_by(status=status)

    withdrawals = query.order_by(Withdrawal.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/withdrawals.html', withdrawals=withdrawals, current_status=status)


@admin_bp.route('/withdrawals/<int:withdrawal_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_withdrawal(withdrawal_id):
    withdrawal = Withdrawal.query.get_or_404(withdrawal_id)
    if withdrawal.status != REQUEST_PENDING:
        flash('Withdrawal already processed.', 'warning')
        return redirect(url_for('admin.withdrawals'))

    if withdrawal.amount > withdrawal.user.wallet.balance:
        flash('Insufficient user balance for this withdrawal.', 'danger')
        return redirect(url_for('admin.withdrawals'))

    withdrawal.status = REQUEST_APPROVED
    withdrawal.approved_by = current_user.id
    withdrawal.approved_at = datetime.now(timezone.utc)

    WalletService.deduct_funds(withdrawal.user, withdrawal.amount,
                              f'Withdrawal #{withdrawal.reference[:8]}')

    AdminLogService.log(current_user.id, 'Withdrawal approved',
                       withdrawal.user_id,
                       f'KES {withdrawal.amount:,.2f} withdrawal approved for {withdrawal.user.username}',
                       request.remote_addr)

    NotificationService.send(withdrawal.user_id, '✅ Withdrawal Approved',
                           f'Your withdrawal of KES {withdrawal.amount:,.2f} has been approved.',
                           NOTIFICATION_WITHDRAWAL, withdrawal.id)

    db.session.commit()
    flash(f'KES {withdrawal.amount:,.2f} withdrawal approved.', 'success')
    return redirect(url_for('admin.withdrawals'))


@admin_bp.route('/withdrawals/<int:withdrawal_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_withdrawal(withdrawal_id):
    withdrawal = Withdrawal.query.get_or_404(withdrawal_id)
    if withdrawal.status != REQUEST_PENDING:
        flash('Withdrawal already processed.', 'warning')
        return redirect(url_for('admin.withdrawals'))

    withdrawal.status = REQUEST_REJECTED
    withdrawal.approved_by = current_user.id
    withdrawal.approved_at = datetime.now(timezone.utc)

    AdminLogService.log(current_user.id, 'Withdrawal rejected',
                       withdrawal.user_id,
                       f'KES {withdrawal.amount:,.2f} withdrawal rejected for {withdrawal.user.username}',
                       request.remote_addr)

    NotificationService.send(withdrawal.user_id, '❌ Withdrawal Rejected',
                           f'Your withdrawal of KES {withdrawal.amount:,.2f} has been rejected.',
                           NOTIFICATION_WITHDRAWAL, withdrawal.id)

    db.session.commit()
    flash('Withdrawal rejected.', 'info')
    return redirect(url_for('admin.withdrawals'))


@admin_bp.route('/matches')
@login_required
@admin_required
def matches():
    sport_id = request.args.get('sport_id', type=int)
    page = request.args.get('page', 1, type=int)

    query = Match.query
    if sport_id:
        query = query.filter_by(sport_id=sport_id)

    matches = query.order_by(Match.match_date.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    sports = Sport.query.all()
    return render_template('admin/matches.html', matches=matches, sports=sports)


@admin_bp.route('/matches/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_match():
    form = MatchForm()
    form.sport_id.choices = [(s.id, s.name) for s in Sport.query.all()]
    form.league_id.choices = [(l.id, l.name) for l in League.query.all()]

    if form.validate_on_submit():
        match = Match(
            sport_id=form.sport_id.data, league_id=form.league_id.data,
            home_team=form.home_team.data, away_team=form.away_team.data,
            match_date=form.match_date.data, status=form.status.data,
            is_featured=form.is_featured.data, is_live=form.is_live.data
        )
        db.session.add(match)
        db.session.flush()

        # Create default odds
        odds = Odds(match_id=match.id, home_win=1.50, draw=3.00, away_win=2.50)
        db.session.add(odds)
        db.session.commit()

        AdminLogService.log(current_user.id, 'Match created', None,
                          f'Match: {match.home_team} vs {match.away_team}',
                          request.remote_addr)
        flash('Match created successfully.', 'success')
        return redirect(url_for('admin.matches'))

    return render_template('admin/match_form.html', form=form, edit=False)


@admin_bp.route('/matches/<int:match_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_match(match_id):
    match = Match.query.get_or_404(match_id)
    form = MatchForm(obj=match)
    form.sport_id.choices = [(s.id, s.name) for s in Sport.query.all()]
    form.league_id.choices = [(l.id, l.name) for l in League.query.all()]

    if form.validate_on_submit():
        match.sport_id = form.sport_id.data
        match.league_id = form.league_id.data
        match.home_team = form.home_team.data
        match.away_team = form.away_team.data
        match.match_date = form.match_date.data
        match.status = form.status.data
        match.is_featured = form.is_featured.data
        match.is_live = form.is_live.data
        db.session.commit()

        AdminLogService.log(current_user.id, 'Match updated', match.id,
                          f'Match: {match.home_team} vs {match.away_team}',
                          request.remote_addr)
        flash('Match updated successfully.', 'success')
        return redirect(url_for('admin.matches'))

    return render_template('admin/match_form.html', form=form, match=match, edit=True)


@admin_bp.route('/matches/<int:match_id>/odds', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_odds(match_id):
    match = Match.query.get_or_404(match_id)
    odds = match.main_odds or Odds(match_id=match.id)
    form = OddsForm(obj=odds)

    if form.validate_on_submit():
        odds.home_win = form.home_win.data
        odds.draw = form.draw.data
        odds.away_win = form.away_win.data
        odds.btts_yes = form.btts_yes.data
        odds.btts_no = form.btts_no.data
        odds.over_under_line = form.over_under_line.data
        odds.over = form.over.data
        odds.under = form.under.data
        odds.double_chance_1x = form.double_chance_1x.data
        odds.double_chance_12 = form.double_chance_12.data
        odds.double_chance_2x = form.double_chance_2x.data

        if not odds.id:
            db.session.add(odds)
            match.odds = odds

        db.session.commit()
        AdminLogService.log(current_user.id, 'Odds updated', match.id,
                          f'Odds updated for {match.home_team} vs {match.away_team}',
                          request.remote_addr)
        flash('Odds updated successfully.', 'success')
        return redirect(url_for('admin.matches'))

    return render_template('admin/odds_form.html', form=form, match=match)


@admin_bp.route('/matches/<int:match_id>/score', methods=['POST'])
@login_required
@admin_required
def update_score(match_id):
    match = Match.query.get_or_404(match_id)
    match.home_score = request.form.get('home_score', type=int)
    match.away_score = request.form.get('away_score', type=int)

    # Auto-settle if match finished
    if match.status == MATCH_FINISHED:
        from app.services import BettingService
        # Settle all bets containing this match
        selections = BetSelection.query.filter_by(match_id=match.id).all()
        for sel in selections:
            bet = Bet.query.get(sel.bet_id)
            if bet and bet.status == BET_PENDING:
                BettingService.settle_bet(bet, {})

    db.session.commit()
    flash(f'Score updated: {match.home_team} {match.home_score} - {match.away_score} {match.away_team}', 'success')
    return redirect(url_for('admin.matches'))


@admin_bp.route('/sports')
@login_required
@admin_required
def sports():
    sports = Sport.query.order_by(Sport.display_order).all()
    return render_template('admin/sports.html', sports=sports)


@admin_bp.route('/sports/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_sport():
    form = SportForm()
    if form.validate_on_submit():
        sport = Sport(name=form.name.data, slug=form.slug.data,
                     icon=form.icon.data, description=form.description.data,
                     display_order=form.display_order.data)
        db.session.add(sport)
        db.session.commit()
        flash(f'Sport "{sport.name}" created.', 'success')
        return redirect(url_for('admin.sports'))
    return render_template('admin/sport_form.html', form=form, edit=False)


@admin_bp.route('/leagues')
@login_required
@admin_required
def leagues():
    leagues = League.query.order_by(League.name).all()
    sports = Sport.query.all()
    return render_template('admin/leagues.html', leagues=leagues, sports=sports)


@admin_bp.route('/leagues/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_league():
    form = LeagueForm()
    form.sport_id.choices = [(s.id, s.name) for s in Sport.query.all()]
    if form.validate_on_submit():
        league = League(sport_id=form.sport_id.data, name=form.name.data,
                       country=form.country.data)
        db.session.add(league)
        db.session.commit()
        flash(f'League "{league.name}" created.', 'success')
        return redirect(url_for('admin.leagues'))
    return render_template('admin/league_form.html', form=form, edit=False)


@admin_bp.route('/announcements')
@login_required
@admin_required
def announcements():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin/announcements.html', announcements=announcements)


@admin_bp.route('/announcements/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_announcement():
    form = AnnouncementForm()
    if form.validate_on_submit():
        announcement = Announcement(
            title=form.title.data, content=form.content.data,
            priority=form.priority.data, created_by=current_user.id
        )
        db.session.add(announcement)
        db.session.commit()

        # Send to all users
        users = User.query.filter_by(is_active=True).all()
        for user in users:
            NotificationService.send(user.id, form.title.data, form.content.data,
                                    NOTIFICATION_ANNOUNCEMENT)

        AdminLogService.log(current_user.id, 'Announcement created', None,
                          f'Announcement: {form.title.data}', request.remote_addr)
        flash('Announcement sent to all users.', 'success')
        return redirect(url_for('admin.announcements'))
    return render_template('admin/announcement_form.html', form=form)


@admin_bp.route('/bets')
@login_required
@admin_required
def bets():
    status = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)

    query = Bet.query
    if status != 'all':
        query = query.filter_by(status=status)

    bets = query.order_by(Bet.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/bets.html', bets=bets, current_status=status)


@admin_bp.route('/wallet-adjustments')
@login_required
@admin_required
def wallet_adjustments():
    form = AdminDepositForm()
    users_list = User.query.order_by(User.username).all()
    return render_template('admin/wallet_adjustments.html', form=form, users=users_list)


@admin_bp.route('/wallet-adjustments/add', methods=['POST'])
@login_required
@admin_required
def add_wallet_funds():
    user_id = request.form.get('user_id', type=int)
    amount = request.form.get('amount', type=float)
    description = request.form.get('description', 'Admin adjustment')

    if not user_id or not amount or amount <= 0:
        flash('Invalid input.', 'danger')
        return redirect(url_for('admin.wallet_adjustments'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.wallet_adjustments'))

    WalletService.add_funds(user, amount, f'Admin adjustment: {description}')

    AdminLogService.log(current_user.id, 'Wallet adjustment',
                       user_id, f'Added KES {amount:,.2f} to {user.username}. Reason: {description}',
                       request.remote_addr)

    NotificationService.send(user.id, '💳 Wallet Credited',
                           f'KES {amount:,.2f} has been added to your wallet. ({description})',
                           NOTIFICATION_DEPOSIT)

    db.session.commit()
    flash(f'KES {amount:,.2f} added to {user.username}\'s wallet.', 'success')
    return redirect(url_for('admin.wallet_adjustments'))


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc())\
        .paginate(page=page, per_page=30, error_out=False)
    return render_template('admin/audit_logs.html', logs=logs)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    form = SystemSettingsForm()
    if form.validate_on_submit():
        settings_map = {
            'minimum_deposit': form.minimum_deposit.data,
            'minimum_withdrawal': form.minimum_withdrawal.data,
            'minimum_stake': form.minimum_stake.data,
            'maximum_stake': form.maximum_stake.data,
            'welcome_bonus_amount': form.welcome_bonus_amount.data,
            'welcome_bonus_min_deposit': form.welcome_bonus_min_deposit.data,
        }
        for key, value in settings_map.items():
            setting = SystemSettings.query.filter_by(key=key).first()
            if setting:
                setting.value = str(value)
            else:
                db.session.add(SystemSettings(key=key, value=str(value)))
        db.session.commit()
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('admin.settings'))

    # Load current values
    for key in ['minimum_deposit', 'minimum_withdrawal', 'minimum_stake',
                'maximum_stake', 'welcome_bonus_amount', 'welcome_bonus_min_deposit']:
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting and hasattr(form, key):
            getattr(form, key).data = float(setting.value)

    return render_template('admin/settings.html', form=form)


@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    # Returns JSON data for charts
    from sqlalchemy import func, extract

    # Daily deposits for last 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    daily_deposits = db.session.query(
        func.date(Deposit.created_at).label('date'),
        func.coalesce(func.sum(Deposit.amount), 0).label('total')
    ).filter(
        Deposit.status == REQUEST_APPROVED,
        Deposit.created_at >= thirty_days_ago
    ).group_by(func.date(Deposit.created_at)).all()

    # Daily registrations
    daily_registrations = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= thirty_days_ago
    ).group_by(func.date(User.created_at)).all()

    # Bets by status
    bets_by_status = db.session.query(
        Bet.status, func.count(Bet.id)
    ).group_by(Bet.status).all()

    # Top users by deposits
    top_users = db.session.query(
        User.username,
        func.coalesce(func.sum(Deposit.amount), 0).label('total_deposits')
    ).join(Deposit, User.id == Deposit.user_id)\
     .filter(Deposit.status == REQUEST_APPROVED)\
     .group_by(User.id, User.username)\
     .order_by(func.coalesce(func.sum(Deposit.amount), 0).desc())\
     .limit(10).all()

    return jsonify({
        'daily_deposits': [{'date': str(d.date), 'total': float(d.total)} for d in daily_deposits],
        'daily_registrations': [{'date': str(r.date), 'count': r.count} for r in daily_registrations],
        'bets_by_status': {s: int(c) for s, c in bets_by_status},
        'top_users': [{'username': u.username, 'total_deposits': float(u.total_deposits)} for u in top_users],
    })


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    page = request.args.get('page', 1, type=int)
    logs = AdminLog.query.order_by(AdminLog.created_at.desc())\
        .paginate(page=page, per_page=30, error_out=False)
    return render_template('admin/logs.html', logs=logs)