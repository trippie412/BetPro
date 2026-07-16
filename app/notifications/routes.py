"""Notification routes."""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Notification
from app.notifications import notifications_bp
from app.decorators import suspended_check


@notifications_bp.route('/')
@login_required
@suspended_check
def index():
    page = request.args.get('page', 1, type=int)
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=20, error_out=False)
    return render_template('notifications/index.html', notifications=notifs)


@notifications_bp.route('/read/<int:notification_id>', methods=['POST'])
@login_required
def mark_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@notifications_bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({Notification.is_read: True})
    db.session.commit()
    return jsonify({'success': True, 'count': 0})