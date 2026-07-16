"""Wallet forms."""
from flask_wtf import FlaskForm
from wtforms import FloatField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional, Length


class DepositForm(FlaskForm):
    amount = FloatField('Amount (KES)', validators=[DataRequired(), NumberRange(min=50)])
    payment_method = SelectField('Payment Method', choices=[
        ('mpesa', 'M-Pesa'), ('airtel_money', 'Airtel Money'),
        ('bank_transfer', 'Bank Transfer'), ('card', 'Debit/Credit Card')
    ], validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(8, 20)])
    submit = SubmitField('Deposit Now')


class WithdrawalForm(FlaskForm):
    amount = FloatField('Amount (KES)', validators=[DataRequired(), NumberRange(min=100)])
    payment_method = SelectField('Payment Method', choices=[
        ('mpesa', 'M-Pesa'), ('airtel_money', 'Airtel Money'),
        ('bank_transfer', 'Bank Transfer')
    ], validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[Optional(), Length(8, 20)])
    account_name = StringField('Account Name', validators=[Optional(), Length(2, 100)])
    account_number = StringField('Account Number', validators=[Optional(), Length(2, 100)])
    submit = SubmitField('Request Withdrawal')