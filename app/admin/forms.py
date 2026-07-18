"""Forms for the admin panel."""
from datetime import datetime, timezone
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, FloatField, IntegerField,
                     TextAreaField, SelectField, BooleanField, DateTimeField,
                     FileField,SubmitField, HiddenField)
from wtforms.validators import DataRequired, Optional, NumberRange, Length, Email


class MatchForm(FlaskForm):
    """Form for creating/editing matches."""
    sport_id = SelectField('Sport', coerce=int, validators=[DataRequired()])
    league_id = SelectField('League', coerce=int, validators=[DataRequired()])
    home_team = StringField('Home Team', validators=[DataRequired(), Length(max=120)])
    away_team = StringField('Away Team', validators=[DataRequired(), Length(max=120)])
    match_date = DateTimeField('Match Date & Time', format='%Y-%m-%dT%H:%M',
                               validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('finished', 'Finished'),
        ('postponed', 'Postponed'),
        ('cancelled', 'Cancelled'),
    ], default='scheduled')
    is_featured = BooleanField('Featured Match')
    is_live = BooleanField('Live Match')
    home_score = IntegerField('Home Score', validators=[Optional()])
    away_score = IntegerField('Away Score', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])


class OddsForm(FlaskForm):
    """Form for editing match odds."""
    home_win = FloatField('Home Win', validators=[Optional(), NumberRange(min=1.0)])
    draw = FloatField('Draw', validators=[Optional(), NumberRange(min=1.0)])
    away_win = FloatField('Away Win', validators=[Optional(), NumberRange(min=1.0)])
    over_under_line = FloatField('Over/Under Line', validators=[Optional()])
    over = FloatField('Over', validators=[Optional(), NumberRange(min=1.0)])
    under = FloatField('Under', validators=[Optional(), NumberRange(min=1.0)])
    btts_yes = FloatField('BTTS Yes', validators=[Optional(), NumberRange(min=1.0)])
    btts_no = FloatField('BTTS No', validators=[Optional(), NumberRange(min=1.0)])
    double_chance_1x = FloatField('1X (Home or Draw)', validators=[Optional(), NumberRange(min=1.0)])
    double_chance_12 = FloatField('12 (Home or Away)', validators=[Optional(), NumberRange(min=1.0)])
    double_chance_2x = FloatField('2X (Away or Draw)', validators=[Optional(), NumberRange(min=1.0)])
    is_betting_open = BooleanField('Betting Open')


class SportForm(FlaskForm):
    """Form for creating/editing sports."""
    name = StringField('Sport Name', validators=[DataRequired(), Length(max=80)])
    slug = StringField('Slug', validators=[DataRequired(), Length(max=80)])
    icon = StringField('Icon Class', validators=[Optional(), Length(max=50)])
    description = TextAreaField('Description', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    display_order = IntegerField('Display Order', default=0, validators=[Optional()])


class LeagueForm(FlaskForm):
    """Form for creating/editing leagues."""
    sport_id = SelectField('Sport', coerce=int, validators=[DataRequired()])
    name = StringField('League Name', validators=[DataRequired(), Length(max=120)])
    slug = StringField('Slug', validators=[Optional(), Length(max=120)])
    country = StringField('Country', validators=[Optional(), Length(max=60)])
    is_active = BooleanField('Active', default=True)


class AnnouncementForm(FlaskForm):
    """Form for creating announcements."""
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], default='normal')
    is_active = BooleanField('Active', default=True)
    
class ReviewForm(FlaskForm):
    phone_number = StringField("Phone Number", validators=[DataRequired()])

    message = TextAreaField("Review", validators=[DataRequired()])

    rating = SelectField(
        "Rating",
        choices=[
            (5, "★★★★★"),
            (4, "★★★★☆"),
            (3, "★★★☆☆"),
            (2, "★★☆☆☆"),
            (1, "★☆☆☆☆")
        ],
        coerce=int
    )

    is_visible = BooleanField("Visible", default=True)

    submit = SubmitField("Save Review")


class SystemSettingsForm(FlaskForm):
    """Form for system settings."""
    site_name = StringField('Site Name', validators=[Optional(), Length(max=100)])
    site_logo = FileField('Site Logo', validators=[Optional()])
    currency = StringField('Currency Code', default='KES', validators=[Optional(), Length(max=10)])
    currency_symbol = StringField('Currency Symbol', default='KSh', validators=[Optional(), Length(max=10)])
    minimum_deposit = FloatField('Minimum Deposit', default=50, validators=[Optional()])
    minimum_withdrawal = FloatField('Minimum Withdrawal', default=100, validators=[Optional()])
    minimum_stake = FloatField('Minimum Stake', default=10, validators=[Optional()])
    maximum_stake = FloatField('Maximum Stake', default=100000, validators=[Optional()])
    welcome_bonus_amount = FloatField('Welcome Bonus Amount', default=1000, validators=[Optional()])
    welcome_bonus_min_deposit = FloatField('Welcome Bonus Min Deposit', default=500, validators=[Optional()])
    maintenance_mode = BooleanField('Maintenance Mode')
    maintenance_message = TextAreaField('Maintenance Message', validators=[Optional()])


class AdminDepositForm(FlaskForm):
    """Form for admin to manually add funds."""
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount (KES)', validators=[DataRequired(), NumberRange(min=1)])
    description = StringField('Reason', validators=[Optional(), Length(max=200)])


class AdminWithdrawalForm(FlaskForm):
    """Form for admin to manually deduct funds."""
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount (KES)', validators=[DataRequired(), NumberRange(min=1)])
    description = StringField('Reason', validators=[Optional(), Length(max=200)])


class UserEditForm(FlaskForm):
    """Form for editing user details."""
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    full_name = StringField('Full Name', validators=[Optional(), Length(max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    country = StringField('Country', validators=[Optional(), Length(max=60)])
    is_active = BooleanField('Active')
    is_suspended = BooleanField('Suspended')
    is_admin = BooleanField('Admin')


class PromoCodeForm(FlaskForm):
    """Form for creating promo codes."""
    code = StringField('Promo Code', validators=[DataRequired(), Length(max=50)])
    description = StringField('Description', validators=[Optional(), Length(max=200)])
    discount_type = SelectField('Discount Type', choices=[
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], default='percentage')
    discount_value = FloatField('Discount Value', validators=[DataRequired(), NumberRange(min=0)])
    max_uses = IntegerField('Max Uses', default=100, validators=[Optional()])
    min_bet_amount = FloatField('Min Bet Amount', default=0, validators=[Optional()])
    expires_at = DateTimeField('Expiry Date', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    is_active = BooleanField('Active', default=True)