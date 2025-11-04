import os
from dotenv import load_dotenv

# Find the absolute path of the directory this file is in
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """
    Main application configuration class.
    It reads variables from the environment (loaded from .env).
    """

    # --- Flask Security ---
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'

    # --- Database Configuration ---
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- ★★★ THIS IS THE FINAL FIX ★★★ ---
    # We get the path from the .env file.
    upload_folder_from_env = os.environ.get('UPLOAD_FOLDER')
    
    if upload_folder_from_env and os.path.isabs(upload_folder_from_env):
        # If the user provided an absolute path, use it.
        UPLOAD_FOLDER = upload_folder_from_env
    else:
        # If it's relative (like 'app/static/uploads') or not set,
        # create the correct, absolute path.
        UPLOAD_FOLDER = os.path.join(basedir, upload_folder_from_env or 'app/static/uploads')
        
        
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    # --- ★★★ END OF FIX ★★★ ---