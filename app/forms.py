from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length, Regexp
from app.models import User
# We no longer need the blocklist import here, it's moved to routes.py

# --- ★★★ NEW OTP Form ★★★ ---
class VerifyOTPForm(FlaskForm):
    otp = StringField('OTP', validators=[
        DataRequired(),
        Length(min=6, max=6, message="OTP must be 6 digits."),
        Regexp(r'^\d{6}$', message="OTP must be numeric.")
    ])
    submit = SubmitField('Verify Account')

# --- ▼▼▼ DELETED ResendVerificationForm ▼▼▼ ---

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username (public, for search)', validators=[DataRequired(), Length(min=3, max=64)])
    name = StringField('Full Name (for display)', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    password2 = PasswordField(
        'Confirm Password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    submit = SubmitField('Register')

    # --- ★★★ KEY CHANGE: VALIDATION REMOVED ★★★ ---
    # We removed validate_username and validate_email.
    # Your routes.py file will now handle this logic,
    # which allows for the "unverified user" flow you want.
    # --- ★★★ END OF CHANGE ★★★ ---


# --- Chat Forms (Unchanged) ---
class CreateGroupForm(FlaskForm):
    name = StringField('Group Name', validators=[DataRequired(), Length(min=3, max=100)])
    members = SelectMultipleField('Select Members', coerce=int, validators=[DataRequired()])
    include_creator = BooleanField('Include myself in this group', default='checked')
    submit = SubmitField('Create Group')

class MessageForm(FlaskForm):
    content = StringField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')

