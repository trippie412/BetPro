"""Error page routes."""
from flask import render_template
from app.errors import errors_bp


@errors_bp.app_errorhandler(404)
def not_found(error):
    return render_template('errors/404.html'), 404


@errors_bp.app_errorhandler(403)
def forbidden(error):
    return render_template('errors/403.html'), 403


@errors_bp.app_errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


@errors_bp.app_errorhandler(429)
def ratelimit_error(error):
    return render_template('errors/429.html'), 429