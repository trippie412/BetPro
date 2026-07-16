"""Admin forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, FloatField, IntegerField, DateTimeField, FileField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, ValidationError
from flask_wtf.file import FileAllowed


class UserEditForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(2, 120)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired()])
    is_active = BooleanField('Active')
    is_suspended = BooleanField('Suspended')
    submit = SubmitField('Update User')


class MatchForm(FlaskForm):
    sport_id = SelectField('Sport', coerce=int, validators=[DataRequired()])
    league_id = SelectField('League', coerce=int, validators=[DataRequired()])
    home_team = StringField('Home Team', validators=[DataRequired(), Length(2, 120)])
    away_team = StringField('Away Team', validators=[DataRequired(), Length(2, 120)])
    match_date = DateTimeField('Match Date/Time (YYYY-MM-DD HH:MM)', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('scheduled', 'Scheduled'), ('live', 'Live'),
        ('finished', 'Finished'), ('cancelled', 'Cancelled'), ('postponed', 'Postponed')
    ], default='scheduled')
    is_featured = BooleanField('Featured Match')
    is_live = BooleanField('Live Now')
    submit = SubmitField('Save Match')


class OddsForm(FlaskForm):
    home_win = FloatField('Home Win', validators=[DataRequired(), NumberRange(min=1.01)])
    draw = FloatField('Draw', validators=[Optional()])
    away_win = FloatField('Away Win', validators=[DataRequired(), NumberRange(min=1.01)])
    btts_yes = FloatField('Both Teams to Score - Yes', validators=[Optional()])
    btts_no = FloatField('Both Teams to Score - No', validators=[Optional()])
    over_under_line = FloatField('Over/Under Line', validators=[Optional()])
    over = FloatField('Over', validators=[Optional()])
    under = FloatField('Under', validators=[Optional()])
    double_chance_1x = FloatField('Double Chance 1X', validators=[Optional()])
    double_chance_12 = FloatField('Double Chance 12', validators=[Optional()])
    double_chance_2x = FloatField('Double Chance 2X', validators=[Optional()])
    submit = SubmitField('Update Odds')


class SportForm(FlaskForm):
    name = StringField('Sport Name', validators=[DataRequired(), Length(2, 80)])
    slug = StringField('URL Slug', validators=[DataRequired(), Length(2, 80)])
    icon = StringField('Icon Class (e.g., fa-futbol)', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    display_order = IntegerField('Display Order', default=0)
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Sport')


class LeagueForm(FlaskForm):
    sport_id = SelectField('Sport', coerce=int, validators=[DataRequired()])
    name = StringField('League Name', validators=[DataRequired(), Length(2, 120)])
    country = StringField('Country', validators=[Optional()])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save League')


class AnnouncementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(2, 200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')
    ], default='normal')
    submit = SubmitField('Send Announcement')


class SystemSettingsForm(FlaskForm):
    minimum_deposit = FloatField('Minimum Deposit (KES)', validators=[DataRequired()])
    minimum_withdrawal = FloatField('Minimum Withdrawal (KES)', validators=[DataRequired()])
    minimum_stake = FloatField('Minimum Stake (KES)', validators=[DataRequired()])
    maximum_stake = FloatField('Maximum Stake (KES)', validators=[DataRequired()])
    welcome_bonus_amount = FloatField('Welcome Bonus Amount (KES)', validators=[DataRequired()])
    welcome_bonus_min_deposit = FloatField('Welcome Bonus Min Deposit (KES)', validators=[DataRequired()])
    submit = SubmitField('Save Settings')


class AdminDepositForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount (KES)', validators=[DataRequired(), NumberRange(min=1)])
    description = StringField('Description', validators=[Optional(), Length(0, 200)])
    submit = SubmitField('Add Funds')


class AdminWithdrawalForm(FlaskForm):
    user_id = SelectField('User', coerce=int, validators=[DataRequired()])
    amount = FloatField('Amount (KES)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Process Withdrawal')