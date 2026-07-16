"""Payment forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SubmitField, PasswordField
from wtforms.validators import Optional, DataRequired


class PaymentConfigForm(FlaskForm):
    mpesa_consumer_key = StringField('M-Pesa Consumer Key', validators=[Optional()])
    mpesa_consumer_secret = PasswordField('M-Pesa Consumer Secret', validators=[Optional()])
    mpesa_passkey = PasswordField('M-Pesa Passkey', validators=[Optional()])
    mpesa_shortcode = StringField('M-Pesa Shortcode', validators=[Optional()])
    mpesa_environment = SelectField('Environment', choices=[('sandbox', 'Sandbox'), ('production', 'Production')])
    enable_mpesa = BooleanField('Enable M-Pesa')
    enable_card = BooleanField('Enable Card Payments')
    submit = SubmitField('Save Configuration')