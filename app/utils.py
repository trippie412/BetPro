"""Utility functions for the application."""
import os
import uuid
import random
import string
from datetime import datetime, timedelta
from PIL import Image
from flask import current_app


def generate_reference(prefix='BET'):
    """Generate a unique reference number."""
    timestamp = datetime.now().strftime('%y%m%d%H%M%S')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f'{prefix}-{timestamp}-{random_part}'


def generate_transaction_code():
    """Generate a transaction code like M-Pesa format."""
    return ''.join(random.choices(string.digits, k=12))


def save_picture(form_picture, folder='profile_pictures', output_size=(300, 300)):
    """Save uploaded picture with resizing."""
    random_hex = uuid.uuid4().hex
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static', 'uploads', folder, picture_fn)

    os.makedirs(os.path.dirname(picture_path), exist_ok=True)

    if output_size:
        try:
            i = Image.open(form_picture)
            i.thumbnail(output_size)
            i.save(picture_path)
        except Exception:
            form_picture.save(picture_path)
    else:
        form_picture.save(picture_path)

    return picture_fn


def format_currency(amount, currency='KES'):
    """Format currency amount."""
    return f'{currency} {amount:,.2f}'


def calculate_odds(probability):
    """Convert probability to decimal odds."""
    if probability <= 0 or probability >= 1:
        return 0
    return round(1 / probability, 2)


def time_ago(dt):
    """Human readable time ago."""
    now = datetime.utcnow()
    diff = now - dt

    seconds = diff.total_seconds()
    if seconds < 60:
        return 'just now'
    minutes = seconds // 60
    if minutes < 60:
        return f'{int(minutes)}m ago'
    hours = minutes // 60
    if hours < 24:
        return f'{int(hours)}h ago'
    days = hours // 24
    if days < 30:
        return f'{int(days)}d ago'
    months = days // 30
    if months < 12:
        return f'{int(months)}mo ago'
    years = months // 12
    return f'{int(years)}y ago'


def calculate_wagering_requirement(bonus_amount, multiplier=10):
    """Calculate wagering requirement for a bonus."""
    return round(bonus_amount * multiplier, 2)


def is_safe_url(target):
    """Check if a URL is safe for redirects."""
    from urllib.parse import urlparse, urljoin
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc