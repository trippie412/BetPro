"""Initialize the Flask application using the application factory pattern."""
import os
from flask import Flask, redirect, url_for
from app.extensions import db, login_manager, migrate, csrf, mail, limiter, sess
from config import config


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(
    __name__,
    instance_relative_config=True,
    template_folder="../templates",
    static_folder="../static"
)
    app.config.from_object(config[config_name])
    print("=" * 50)
    print("CONFIG NAME:", config_name)
    print("DATABASE URI:", app.config["SQLALCHEMY_DATABASE_URI"])
    print("VERCEL:", os.environ.get("VERCEL"))
    print("=" * 50)
    config[config_name].init_app(app)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Ensure upload directories exist
    if not os.environ.get("VERCEL"):
        _ensure_directories(app)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Only initialize Flask-Session when using filesystem sessions
    if not os.environ.get("VERCEL"):
        sess.init_app(app)
    
     # Register blueprints
    _register_blueprints(app)

    @app.route("/")
    def home():
        return redirect(url_for("auth.login"))

    # Register error handlers
    _register_error_handlers(app)

    # Register context processors
    _register_context_processors(app)

    # Load user loader
    _load_user_loader()

    # Initialize database only when not running on Vercel
    with app.app_context():
        from app import models  # noqa

        if not os.environ.get("VERCEL"):
           db.create_all()
           _seed_initial_data(app)

    return app

    


def _ensure_directories(app):
    """Ensure all required directories exist."""
    dirs = [
        os.path.join(app.root_path, 'static', 'uploads', 'profile_pictures'),
        os.path.join(app.root_path, 'static', 'uploads', 'documents'),
        os.path.join(app.root_path, 'database'),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def _register_blueprints(app):
    """Register all Flask blueprints."""
    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.dashboard.routes import dashboard_bp
    from app.wallet.routes import wallet_bp
    from app.betting.routes import betting_bp
    from app.matches.routes import matches_bp
    from app.sports.routes import sports_bp
    from app.payments.routes import payments_bp
    from app.notifications.routes import notifications_bp
    from app.profile.routes import profile_bp
    from app.reports.routes import reports_bp
    from app.api.routes import api_bp
    from app.errors.routes import errors_bp

    blueprints = [
        (auth_bp, '/auth'),
        (admin_bp, '/admin'),
        (dashboard_bp, '/dashboard'),
        (wallet_bp, '/wallet'),
        (betting_bp, '/betting'),
        (matches_bp, '/matches'),
        (sports_bp, '/sports'),
        (payments_bp, '/payments'),
        (notifications_bp, '/notifications'),
        (profile_bp, '/profile'),
        (reports_bp, '/reports'),
        (api_bp, '/api/v1'),
        (errors_bp, '/errors'),
    ]

    for bp, url_prefix in blueprints:
        app.register_blueprint(bp, url_prefix=url_prefix)


def _register_error_handlers(app):
    """Register custom error handlers."""
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def ratelimit_error(error):
        from flask import render_template
        return render_template('errors/429.html'), 429


def _register_context_processors(app):
    """Register context processors for templates."""
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.models import Notification, Sport
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        sports = Sport.query.filter_by(is_active=True).order_by(Sport.display_order).all()
        return {
            'unread_notifications': unread_count,
            'sports': sports,
            'app_name': 'BetPro',
            'currency': 'KES',
            'currency_symbol': 'KSh',
        }


def _load_user_loader():
    """Load the user loader for Flask-Login."""
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


def _seed_initial_data(app):
    """Seed initial data if database is empty."""
    from app.models import Sport, Role, SystemSettings, Match

    # Create default roles
    if Role.query.count() == 0:
        roles = [
            Role(name='user', description='Regular user'),
            Role(name='admin', description='Administrator'),
            Role(name='super_admin', description='Super Administrator'),
        ]
        db.session.add_all(roles)
        db.session.commit()

    # Create default sports
    if Sport.query.count() == 0:
        sports_data = [
            Sport(name='Football', slug='football', icon='fa-futbol', display_order=1),
            Sport(name='Basketball', slug='basketball', icon='fa-basketball-ball', display_order=2),
            Sport(name='Tennis', slug='tennis', icon='fa-table-tennis', display_order=3),
            Sport(name='Volleyball', slug='volleyball', icon='fa-volleyball-ball', display_order=4),
            Sport(name='Rugby', slug='rugby', icon='fa-football-ball', display_order=5),
            Sport(name='eSports', slug='esports', icon='fa-gamepad', display_order=6),
            Sport(name='Virtual Games', slug='virtual-games', icon='fa-robot', display_order=7),
        ]
        db.session.add_all(sports_data)
        db.session.commit()

    # Seed sample match data
    from app.services import LiveDataService
    if Match.query.count() == 0:
        LiveDataService.sync_matches_to_db()