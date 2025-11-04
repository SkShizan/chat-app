from flask import Flask, redirect, url_for
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect  # ««« 1. IMPORT THIS
import os
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
socketio = SocketIO()
csrf = CSRFProtect()  # ««« 2. CREATE THE INSTANCE HERE
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app, async_mode='eventlet') 
    csrf.init_app(app)  # ««« 3. INITIALIZE THE APP HERE
    mail.init_app(app)

    # Ensure upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # --- Register Blueprints ---
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.chat import bp as chat_bp
    app.register_blueprint(chat_bp, url_prefix='/chat')

    @app.route('/')
    def index():
        """Main entry point, redirects to chat or login."""
        return redirect(url_for('chat.index'))

    return app