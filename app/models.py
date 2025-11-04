import random
from datetime import datetime, timezone, timedelta # <-- Make sure timedelta is imported
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# (Keep your generate_public_id function as-is)
def generate_public_id():
    """Generates a unique 11-digit numeric public ID."""
    while True:
        new_id = str(random.randint(10000000000, 99999999999))
        if not User.query.filter_by(public_id=new_id).first():
            return new_id

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    
    public_id = db.Column(db.String(11), unique=True, nullable=False, default=generate_public_id, index=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False) # User's full name
    password_hash = db.Column(db.String(256))
    
    is_active = db.Column(db.Boolean, default=True) 
    is_verified = db.Column(db.Boolean, default=False, nullable=False) 

    # --- ★★★ NEW OTP FIELDS ★★★ ---
    verification_otp = db.Column(db.String(6), nullable=True)
    otp_expiration = db.Column(db.DateTime, nullable=True)
    # --- ★★★ END OF NEW FIELDS ★★★ ---

    last_seen = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    
    chat_participations = db.relationship('ChatParticipant', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    messages_sent = db.relationship('ChatMessage', foreign_keys='ChatMessage.sender_id', back_populates='sender', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- ★★★ NEW OTP METHODS ★★★ ---
    def generate_otp(self):
        """Generates a 6-digit OTP and sets its expiration."""
        self.verification_otp = str(random.randint(100000, 999999))
        self.otp_expiration = datetime.utcnow() + timedelta(minutes=10) # OTP is valid for 10 minutes
        return self.verification_otp

    def verify_otp(self, otp):
        """Checks if the provided OTP is valid and not expired."""
        if self.otp_expiration and datetime.utcnow() > self.otp_expiration:
            # OTP has expired
            self.verification_otp = None
            self.otp_expiration = None
            db.session.commit() # Clear the expired OTP
            return False
        
        if otp == self.verification_otp:
            # Success
            self.verification_otp = None
            self.otp_expiration = None
            self.is_verified = True
            self.is_active = True
            return True
        
        # Invalid OTP
        return False
    # --- ★★★ END OF NEW METHODS ★★★ ---

    def __repr__(self):
        return f'<User {self.username} ({self.public_id})>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class ChatRoom(db.Model):
    __tablename__ = 'chat_room'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True) 
    room_type = db.Column(db.String(20), nullable=False, default='one_to_one')
    
    participants = db.relationship('ChatParticipant', back_populates='room', lazy='dynamic', cascade="all, delete-orphan")
    messages = db.relationship('ChatMessage', back_populates='room', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ChatRoom {self.name or self.id}>'

class ChatParticipant(db.Model):
    __tablename__ = 'chat_participant'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    unread_count = db.Column(db.Integer, default=0)
    
    user = db.relationship('User', back_populates='chat_participations')
    room = db.relationship('ChatRoom', back_populates='participants')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'room_id', name='_user_room_uc'),)

class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.utcnow())
    
    sender = db.relationship('User', foreign_keys=[sender_id], back_populates='messages_sent')
    room = db.relationship('ChatRoom', back_populates='messages')
    attachment = db.relationship('ChatMessageAttachment', back_populates='message', uselist=False, cascade="all, delete-orphan")

class ChatMessageAttachment(db.Model):
    __tablename__ = 'chat_message_attachment'
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_message.id'), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False) # Relative path
    file_size_bytes = db.Column(db.Integer)
    viewed = db.Column(db.Boolean, default=False)
    
    message = db.relationship('ChatMessage', back_populates='attachment')

