# Chat Application

## Overview
This is a Flask-based real-time chat application with user authentication, email verification, and WebSocket support for live messaging. The application features user registration, login, chat rooms, and real-time messaging using Flask-SocketIO.

## Current State
- **Status**: Fully configured and running on Replit
- **Port**: 5000
- **Database**: SQLite (instance/app.db)
- **Framework**: Flask with SocketIO for real-time features

## Recent Changes (November 4, 2025)
- Configured project for Replit environment
- Updated run.py to bind to 0.0.0.0:5000 for proper hosting
- Fixed database configuration to use SQLite instead of PostgreSQL
- Created .gitignore for Python project
- Configured workflow to run Flask-SocketIO server
- Set up deployment configuration for autoscale

## Project Structure
```
.
├── app/
│   ├── auth/              # Authentication routes and logic
│   ├── chat/              # Chat functionality
│   ├── templates/         # HTML templates
│   │   ├── auth/         # Login, register, verification pages
│   │   └── chat/         # Chat interface templates
│   ├── __init__.py       # App factory and initialization
│   ├── forms.py          # WTForms definitions
│   └── models.py         # Database models
├── migrations/           # Database migrations
├── instance/            # Instance-specific files (database)
├── config.py            # Application configuration
├── run.py              # Application entry point
└── requirements.txt    # Python dependencies
```

## Features
- User authentication (registration, login, logout)
- Email verification with OTP
- Real-time chat using WebSocket
- Chat rooms (private and group chats)
- File uploads for chat messages
- Session management
- CSRF protection

## Technology Stack
- **Backend**: Flask 3.1.2
- **Real-time**: Flask-SocketIO with eventlet
- **Database**: SQLAlchemy with SQLite
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF with WTForms
- **Email**: Flask-Mail
- **Migrations**: Flask-Migrate (Alembic)

## Environment Variables
The application uses the following environment variables (stored in .env):
- `SECRET_KEY`: Flask secret key for sessions
- `FLASK_APP`: Application entry point (run.py)
- `UPLOAD_FOLDER`: Directory for file uploads
- `MAIL_SERVER`: SMTP server for email
- `MAIL_PORT`: SMTP port
- `MAIL_USE_TLS`: Enable TLS for email
- `MAIL_USERNAME`: Email username
- `MAIL_PASSWORD`: Email password
- `MAIL_DEFAULT_SENDER`: Default sender email

## Running the Application
The application runs automatically via the configured workflow. It binds to 0.0.0.0:5000 and uses Flask-SocketIO with eventlet for WebSocket support.

## Database
- **Type**: SQLite
- **Location**: instance/app.db
- **Models**: User, ChatRoom, ChatMessage, ChatParticipant
- The database is already initialized with existing data

## Deployment
Configured for Replit autoscale deployment:
- Deployment target: autoscale (stateless web application)
- Run command: python run.py
- Port: 5000

## User Preferences
None specified yet.

## Notes
- The application uses SQLite for simplicity and portability
- Email functionality requires valid SMTP credentials in .env
- Real-time features require WebSocket support (provided by Flask-SocketIO)
- The app.db file contains existing user and chat data
