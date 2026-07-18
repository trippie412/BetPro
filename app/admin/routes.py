"""Admin panel routes."""
from datetime import datetime, timezone, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import (User, Wallet, Deposit, Withdrawal, Bet, BetSelection,
                        Match, Odds, Sport, League, Notification, Bonus,
                        Announcement, AuditLog, AdminLog, WalletTransaction,
                        Review, SystemSettings)
from app.admin import admin_bp
from app.admin.forms import (UserEditForm, MatchForm, OddsForm, SportForm,
                              LeagueForm, AnnouncementForm, SystemSettingsForm,
                              AdminDepositForm, ReviewForm, AdminWithdrawalForm)
from app.decorators import admin_required
from app.constants import *
from app.services import WalletService, NotificationService, AdminLogService
from app.admin.review_generator import generate_review


# =============================================================================
# CONTEXT PROCESSOR
# =============================================================================

@admin_bp.context_processor
def inject_admin_globals():
    """Inject admin-specific globals into all admin templates."""
    pending_deps = Deposit.query.filter_by(status=REQUEST_PENDING).count()
    pending_withs = Withdrawal.query.filter_by(status=REQUEST_PENDING).count()
    return {
        'now': datetime.now,
        'pending_deposits': pending_deps,
        'pending_withdrawals': pending_withs,
        'currency_symbol': 'KSh',
    }


# =============================================================================
# DASHBOARD
# =============================================================================

@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Enhanced admin dashboard with full stats, charts, recent data."""
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

    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_deposits = db.session.query(db.func.coalesce(db.func.sum(Deposit.amount), 0))\
        .filter(Deposit.status == REQUEST_APPROVED, Deposit.created_at >= today_start).scalar()

    recent_bets = Bet.query.order_by(Bet.created_at.desc()).limit(5).all()

    recent_transactions = WalletTransaction.query.order_by(
        WalletTransaction.id.desc()
    ).limit(10).all()

    bets_by_status = dict(
        db.session.query(Bet.status, func.count(Bet.id))
        .group_by(Bet.status).all()
    )

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    revenue_data = db.session.query(
        func.date(Deposit.created_at).label('date'),
        func.coalesce(func.sum(Deposit.amount), 0).label('total')
    ).filter(
        Deposit.status == REQUEST_APPROVED,
        Deposit.created_at >= thirty_days_ago
    ).group_by(func.date(Deposit.created_at)).order_by(func.date(Deposit.created_at)).all()

    sport_summary = db.session.query(
        Sport.name,
        func.count(Match.id).label('match_count')
    ).outerjoin(Match, Match.sport_id == Sport.id)\
     .group_by(Sport.id, Sport.name)\
     .order_by(func.count(Match.id).desc()).all()

    stats = {
        "total_users": total_users,
        "active_users": active_users,
        "total_deposits": float(total_deposits or 0),
        "total_withdrawals": float(total_withdrawals or 0),
        "total_bets": total_bets,
        "pending_bets": pending_bets,
        "pending_deposits": pending_deposits,
        "pending_withdrawals": pending_withdrawals,
        "today_deposits": float(today_deposits or 0),
    }

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_users=recent_users,
        recent_bets=recent_bets,
        recent_transactions=recent_transactions,
        bets_by_status=bets_by_status,
        revenue_data=[{'date': str(d.date), 'total': float(d.total)} for d in revenue_data],
        sport_summary=sport_summary
    )


# =============================================================================
# USER MANAGEMENT
# =============================================================================

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


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user details."""
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        user.username = form.username.data
        user.full_name = form.full_name.data
        user.email = form.email.data
        user.phone = form.phone.data
        user.country = form.country.data
        user.is_active = form.is_active.data
        user.is_suspended = form.is_suspended.data
        user.is_admin = form.is_admin.data
        db.session.commit()

        AdminLogService.log(current_user.id, 'User updated', user.id,
                            f'Updated user: {user.username}', request.remote_addr)
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.user_detail', user_id=user.id))

    return render_template('admin/user_form.html', form=form, user=user)


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    """Reset a user's password."""
    user = User.query.get_or_404(user_id)
    new_password = request.form.get('new_password', 'Password123!')

    user.set_password(new_password)
    db.session.commit()

    AdminLogService.log(current_user.id, 'Password reset', user.id,
                        f'Password reset for user: {user.username}',
                        request.remote_addr)

    NotificationService.send(user.id, '🔑 Password Reset',
                             f'Your password has been reset by an administrator. New password: {new_password}. Please change it after logging in.',
                             'security')

    flash(f'Password reset for {user.username}. New password: {new_password}', 'warning')
    return redirect(url_for('admin.user_detail', user_id=user.id))


@admin_bp.route('/users/<int:user_id>/balance', methods=['POST'])
@login_required
@admin_required
def adjust_user_balance(user_id):
    """Adjust a user's wallet balance."""
    user = User.query.get_or_404(user_id)
    amount = request.form.get('amount', type=float)
    action = request.form.get('action', 'add')

    if not amount or amount <= 0:
        flash('Invalid amount.', 'danger')
        return redirect(url_for('admin.user_detail', user_id=user.id))

    if action == 'add':
        WalletService.add_funds(user, amount,
                                f'Admin credit adjustment by {current_user.username}')
        flash(f'KES {amount:,.2f} added to {user.username}\'s wallet.', 'success')
    elif action == 'deduct':
        if user.wallet.balance >= amount:
            WalletService.deduct_funds(user, amount,
                                       f'Admin debit adjustment by {current_user.username}')
            flash(f'KES {amount:,.2f} deducted from {user.username}\'s wallet.', 'success')
        else:
            flash('Insufficient balance.', 'danger')

    AdminLogService.log(current_user.id, f'Balance {action}', user.id,
                        f'{action.upper()}: KES {amount:,.2f} for {user.username}',
                        request.remote_addr)
    db.session.commit()
    return redirect(url_for('admin.user_detail', user_id=user.id))


# =============================================================================
# DEPOSITS
# =============================================================================

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


# =============================================================================
# WITHDRAWALS
# =============================================================================

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


# =============================================================================
# WALLET MANAGEMENT
# =============================================================================

@admin_bp.route('/wallet')
@login_required
@admin_required
def wallet():
    """Wallet management dashboard - overview of pending requests."""
    pending_deposits = Deposit.query.filter_by(status=REQUEST_PENDING)\
        .order_by(Deposit.created_at.desc()).all()
    pending_withdrawals = Withdrawal.query.filter_by(status=REQUEST_PENDING)\
        .order_by(Withdrawal.created_at.desc()).all()

    recent_approved_deposits = Deposit.query.filter_by(status=REQUEST_APPROVED)\
        .order_by(Deposit.approved_at.desc()).limit(10).all()
    recent_approved_withdrawals = Withdrawal.query.filter_by(status=REQUEST_APPROVED)\
        .order_by(Withdrawal.approved_at.desc()).limit(10).all()

    return render_template('admin/wallet.html',
                           pending_deposits=pending_deposits,
                           pending_withdrawals=pending_withdrawals,
                           recent_approved_deposits=recent_approved_deposits,
                           recent_approved_withdrawals=recent_approved_withdrawals)


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


# =============================================================================
# MATCH MANAGEMENT
# =============================================================================

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


@admin_bp.route('/matches/search')
@login_required
@admin_required
def match_search():
    """AJAX search for matches."""
    q = request.args.get('q', '')
    sport_id = request.args.get('sport_id', type=int)
    status = request.args.get('status', '')

    query = Match.query
    if q:
        query = query.filter(
            Match.home_team.ilike(f'%{q}%') |
            Match.away_team.ilike(f'%{q}%')
        )
    if sport_id:
        query = query.filter_by(sport_id=sport_id)
    if status:
        query = query.filter_by(status=status)

    matches = query.order_by(Match.match_date.desc()).limit(10).all()
    return jsonify([{
        'id': m.id,
        'display_name': m.display_name if hasattr(m, 'display_name') else f'{m.home_team} vs {m.away_team}',
        'match_date': m.match_date.strftime('%Y-%m-%d %H:%M') if m.match_date else '',
        'status': m.status,
    } for m in matches])


@admin_bp.route('/matches/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_match():
    form = MatchForm()
    form.sport_id.choices = [(s.id, s.name) for s in Sport.query.all()]
    form.league_id.choices = [(l.id, l.name) for l in League.query.all()]

    if form.validate_on_submit():
        try:
            match = Match(
                sport_id=form.sport_id.data,
                league_id=form.league_id.data,
                home_team=form.home_team.data,
                away_team=form.away_team.data,
                match_date=form.match_date.data,
                status=form.status.data,
                is_featured=form.is_featured.data,
                is_live=form.is_live.data
            )

            db.session.add(match)
            db.session.flush()

            odds = Odds(
                match_id=match.id,
                home_win=1.50,
                draw=3.00,
                away_win=2.50
            )

            db.session.add(odds)
            db.session.commit()

            flash("Match created successfully.", "success")
            return redirect(url_for("admin.matches"))

        except Exception as e:
            db.session.rollback()
            print(e)
            flash(str(e), "danger")
    else:
        print(form.errors)

    return render_template(
        "admin/match_form.html",
        form=form,
        edit=False
    )


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
    odds = match.main_odds if hasattr(match, 'main_odds') else None
    if not odds:
        odds = Odds(match_id=match.id)
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

    if match.status == MATCH_FINISHED:
        selections = BetSelection.query.filter_by(match_id=match.id).all()
        for sel in selections:
            bet = Bet.query.get(sel.bet_id)
            if bet and bet.status == BET_PENDING:
                from app.services import BettingService
                BettingService.settle_bet(bet, {})

    db.session.commit()
    flash(f'Score updated: {match.home_team} {match.home_score or "?"}-{match.away_score or "?"} {match.away_team}', 'success')
    return redirect(url_for('admin.matches'))


@admin_bp.route('/matches/<int:match_id>/mark-live', methods=['POST'])
@login_required
@admin_required
def mark_match_live(match_id):
    """Mark a match as live."""
    match = Match.query.get_or_404(match_id)
    match.is_live = True
    match.status = 'live'
    db.session.commit()

    AdminLogService.log(current_user.id, 'Match marked live', match.id,
                        f'{match.home_team} vs {match.away_team} marked as live',
                        request.remote_addr)
    flash(f'{match.home_team} vs {match.away_team} is now LIVE!', 'success')
    return redirect(url_for('admin.matches'))


@admin_bp.route('/matches/<int:match_id>/feature', methods=['POST'])
@login_required
@admin_required
def toggle_feature_match(match_id):
    """Toggle featured status of a match."""
    match = Match.query.get_or_404(match_id)
    match.is_featured = not match.is_featured
    db.session.commit()

    action = 'featured' if match.is_featured else 'unfeatured'
    flash(f'Match {action}: {match.home_team} vs {match.away_team}', 'info')
    return redirect(url_for('admin.matches'))


@admin_bp.route('/matches/<int:match_id>/suspend', methods=['POST'])
@login_required
@admin_required
def suspend_match(match_id):
    """Suspend a match (cancel/void)."""
    match = Match.query.get_or_404(match_id)
    match.status = 'cancelled'
    match.is_live = False
    db.session.commit()

    AdminLogService.log(current_user.id, 'Match suspended', match.id,
                        f'{match.home_team} vs {match.away_team} suspended',
                        request.remote_addr)
    flash(f'Match suspended: {match.home_team} vs {match.away_team}', 'warning')
    return redirect(url_for('admin.matches'))


@admin_bp.route('/matches/<int:match_id>/finish', methods=['POST'])
@login_required
@admin_required
def finish_match(match_id):
    """Finish a match and optionally set score."""
    match = Match.query.get_or_404(match_id)
    home_score = request.form.get('home_score', type=int)
    away_score = request.form.get('away_score', type=int)

    if home_score is not None and away_score is not None:
        match.home_score = home_score
        match.away_score = away_score

    match.status = MATCH_FINISHED
    match.is_live = False
    db.session.commit()

    AdminLogService.log(current_user.id, 'Match finished', match.id,
                        f'{match.home_team} {home_score or "?"}-{away_score or "?"} {match.away_team}',
                        request.remote_addr)
    flash(f'Match finished: {match.home_team} vs {match.away_team}', 'success')
    return redirect(url_for('admin.matches'))


@admin_bp.route('/matches/<int:match_id>/odds/close', methods=['POST'])
@login_required
@admin_required
def close_betting(match_id):
    """Close betting for a match."""
    match = Match.query.get_or_404(match_id)
    odds = match.main_odds if hasattr(match, 'main_odds') else None
    if not odds:
        flash('No odds record found for this match.', 'warning')
    else:
        odds.is_closed = True
        db.session.commit()
        flash(f'Betting closed for {match.home_team} vs {match.away_team}', 'success')
    return redirect(url_for('admin.edit_odds', match_id=match_id))


@admin_bp.route('/matches/<int:match_id>/odds/open', methods=['POST'])
@login_required
@admin_required
def open_betting(match_id):
    """Open betting for a match."""
    match = Match.query.get_or_404(match_id)
    odds = match.main_odds if hasattr(match, 'main_odds') else None
    if not odds:
        flash('No odds record found for this match.', 'warning')
    else:
        odds.is_closed = False
        db.session.commit()
        flash(f'Betting opened for {match.home_team} vs {match.away_team}', 'success')
    return redirect(url_for('admin.edit_odds', match_id=match_id))


# =============================================================================
# SPORT MANAGEMENT
# =============================================================================

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


@admin_bp.route('/sports/<int:sport_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_sport(sport_id):
    """Edit a sport."""
    sport = Sport.query.get_or_404(sport_id)
    form = SportForm(obj=sport)

    if form.validate_on_submit():
        sport.name = form.name.data
        sport.slug = form.slug.data
        sport.icon = form.icon.data
        sport.description = form.description.data
        sport.is_active = form.is_active.data
        sport.display_order = form.display_order.data
        db.session.commit()

        AdminLogService.log(current_user.id, 'Sport updated', sport.id,
                            f'Sport: {sport.name}', request.remote_addr)
        flash(f'Sport "{sport.name}" updated.', 'success')
        return redirect(url_for('admin.sports'))

    return render_template('admin/sport_form.html', form=form, sport=sport, edit=True)


@admin_bp.route('/sports/<int:sport_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_sport(sport_id):
    """Delete a sport."""
    sport = Sport.query.get_or_404(sport_id)
    name = sport.name
    db.session.delete(sport)
    db.session.commit()

    AdminLogService.log(current_user.id, 'Sport deleted', None,
                        f'Sport: {name}', request.remote_addr)
    flash(f'Sport "{name}" deleted.', 'success')
    return redirect(url_for('admin.sports'))


# =============================================================================
# LEAGUE MANAGEMENT
# =============================================================================

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


@admin_bp.route('/leagues/<int:league_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_league(league_id):
    """Edit a league."""
    league = League.query.get_or_404(league_id)
    form = LeagueForm(obj=league)
    form.sport_id.choices = [(s.id, s.name) for s in Sport.query.all()]

    if form.validate_on_submit():
        league.sport_id = form.sport_id.data
        league.name = form.name.data
        league.slug = form.slug.data
        league.country = form.country.data
        league.is_active = form.is_active.data
        db.session.commit()

        AdminLogService.log(current_user.id, 'League updated', league.id,
                            f'League: {league.name}', request.remote_addr)
        flash(f'League "{league.name}" updated.', 'success')
        return redirect(url_for('admin.leagues'))

    return render_template('admin/league_form.html', form=form, league=league, edit=True)


@admin_bp.route('/leagues/<int:league_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_league(league_id):
    """Delete a league."""
    league = League.query.get_or_404(league_id)
    name = league.name
    db.session.delete(league)
    db.session.commit()

    AdminLogService.log(current_user.id, 'League deleted', None,
                        f'League: {name}', request.remote_addr)
    flash(f'League "{name}" deleted.', 'success')
    return redirect(url_for('admin.leagues'))


# =============================================================================
# BET MANAGEMENT
# =============================================================================

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


# =============================================================================
# COMMUNITY REVIEWS
# =============================================================================

@admin_bp.route('/reviews')
@login_required
@admin_required
def reviews():
    """List all reviews (from both Review and CommunityReview models)."""
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews.html', reviews=reviews)


@admin_bp.route("/reviews/generate", methods=["POST"])
@login_required
@admin_required
def generate_review_ai():

    data = generate_review()

    review = Review(
        phone_number=data["phone"],
        message=data["review"],
        rating=data["rating"],
        is_visible=True,
        created_by=current_user.id
    )

    db.session.add(review)
    db.session.commit()

    flash("AI review generated successfully.", "success")
    return redirect(url_for("admin.reviews"))

@admin_bp.route('/reviews/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_review():
    """Create a new review."""
    form = ReviewForm()

    if form.validate_on_submit():
        review = Review(
            phone_number=form.phone_number.data,
            message=form.message.data,
            rating=form.rating.data,
            is_visible=form.is_visible.data,
            created_by=current_user.id
        )

        db.session.add(review)
        db.session.commit()

        flash('Review created successfully.', 'success')
        return redirect(url_for('admin.reviews'))

    return render_template(
        'admin/review_form.html',
        form=form,
        title='Create Review'
    )


@admin_bp.route('/reviews/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_review(id):
    """Edit an existing review."""
    review = Review.query.get_or_404(id)
    form = ReviewForm(obj=review)

    if form.validate_on_submit():
        form.populate_obj(review)
        db.session.commit()

        flash('Review updated successfully.', 'success')
        return redirect(url_for('admin.reviews'))

    return render_template(
        'admin/review_form.html',
        form=form,
        title='Edit Review'
    )


@admin_bp.route('/reviews/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_review(id):
    """Delete a review."""
    review = Review.query.get_or_404(id)
    db.session.delete(review)
    db.session.commit()

    flash('Review deleted.', 'success')
    return redirect(url_for('admin.reviews'))


# =============================================================================
# ANNOUNCEMENTS
# =============================================================================

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

        users = User.query.filter_by(is_active=True).all()
        for user in users:
            NotificationService.send(user.id, form.title.data, form.content.data,
                                     NOTIFICATION_ANNOUNCEMENT)

        AdminLogService.log(current_user.id, 'Announcement created', None,
                            f'Announcement: {form.title.data}', request.remote_addr)
        flash('Announcement sent to all users.', 'success')
        return redirect(url_for('admin.announcements'))
    return render_template('admin/announcement_form.html', form=form)


@admin_bp.route('/announcements/<int:announcement_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_announcement(announcement_id):
    """Edit an announcement."""
    announcement = Announcement.query.get_or_404(announcement_id)
    form = AnnouncementForm(obj=announcement)

    if form.validate_on_submit():
        announcement.title = form.title.data
        announcement.content = form.content.data
        announcement.priority = form.priority.data
        announcement.is_active = form.is_active.data
        db.session.commit()

        AdminLogService.log(current_user.id, 'Announcement updated', announcement.id,
                            f'Announcement: {announcement.title}', request.remote_addr)
        flash('Announcement updated.', 'success')
        return redirect(url_for('admin.announcements'))

    return render_template('admin/announcement_form.html', form=form, announcement=announcement, edit=True)


@admin_bp.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_announcement(announcement_id):
    """Delete an announcement."""
    announcement = Announcement.query.get_or_404(announcement_id)
    title = announcement.title
    db.session.delete(announcement)
    db.session.commit()

    AdminLogService.log(current_user.id, 'Announcement deleted', None,
                        f'Announcement: {title}', request.remote_addr)
    flash(f'Announcement "{title}" deleted.', 'success')
    return redirect(url_for('admin.announcements'))


@admin_bp.route('/announcements/<int:announcement_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_announcement(announcement_id):
    """Toggle announcement active status."""
    announcement = Announcement.query.get_or_404(announcement_id)
    announcement.is_active = not announcement.is_active
    db.session.commit()

    action = 'activated' if announcement.is_active else 'deactivated'
    flash(f'Announcement {action}.', 'info')
    return redirect(url_for('admin.announcements'))


# =============================================================================
# PROMOTIONS
# =============================================================================

@admin_bp.route('/promotions')
@login_required
@admin_required
def promotions():
    """Promotions management page."""
    welcome_bonuses = Bonus.query.filter_by(
        bonus_type='welcome'
    ).order_by(Bonus.created_at.desc()).limit(20).all()

    promo_bonuses = Bonus.query.filter_by(
        bonus_type='promo'
    ).order_by(Bonus.created_at.desc()).limit(20).all()

    active_bonuses_count = Bonus.query.filter_by(
        is_active=True,
        is_expired=False
    ).count()

    total_bonus_amount = db.session.query(
        func.coalesce(func.sum(Bonus.amount), 0)
    ).filter(
        Bonus.is_active == True
    ).scalar()

    users = User.query.order_by(User.username).all()

    return render_template(
        'admin/promotions.html',
        welcome_bonuses=welcome_bonuses,
        promo_bonuses=promo_bonuses,
        active_bonuses_count=active_bonuses_count,
        total_bonus_amount=float(total_bonus_amount or 0),
        users=users
    )


@admin_bp.route('/promotions/bonus/send', methods=['POST'])
@login_required
@admin_required
def send_bonus():
    """Send bonus to a user."""
    user_id = request.form.get('user_id', type=int)
    amount = request.form.get('amount', type=float)
    bonus_type = request.form.get('bonus_type', 'promo')
    description = request.form.get('description', 'Promotional bonus')

    if not user_id or not amount or amount <= 0:
        flash('Invalid input.', 'danger')
        return redirect(url_for('admin.promotions'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.promotions'))

    if hasattr(user.wallet, 'add_bonus'):
        user.wallet.add_bonus(amount)

    bonus = Bonus(
        user_id=user.id,
        bonus_type=bonus_type,
        amount=amount,
        is_active=True,
    )
    db.session.add(bonus)

    txn = WalletTransaction(
        user_id=user.id,
        transaction_type='bonus',
        amount=amount,
        balance_before=user.wallet.balance if user.wallet else 0,
        balance_after=user.wallet.balance if user.wallet else 0,
        description=description,
    )
    db.session.add(txn)

    NotificationService.send(user.id, '🎉 Bonus Received!',
                             f'You have received a bonus of KES {amount:,.2f}! {description}',
                             'promotion')

    AdminLogService.log(current_user.id, 'Bonus sent', user.id,
                        f'{bonus_type} bonus of KES {amount:,.2f} to {user.username}',
                        request.remote_addr)
    db.session.commit()
    flash(f'KES {amount:,.2f} bonus sent to {user.username}.', 'success')
    return redirect(url_for('admin.promotions'))


# =============================================================================
# REPORTS
# =============================================================================

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """Reports dashboard."""
    period = request.args.get('period', 'daily')

    today = datetime.now(timezone.utc).date()
    if period == 'weekly':
        start_date = today - timedelta(days=7)
    elif period == 'monthly':
        start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=1)

    revenue_report = db.session.query(
        func.date(Bet.created_at).label('date'),
        func.count(Bet.id).label('bets'),
        func.coalesce(func.sum(Bet.stake), 0).label('stakes'),
        func.coalesce(func.sum(Bet.winnings), 0).label('winnings')
    ).filter(
        Bet.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc),
        Bet.status.in_([BET_WON, BET_LOST])
    ).group_by(func.date(Bet.created_at)).order_by(func.date(Bet.created_at)).all()

    popular_matches = db.session.query(
        Match.id,
        Match.home_team,
        Match.away_team,
        func.count(BetSelection.id).label('selection_count')
    ).join(BetSelection, BetSelection.match_id == Match.id)\
     .group_by(Match.id, Match.home_team, Match.away_team)\
     .order_by(func.count(BetSelection.id).desc())\
     .limit(10).all()

    top_depositors = db.session.query(
        User.id, User.username,
        func.coalesce(func.sum(Deposit.amount), 0).label('total_deposits')
    ).join(Deposit, Deposit.user_id == User.id)\
     .filter(Deposit.status == REQUEST_APPROVED)\
     .group_by(User.id, User.username)\
     .order_by(func.coalesce(func.sum(Deposit.amount), 0).desc())\
     .limit(10).all()

    top_bettors = db.session.query(
        User.id, User.username,
        func.count(Bet.id).label('total_bets'),
        func.coalesce(func.sum(Bet.stake), 0).label('total_stakes')
    ).join(Bet, Bet.user_id == User.id)\
     .group_by(User.id, User.username)\
     .order_by(func.count(Bet.id).desc())\
     .limit(10).all()

    return render_template('admin/reports.html',
                           revenue=revenue_report,
                           popular_matches=popular_matches,
                           top_depositors=top_depositors,
                           top_bettors=top_bettors,
                           selected_period=period)


# =============================================================================
# AUDIT LOGS
# =============================================================================

@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc())\
        .paginate(page=page, per_page=30, error_out=False)
    return render_template('admin/audit_logs.html', logs=logs)


@admin_bp.route('/activity-logs')
@login_required
@admin_required
def activity_logs():
    """View admin activity logs."""
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    admin_id = request.args.get('admin_id', type=int)

    query = AdminLog.query
    if action_filter:
        query = query.filter_by(action=action_filter)
    if admin_id:
        query = query.filter_by(admin_id=admin_id)

    logs = query.order_by(AdminLog.created_at.desc())\
        .paginate(page=page, per_page=30, error_out=False)

    admins = User.query.filter(User.is_admin == True).all()

    actions = db.session.query(AdminLog.action).distinct().order_by(AdminLog.action).all()
    actions = [a[0] for a in actions]

    return render_template('admin/activity_logs.html', logs=logs, admins=admins,
                           actions=actions,
                           action_filter=action_filter, selected_admin_id=admin_id)


@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    page = request.args.get('page', 1, type=int)
    logs = AdminLog.query.order_by(AdminLog.created_at.desc())\
        .paginate(page=page, per_page=30, error_out=False)
    return render_template('admin/logs.html', logs=logs)


# =============================================================================
# ANALYTICS API
# =============================================================================

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    """Returns JSON data for charts."""
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    daily_deposits = db.session.query(
        func.date(Deposit.created_at).label('date'),
        func.coalesce(func.sum(Deposit.amount), 0).label('total')
    ).filter(
        Deposit.status == REQUEST_APPROVED,
        Deposit.created_at >= thirty_days_ago
    ).group_by(func.date(Deposit.created_at)).all()

    daily_registrations = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= thirty_days_ago
             ).group_by(func.date(User.created_at)).all()

    bets_by_status = db.session.query(
        Bet.status, func.count(Bet.id)
    ).group_by(Bet.status).all()

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


# =============================================================================
# SETTINGS
# =============================================================================

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """Site settings page."""
    form = SystemSettingsForm()

    if form.validate_on_submit():
        settings_map = {
            'site_name': form.site_name.data,
            'currency': form.currency.data,
            'currency_symbol': form.currency_symbol.data,
            'minimum_deposit': form.minimum_deposit.data,
            'minimum_withdrawal': form.minimum_withdrawal.data,
            'minimum_stake': form.minimum_stake.data,
            'maximum_stake': form.maximum_stake.data,
            'welcome_bonus_amount': form.welcome_bonus_amount.data,
            'welcome_bonus_min_deposit': form.welcome_bonus_min_deposit.data,
            'maintenance_mode': str(form.maintenance_mode.data),
            'maintenance_message': form.maintenance_message.data or '',
        }

        for key, value in settings_map.items():
            setting = SystemSettings.query.filter_by(key=key).first()
            if setting:
                setting.value = str(value)
            else:
                db.session.add(SystemSettings(key=key, value=str(value)))

        if hasattr(form, 'site_logo') and form.site_logo.data:
            from werkzeug.utils import secure_filename
            import os
            logo_file = form.site_logo.data
            filename = secure_filename(logo_file.filename)
            logo_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
            logo_file.save(logo_path)

            logo_setting = SystemSettings.query.filter_by(key='site_logo').first()
            if logo_setting:
                logo_setting.value = filename
            else:
                db.session.add(SystemSettings(key='site_logo', value=filename))

        db.session.commit()
        AdminLogService.log(current_user.id, 'Settings updated', None,
                            'System settings updated', request.remote_addr)
        flash('Settings updated successfully.', 'success')
        return redirect(url_for('admin.settings'))

    all_settings = {s.key: s.value for s in SystemSettings.query.all()}
    for key in ['site_name', 'currency', 'currency_symbol', 'minimum_deposit',
                'minimum_withdrawal', 'minimum_stake', 'maximum_stake',
                'welcome_bonus_amount', 'welcome_bonus_min_deposit',
                'maintenance_mode', 'maintenance_message']:
        if key in all_settings and hasattr(form, key):
            if key == 'maintenance_mode':
                getattr(form, key).data = all_settings[key].lower() == 'true'
            elif key in ['minimum_deposit', 'minimum_withdrawal', 'minimum_stake',
                         'maximum_stake', 'welcome_bonus_amount', 'welcome_bonus_min_deposit']:
                try:
                    getattr(form, key).data = float(all_settings[key])
                except (ValueError, TypeError):
                    pass
            else:
                getattr(form, key).data = all_settings[key]

    return render_template('admin/settings.html', form=form)