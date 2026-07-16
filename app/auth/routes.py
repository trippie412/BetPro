"""Authentication routes."""
from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Wallet, AuditLog
from app.auth import auth_bp
from app.auth.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from app.decorators import suspended_check
from app.services import AuditService


@auth_bp.route('/login', methods=['GET', 'POST'])
@suspended_check
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.username.data)
        ).first()

        if user and user.check_password(form.password.data):
            if user.is_suspended:
                flash('Your account has been suspended. Please contact support.', 'danger')
                return render_template('auth/login.html', form=form)

            login_user(user, remember=form.remember.data)
            user.last_login = datetime.now(timezone.utc)

            AuditService.log(user.id, 'User logged in', 'auth', user.id,
                             f'User {user.username} logged in from {request.remote_addr}',
                             request.remote_addr, request.user_agent.string)

            db.session.commit()

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data,
            country=form.country.data,
        )
        user.set_password(form.password.data)

        # Assign default user role
        user_role = Role.query.filter_by(name='user').first()
        if user_role:
            user.roles.append(user_role)

        db.session.add(user)
        db.session.flush()

        # Create wallet
        wallet = Wallet(user_id=user.id, balance=0.0, bonus_balance=0.0)
        db.session.add(wallet)

        AuditService.log(user.id, 'User registered', 'auth', user.id,
                         f'New user {user.username} registered',
                         request.remote_addr, request.user_agent.string)

        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    AuditService.log(current_user.id, 'User logged out', 'auth', current_user.id,
                     f'User {current_user.username} logged out',
                     request.remote_addr, request.user_agent.string)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # In production, send email with reset link
            flash('A password reset link has been sent to your email.', 'info')
        else:
            flash('If that email is registered, a reset link will be sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    form = ResetPasswordForm()
    if form.validate_on_submit():
        # In production, verify token and reset password
        flash('Password has been reset successfully.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form, token=token)


# Import here to avoid circular imports
from app.models import Role