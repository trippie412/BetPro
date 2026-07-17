"""Decorators for admin panel routes."""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(f):
    """Require that the current user is an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin and not current_user.has_role('admin') and not current_user.has_role('super_admin'):
            flash('You do not have permission to access this area.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    """Require that the current user is a super admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin and not current_user.has_role('super_admin'):
            flash('Super administrator access required.', 'danger')
            return redirect(url_for('admin.index'))
        return f(*args, **kwargs)
    return decorated_function