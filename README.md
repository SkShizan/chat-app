# 💬 VizzChat

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000.svg?style=for-the-badge&logo=flask&logoColor=white)
![Socket.IO](https://img.shields.io/badge/Socket.io-Realtime-black?style=for-the-badge&logo=socket.io&badgeColor=010101)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)

**VizzChat** is a sophisticated, real-time messaging platform engineered with **Flask** and **Socket.IO**. Featuring the custom "Zenith UI," it delivers a professional, full-screen chat experience with enterprise-grade security including OTP verification and disposable email blocking.

---

## ✨ Key Features

### 🔐 Security & Auth
* **Secure Identity**: Robust registration with password hashing and session management.
* **OTP Verification**: Email-based One-Time Password activation system to prevent spam accounts.
* **Disposable Email Block**: Automatically rejects registration from temporary/burner email providers.

### ⚡ Real-Time Interaction
* **Instant Messaging**: Zero-latency messaging using WebSocket technology.
* **Live Presence**: Real-time **Online/Offline** status and **Last Seen** timestamps converted to local time.
* **Typing Indicators**: Visual cues when other users are typing a message.

### 🛠️ Advanced Chat Tools
* **Group & Private Chats**: Seamlessly switch between 1-on-1 direct messages and multi-user groups.
* **Media Sharing**: Upload and view images or files directly within the chat stream.
* **Message Forwarding**: Forward messages (text or attachments) to other conversations.
* **Voice/Video Calls**: Integrated WebRTC support for peer-to-peer calling.

---

## 🎨 The "Zenith" UI
VizzChat features a bespoke interface designed for professional use:
* **Full-Screen Architecture**: 2-column layout optimized for desktop and mobile.
* **Smart Sidebar**: Dynamic search filtering for users and conversations.
* **Visual Feedback**: "Sent" vs "Received" message styling with read receipt tracking.

---

## 🏗️ Tech Stack

| Category | Technologies |
| :--- | :--- |
| **Backend** | Python, Flask, Flask-SocketIO (Eventlet) |
| **Database** | SQLite, SQLAlchemy ORM, Flask-Migrate |
| **Frontend** | HTML5, CSS3, Bootstrap 5, Custom "Zenith UI" |
| **Real-Time** | Socket.IO, WebRTC (Peer-to-Peer) |
| **Forms** | Flask-WTF, WTForms |

---

## 🚀 Quick Start

### 1. Clone & Setup
git clone [https://github.com/SkShizan/chat-app.git](https://github.com/SkShizan/chat-app.git)
cd chat-app
pip install -r requirements.txt
2. Configure Environment
Create a .env file in the root directory:

Code snippet

SECRET_KEY=your_secure_secret
UPLOAD_FOLDER=app/static/uploads
# SMTP Settings for OTP
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
3. Initialize & Run
Bash

# Initialize DB
flask db upgrade

# Start Server
python run.py
Access the app at http://localhost:5000

📂 Project Structure
Plaintext

chat-app/
├── app/
│   ├── auth/          # Authentication routes & logic
│   ├── chat/          # Chat sockets, messages, & uploads
│   ├── templates/     # Jinja2 templates (Zenith UI)
│   ├── models.py      # DB Models (User, ChatRoom, Message)
│   └── forms.py       # Login, Register, & Group forms
├── instance/          # SQLite Database
├── migrations/        # Alembic migration scripts
├── config.py          # App configuration
└── run.py             # Entry point
<p align="center"> Developed by <a href="https://www.google.com/search?q=https://github.com/SkShizan">SkShizan</a> &bull; Licensed under MIT </p>
