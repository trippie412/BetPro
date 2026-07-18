"""User dashboard routes."""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Bet, Notification, Wallet, Review, Match, Sport
from app.dashboard import dashboard_bp
from app.decorators import suspended_check
from app.constants import *
from datetime import datetime, timezone, timedelta


@dashboard_bp.route('/')
@login_required
@suspended_check
def index():
    wallet = current_user.wallet
    recent_bets = Bet.query.filter_by(user_id=current_user.id)\
        .order_by(Bet.created_at.desc()).limit(5).all()

    # Notification stats
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

    # Bet stats
    total_bets = Bet.query.filter_by(user_id=current_user.id).count()
    won_bets = Bet.query.filter_by(user_id=current_user.id, status=BET_WON).count()
    lost_bets = Bet.query.filter_by(user_id=current_user.id, status=BET_LOST).count()
    pending_bets = Bet.query.filter_by(user_id=current_user.id, status=BET_PENDING).count()

    # Recent transactions
    from app.models import WalletTransaction
    recent_transactions = WalletTransaction.query.filter_by(user_id=current_user.id)\
        .order_by(WalletTransaction.created_at.desc()).limit(5).all()

    # Featured matches
    featured_matches = Match.query.filter_by(is_featured=True, status=MATCH_SCHEDULED)\
        .order_by(Match.match_date.asc()).limit(4).all()

    # Live matches
    live_matches = Match.query.filter_by(is_live=True, status=MATCH_LIVE).all()

    # Chart data - last 7 days deposits
    from app.services import WalletService
    chart_labels = []
    chart_deposits = []
    chart_bets = []
    
    for i in range(6, -1, -1):
        day = datetime.now(timezone.utc) - timedelta(days=i)
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

    chart_labels.append(day.strftime('%a'))

    dep_total = db.session.query(
        db.func.coalesce(db.func.sum(WalletTransaction.amount), 0)
    ).filter(
        WalletTransaction.user_id == current_user.id,
        WalletTransaction.transaction_type == TRANSACTION_DEPOSIT,
        WalletTransaction.created_at.between(day_start, day_end)
    ).scalar()

    chart_deposits.append(float(dep_total))

    bet_total = db.session.query(
        db.func.coalesce(db.func.sum(Bet.stake), 0)
    ).filter(
        Bet.user_id == current_user.id,
        Bet.created_at.between(day_start, day_end)
    ).scalar()

    chart_bets.append(float(bet_total))
    
    
    recent_notifs = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).limit(5).all()
    
    community_reviews = (
       Review.query
       .filter_by(is_visible=True)
       .order_by(Review.created_at.desc())
       .limit(8)
       .all()
    )

    return render_template(
        "dashboard/index.html",
        wallet=wallet,
        recent_bets=recent_bets,
        unread_count=unread_count,
        recent_notifs=recent_notifs,
        total_bets=total_bets,
        won_bets=won_bets,
        lost_bets=lost_bets,
        pending_bets=pending_bets,
        recent_transactions=recent_transactions,
        featured_matches=featured_matches,
        live_matches=live_matches,
        chart_labels=chart_labels,
        chart_deposits=chart_deposits,
        chart_bets=chart_bets,
        community_reviews=community_reviews,)


@dashboard_bp.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('dashboard/notifications.html', notifications=notifications)


@dashboard_bp.route('/mark-notification-read/<int:notification_id>')
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@dashboard_bp.route('/mark-all-read')
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({Notification.is_read: True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('dashboard.index'))