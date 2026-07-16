"""Global form definitions."""
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, FloatField, IntegerField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, NumberRange, Optional
from flask_wtf.file import FileAllowed
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 80)])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(2, 120)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(5, 120)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(8, 20)])
    country = SelectField('Country', choices=[
        ('Kenya', 'Kenya'), ('Uganda', 'Uganda'), ('Tanzania', 'Tanzania'),
        ('Rwanda', 'Rwanda'), ('Burundi', 'Burundi'), ('South Sudan', 'South Sudan'),
        ('Ethiopia', 'Ethiopia'), ('Nigeria', 'Nigeria'), ('Ghana', 'Ghana'),
        ('South Africa', 'South Africa'), ('Other', 'Other')
    ], validators=[DataRequired()])
    password = PasswordField('Password', validators=[
        DataRequired(), Length(8, 128),
        EqualTo('confirm_password', message='Passwords must match.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    agree_terms = BooleanField('I agree to the Terms of Service', validators=[DataRequired()])
    submit = SubmitField('Create Account')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), Length(8, 128),
        EqualTo('confirm_password', message='Passwords must match.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired()])
    submit = SubmitField('Reset Password')


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