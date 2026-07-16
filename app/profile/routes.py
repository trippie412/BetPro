"""User profile routes."""
import os
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import User, Bet, WalletTransaction
from app.profile import profile_bp
from app.profile.forms import ProfileUpdateForm, ChangePasswordForm
from app.decorators import suspended_check
from app.utils import save_picture


@profile_bp.route('/')
@login_required
@suspended_check
def index():
    recent_bets = Bet.query.filter_by(user_id=current_user.id)\
        .order_by(Bet.created_at.desc()).limit(5).all()
    recent_transactions = WalletTransaction.query.filter_by(user_id=current_user.id)\
        .order_by(WalletTransaction.created_at.desc()).limit(5).all()
    return render_template('profile/index.html',
                         recent_bets=recent_bets,
                         recent_transactions=recent_transactions)


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
@suspended_check
def edit():
    form = ProfileUpdateForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.phone = form.phone.data
        current_user.country = form.country.data

        if form.profile_picture.data:
            picture_file = save_picture(form.profile_picture.data)
            current_user.profile_picture = picture_file

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.index'))

    return render_template('profile/edit.html', form=form)


@profile_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
@suspended_check
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('profile/change_password.html', form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Password changed successfully!', 'success')
        return redirect(url_for('profile.index'))

    return render_template('profile/change_password.html', form=form)