"""Betting forms."""
from flask_wtf import FlaskForm
from wtforms import FloatField, HiddenField, SubmitField, BooleanField
from wtforms.validators import DataRequired, NumberRange


class PlaceBetForm(FlaskForm):
    stake = FloatField('Stake Amount (KES)', validators=[DataRequired(), NumberRange(min=10)])
    use_bonus = BooleanField('Use Bonus Balance')
    selections_json = HiddenField('Selections')
    submit = SubmitField('Place Bet')