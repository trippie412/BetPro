"""Reports routes for admin analytics."""
from datetime import datetime, timezone, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Deposit, Withdrawal, Bet, WalletTransaction
from app.reports import reports_bp
from app.decorators import admin_required
from app.constants import *
from sqlalchemy import func


@reports_bp.route('/')
@login_required
@admin_required
def index():
    return render_template('reports/index.html')


@reports_bp.route('/revenue')
@login_required
@admin_required
def revenue():
    period = request.args.get('period', 'monthly')

    if period == 'daily':
        days = 30
    elif period == 'weekly':
        days = 90
    else:
        days = 365

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    deposits = db.session.query(
        func.date(Deposit.created_at).label('date'),
        func.coalesce(func.sum(Deposit.amount), 0).label('total')
    ).filter(
        Deposit.status == REQUEST_APPROVED,
        Deposit.created_at >= start_date
    ).group_by(func.date(Deposit.created_at)).order_by(func.date(Deposit.created_at)).all()

    withdrawals = db.session.query(
        func.date(Withdrawal.created_at).label('date'),
        func.coalesce(func.sum(Withdrawal.amount), 0).label('total')
    ).filter(
        Withdrawal.status == REQUEST_APPROVED,
        Withdrawal.created_at >= start_date
    ).group_by(func.date(Withdrawal.created_at)).order_by(func.date(Withdrawal.created_at)).all()

    bets = db.session.query(
        func.date(Bet.created_at).label('date'),
        func.count(Bet.id).label('count'),
        func.coalesce(func.sum(Bet.stake), 0).label('total_stake')
    ).filter(
        Bet.created_at >= start_date
    ).group_by(func.date(Bet.created_at)).order_by(func.date(Bet.created_at)).all()

    return jsonify({
        'deposits': [{'date': str(d.date), 'total': float(d.total)} for d in deposits],
        'withdrawals': [{'date': str(w.date), 'total': float(w.total)} for w in withdrawals],
        'bets': [{'date': str(b.date), 'count': b.count, 'total_stake': float(b.total_stake)} for b in bets],
    })


@reports_bp.route('/users')
@login_required
@admin_required
def users():
    period = request.args.get('period', 'monthly')

    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True, is_suspended=False).count()
    suspended = User.query.filter_by(is_suspended=True).count()
    new_today = User.query.filter(
        func.date(User.created_at) == func.date(func.now())
    ).new_today = User.query.filter(
        func.date(User.created_at) == func.date(func.now())
    ).count()

    return jsonify({
        'total_users': total_users,
        'active_users': active_users,
        'suspended': suspended,
        'new_today': new_today,
    })


@reports_bp.route('/top-users')
@login_required
@admin_required
def top_users():
    limit = request.args.get('limit', 10, type=int)

    by_deposits = db.session.query(
        User.username, User.full_name,
        func.coalesce(func.sum(Deposit.amount), 0).label('total')
    ).join(Deposit, User.id == Deposit.user_id)\
     .filter(Deposit.status == REQUEST_APPROVED)\
     .group_by(User.id, User.username, User.full_name)\
     .order_by(func.coalesce(func.sum(Deposit.amount), 0).desc())\
     .limit(limit).all()

    by_bets = db.session.query(
        User.username, User.full_name,
        func.count(Bet.id).label('count'),
        func.coalesce(func.sum(Bet.stake), 0).label('total_stake')
    ).join(Bet, User.id == Bet.user_id)\
     .group_by(User.id, User.username, User.full_name)\
     .order_by(func.count(Bet.id).desc())\
     .limit(limit).all()

    return jsonify({
        'by_deposits': [{'username': u.username, 'name': u.full_name, 'total': float(u.total)} for u in by_deposits],
        'by_bets': [{'username': u.username, 'name': u.full_name, 'count': u.count, 'total_stake': float(u.total_stake)} for u in by_bets],
    })


@reports_bp.route('/bonus')
@login_required
@admin_required
def bonus():
    from app.models import Bonus
    total_bonus = db.session.query(func.coalesce(func.sum(Bonus.amount), 0)).scalar()
    welcome_bonus = db.session.query(func.coalesce(func.sum(Bonus.amount), 0))\
        .filter(Bonus.bonus_type == 'welcome').scalar()
    users_with_bonus = db.session.query(func.count(func.distinct(Bonus.user_id))).scalar()

    return jsonify({
        'total_bonus': float(total_bonus),
        'welcome_bonus': float(welcome_bonus),
        'users_with_bonus': users_with_bonus,
    })