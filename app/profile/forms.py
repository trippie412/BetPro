"""Profile forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, PasswordField, FileField
from wtforms.validators import DataRequired, Length, Email, Optional, EqualTo, ValidationError
from flask_wtf.file import FileAllowed


class ProfileUpdateForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(2, 120)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(8, 20)])
    country = SelectField('Country', choices=[
        ('Kenya', 'Kenya'), ('Uganda', 'Uganda'), ('Tanzania', 'Tanzania'),
        ('Rwanda', 'Rwanda'), ('Burundi', 'Burundi'), ('South Sudan', 'South Sudan'),
        ('Ethiopia', 'Ethiopia'), ('Nigeria', 'Nigeria'), ('Ghana', 'Ghana'),
        ('South Africa', 'South Africa'), ('Other', 'Other')
    ], validators=[DataRequired()])
    profile_picture = FileField('Profile Picture', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Update Profile')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(), Length(8, 128),
        EqualTo('confirm_password', message='Passwords must match.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Change Password')