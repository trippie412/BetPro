"""Matches forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import Optional


class MatchSearchForm(FlaskForm):
    search = StringField('Search Teams', validators=[Optional()])
    sport = SelectField('Sport', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('upcoming', 'Upcoming'), ('live', 'Live'), ('finished', 'Finished')
    ], default='upcoming')
    submit = SubmitField('Search')