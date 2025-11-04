from app import create_app, db, socketio
from app.models import User, ChatRoom, ChatMessage, ChatParticipant

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'ChatRoom': ChatRoom,
        'ChatMessage': ChatMessage,
        'ChatParticipant': ChatParticipant
    }

if __name__ == '__main__':
    print("Starting Flask-SocketIO server...")
    socketio.run(app, debug=False, use_reloader=False)