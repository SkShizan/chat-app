from flask import render_template, redirect, url_for, flash, request, current_app, session
from markupsafe import Markup
from flask_login import login_user, logout_user, current_user
from app import db, mail
from app.auth import bp
from app.forms import LoginForm, RegistrationForm, VerifyOTPForm # <-- Import new VerifyOTPForm
from app.models import User
from datetime import datetime
from flask_mail import Message
from threading import Thread
import random # <-- Import random for OTP
from disposable_email_domains import blocklist # <-- Import blocklist for checking

# --- Helper: check disposable email ---
def is_disposable(email):
    domain = email.split('@')[-1].lower()
    return domain in blocklist

# --- Helper: send email asynchronously ---
def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            # Log the error in a real app
            current_app.logger.error(f"Email sending failed: {e}")

def send_verification_email(user, otp):
    msg = Message(
        'Your Verification Code',
        sender=current_app.config['MAIL_DEFAULT_SENDER'],
        recipients=[user.email],
    )
    # Use the new OTP email template
    msg.html = render_template('auth/email/verify.html', user=user, otp=otp)

    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg),
    ).start()


# --- Register route ---
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('chat.index'))

    form = RegistrationForm()

    if form.validate_on_submit():
        # --- ★★★ LOGIC MOVED FROM FORMS.PY TO HERE ★★★ ---

        # 1. Check for disposable email
        if is_disposable(form.email.data):
            flash('Disposable email addresses are not allowed.', 'danger')
            return render_template('auth/register.html', title='Register', form=form)

        # 2. Check if email exists
        user_by_email = User.query.filter_by(email=form.email.data).first()

        # 3. Check if username exists
        user_by_username = User.query.filter_by(username=form.username.data).first()

        if user_by_email:
            if user_by_email.is_verified:
                # Case 1: User exists and is verified.
                flash('This email is already registered. Please log in.', 'warning')
                return redirect(url_for('auth.login'))
            else:
                # Case 2: User exists but is NOT verified (the case you described!)
                # Update their info, generate a new OTP, and resend.
                try:
                    # Check if the username is being taken by *someone else*
                    if user_by_username and user_by_username.email != user_by_email.email:
                        flash('That username is already taken by another account. Please choose a different one.', 'danger')
                        return render_template('auth/register.html', title='Register', form=form)

                    user = user_by_email # Use the existing unverified user
                    user.username = form.username.data
                    user.name = form.name.data
                    user.set_password(form.password.data) # Update their password

                    otp = user.generate_otp() # Generate a new OTP
                    db.session.commit() # Save the new password and OTP

                    send_verification_email(user, otp)
                    flash('This email is already registered. A new verification code has been sent.', 'info')

                    # Redirect to the OTP page
                    return redirect(url_for('auth.verify_otp', email=user.email))

                except Exception as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error re-registering unverified user: {e}")
                    flash('An error occurred. Please try again.', 'danger')
                    return render_template('auth/register.html', title='Register', form=form)

        if user_by_username:
            # Case 3: Email is new, but username is taken by a verified user.
            flash('That username is already taken. Please choose a different one.', 'danger')
            return render_template('auth/register.html', title='Register', form=form)

        # --- ★★★ END OF NEW LOGIC ★★★ ---

        # If we are here, it's a completely new user
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
                name=form.name.data,
                is_verified=False,
                is_active=False # User is inactive until OTP is verified
            )
            user.set_password(form.password.data)

            otp = user.generate_otp()
            db.session.add(user)
            db.session.commit()

            send_verification_email(user, otp)
            flash('Registration successful! A 6-digit OTP has been sent to your email.', 'success')

            # Redirect to the OTP verification page
            return redirect(url_for('auth.verify_otp', email=user.email))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration or email sending failed: {e}")
            flash('An error occurred during registration. Please try again.', 'danger')

    return render_template('auth/register.html', title='Register', form=form)


# --- ★★★ NEW: Verify OTP route ★★★ ---
@bp.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if current_user.is_authenticated:
        return redirect(url_for('chat.index'))

    # Get email from the query string (e.g., /verify_otp?email=...)
    email = request.args.get('email')
    if not email:
        flash('No email specified. Please register again.', 'danger')
        return redirect(url_for('auth.register'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found. Please register.', 'danger')
        return redirect(url_for('auth.register'))

    if user.is_verified:
        flash('Your account is already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))

    form = VerifyOTPForm()
    if form.validate_on_submit():
        otp = form.otp.data
        if user.verify_otp(otp):
            # verify_otp method in User model already handles setting is_verified=True and is_active=True
            db.session.commit()
            flash('Your account has been verified! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')

    return render_template('auth/verify_otp.html', title='Verify Account', form=form, email=email)


# --- ★★★ NEW: Resend OTP route ★★★ ---
@bp.route('/resend_otp/<email>')
def resend_otp(email):
    if current_user.is_authenticated:
        return redirect(url_for('chat.index'))

    user = User.query.filter_by(email=email).first_or_404()

    if user.is_verified:
        flash('This account is already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))

    try:
        otp = user.generate_otp()
        db.session.commit()
        send_verification_email(user, otp)
        flash('A new verification code has been sent.', 'success')
    except Exception as e:
        current_app.logger.error(f"Resend OTP failed: {e}")
        flash('Failed to send verification email. Try again later.', 'warning')

    return redirect(url_for('auth.verify_otp', email=user.email))


# --- Login route (Updated) ---
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat.index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('auth.login'))

        # --- ★★★ NEW: Check if verified ★★★ ---
        if not user.is_verified:
            resend_url = url_for('auth.resend_otp', email=user.email)
            flash(Markup(
                f'Your account is not verified. '
                f'<a href="{resend_url}" class="alert-link">Resend verification code</a>.'
            ), 'warning')
            return redirect(url_for('auth.verify_otp', email=user.email)) # Redirect to OTP page, not login

        if not user.is_active:
            flash('This account has been deactivated.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.remember_me.data)
        user.last_seen = datetime.utcnow()
        db.session.commit()

        next_page = request.args.get('next')
        if not next_page or url_for('chat.index') not in next_page:
            next_page = url_for('chat.index')
        return redirect(next_page)

    return render_template('auth/login.html', title='Login', form=form)


# --- Logout route (Unchanged) ---
@bp.route('/logout')# <-- Good practice to add this
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
