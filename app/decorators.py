"""Decorators for permission checking and utility."""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """Require admin role to access a view."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin and not current_user.has_role('admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    """Require super admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.has_role('super_admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def suspended_check(f):
    """Check if user is suspended."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and current_user.is_suspended:
            flash('Your account has been suspended. Please contact support.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated_function