from flask import Blueprint
admin_bp = Blueprint('admin', __name__, template_folder='../../templates/admin')

"""Admin Blueprint for BetPro."""
from flask import Blueprint

admin_bp = Blueprint(
    'admin',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/admin'
)

from app.admin import routes