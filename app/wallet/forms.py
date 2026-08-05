"""Wallet forms."""

from flask_wtf import FlaskForm
from wtforms import FloatField, SelectField, StringField, SubmitField
from wtforms.validators import (
    DataRequired,
    NumberRange,
    Optional,
    Length,
)


class DepositForm(FlaskForm):
    """Wallet deposit form."""

    amount = FloatField(
        "Amount (KES)",
        validators=[
            DataRequired(),
            NumberRange(min=50),
        ],
    )

    payment_method = SelectField(
        "Payment Method",
        choices=[
            ("palpluss", "M-Pesa"),
        ],
        validators=[DataRequired()],
    )

    phone_number = StringField(
        "Phone Number",
        validators=[
            DataRequired(),
            Length(min=8, max=20),
        ],
    )

    submit = SubmitField("Deposit Now")


class WithdrawalForm(FlaskForm):
    """Wallet withdrawal form."""

    amount = FloatField(
        "Amount (KES)",
        validators=[
            DataRequired(),
            NumberRange(min=100),
        ],
    )

    payment_method = SelectField(
        "Withdrawal Method",
        choices=[
            ("mpesa", "M-Pesa"),
            ("airtel_money", "Airtel Money"),
            ("bank_transfer", "Bank Transfer"),
        ],
        validators=[DataRequired()],
    )

    phone_number = StringField(
        "Phone Number",
        validators=[
            Optional(),
            Length(min=8, max=20),
        ],
    )

    account_name = StringField(
        "Account Name",
        validators=[
            Optional(),
            Length(min=2, max=100),
        ],
    )

    account_number = StringField(
        "Account Number",
        validators=[
            Optional(),
            Length(min=2, max=100),
        ],
    )

    submit = SubmitField("Request Withdrawal")