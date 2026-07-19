"""Application configuration with multiple environments."""
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration shared by all environments."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'betpro-dev-secret-key-change-in-production-2026')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'database', 'betpro.db'))

    # Flask-Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@betpro.com')

    # Session
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    

    # Flask-Session configuration
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = os.path.join(basedir, "flask_session")
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    # Uploads
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

    # Rate limiting
    RATELIMIT_DEFAULT = '100/hour'
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')

    # Betting
    MINIMUM_DEPOSIT = float(os.environ.get('MINIMUM_DEPOSIT', 50))
    MINIMUM_WITHDRAWAL = float(os.environ.get('MINIMUM_WITHDRAWAL', 100))
    MAXIMUM_STAKE = float(os.environ.get('MAXIMUM_STAKE', 100000))
    MINIMUM_STAKE = float(os.environ.get('MINIMUM_STAKE', 10))
    WELCOME_BONUS_AMOUNT = float(os.environ.get('WELCOME_BONUS_AMOUNT', 1000))
    WELCOME_BONUS_MIN_DEPOSIT = float(os.environ.get('WELCOME_BONUS_MIN_DEPOSIT', 500))

    # Pagination
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE', 20))

    # Currency
    CURRENCY_SYMBOL = 'KES'
    CURRENCY_CODE = 'KES'
    
    # =========================================================================
    # API-FOOTBALL Configuration
    # =========================================================================
    API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY")
    API_FOOTBALL_URL = os.environ.get(
        "API_FOOTBALL_URL",
        "https://v3.football.api-sports.io"
    )
    
    PESAPAL_BASE_URL = os.getenv("PESAPAL_BASE_URL")
    PESAPAL_CONSUMER_KEY = os.getenv("PESAPAL_CONSUMER_KEY")
    PESAPAL_CONSUMER_SECRET = os.getenv("PESAPAL_CONSUMER_SECRET")

    # =========================================================================
    # M-Pesa Daraja API Configuration
    # =========================================================================
    MPESA_ENV = os.environ.get('MPESA_ENV', 'sandbox')  # 'sandbox' or 'production'
    MPESA_CONSUMER_KEY = os.environ.get('MPESA_CONSUMER_KEY', 'D10sk9jEdeA1tj2pmsuQylamoJP6vAHXOOMmMnzrMcyk2Y8G')
    MPESA_CONSUMER_SECRET = os.environ.get('MPESA_CONSUMER_SECRET', 'Me4C4kcNKneYHLGKWDH3AQAf3Bz4NIGMszGTOlUOEWXiIDPbdDhrEL0JNSREGRkG')
    MPESA_PASSKEY = os.environ.get('MPESA_PASSKEY', 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919')
    MPESA_SHORTCODE = os.environ.get('MPESA_SHORTCODE', '174379')
    MPESA_TRANSACTION_TYPE = os.environ.get('MPESA_TRANSACTION_TYPE', 'CustomerPayBillOnline')

    # Callback URL - must be HTTPS and publicly reachable
    # For local dev use ngrok: ngrok http 5000
    MPESA_CALLBACK_URL = os.environ.get(
       "MPESA_CALLBACK_URL",
       "https://your-domain.com/payments/callback/mpesa"
    )

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'database', 'betpro.db'))
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
    )

    SESSION_COOKIE_SECURE = True

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        import logging
        app.logger.setLevel(logging.INFO)

        if not os.environ.get("VERCEL"):
            from logging.handlers import RotatingFileHandler

            os.makedirs("logs", exist_ok=True)

            file_handler = RotatingFileHandler(
                "logs/betpro.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=10,
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s: %(message)s "
                    "[in %(pathname)s:%(lineno)d]"
                )
            )
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

        app.logger.info("BetPro startup")
        
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}