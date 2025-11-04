import threading
from datetime import datetime, timedelta, timezone
from flask import render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from app import socketio, db
from flask_socketio import emit, join_room, leave_room, send
from app.chat import bp
from app.models import User, ChatRoom, ChatMessage, ChatMessageAttachment, ChatParticipant
from sqlalchemy import or_, and_
from app.forms import CreateGroupForm, MessageForm
from werkzeug.utils import secure_filename
import os
import shutil
from zoneinfo import ZoneInfo


def to_ist_str(dt):
    """
    Converts a naive UTC datetime from the DB to an IST string for display.
    """
    if dt is None:
        return None
    # Tell the naive datetime it is in UTC
    dt_aware = dt.replace(tzinfo=timezone.utc)
    # Convert to Asia/Kolkata and format
    return dt_aware.astimezone(ZoneInfo("Asia/Kolkata")).strftime('%I:%M %p')

@bp.route('/')
@login_required
def index():
    """Main chat interface page with user search and recent chats."""
    search_query = request.args.get('q', '')
    search_term = f"%{search_query}%"

    # 1. Fetching USERS (User Directory)
    users_query = User.query.filter(
        User.id != current_user.id,
        User.is_active == True
    )
    if search_query:
        users_query = users_query.filter(
            or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
                User.username.ilike(search_term),
                User.public_id.ilike(search_term)
            )
        )
    else:
        # Don't list all users in a public system by default
        users_query = users_query.filter(db.false())
        
    users = users_query.order_by(User.name).all()

    # 2. Fetching PARTICIPATIONS (Recent Chats)
    participations_query = ChatParticipant.query.filter_by(user_id=current_user.id)

    if search_query:
        all_participations = participations_query.all()
        filtered_participations = []

        for p in all_participations:
            room = p.room
            is_match = False

            if room.room_type == 'group' and search_query.lower() in (room.name or '').lower():
                is_match = True

            if room.room_type == 'one_to_one':
                other_user = next((part.user for part in room.participants if part.user_id != current_user.id), None)
                if other_user and (search_query.lower() in other_user.name.lower() or search_query.lower() in other_user.email.lower()):
                    is_match = True

            if is_match:
                filtered_participations.append(p)

        participations = filtered_participations
    else:
        participations = participations_query.order_by(ChatParticipant.unread_count.desc()).all()


    return render_template('chat/index.html', 
                           title='Chat', 
                           users=users,
                           participations=participations,
                           search_query=search_query)

@bp.route('/start/<int:recipient_id>')
@login_required
def start_chat(recipient_id):
    """Finds or creates a 1-on-1 chat and redirects to it."""
    recipient = User.query.get_or_404(recipient_id)
    
    if recipient.id == current_user.id:
        flash("You cannot start a chat with yourself.", "warning")
        return redirect(url_for('chat.index'))

    room = ChatRoom.query.join(ChatParticipant, ChatRoom.id == ChatParticipant.room_id)\
        .filter(ChatRoom.room_type == 'one_to_one')\
        .group_by(ChatRoom.id).having(db.func.count(ChatParticipant.user_id) == 2)\
        .filter(ChatRoom.participants.any(user_id=current_user.id))\
        .filter(ChatRoom.participants.any(user_id=recipient.id)).first()

    if not room:
        room = ChatRoom(room_type='one_to_one')
        db.session.add(room)
        p1 = ChatParticipant(user_id=current_user.id, room=room)
        p2 = ChatParticipant(user_id=recipient.id, room=room)
        db.session.add_all([p1, p2])
        db.session.commit()

    return redirect(url_for('chat.view_room', room_id=room.id))

@bp.route('/room/<int:room_id>', methods=['GET', 'POST'])
@login_required
def view_room(room_id):
    """Displays the full chat interface with a specific room selected."""
    active_room = ChatRoom.query.get_or_404(room_id)

    participation = active_room.participants.filter_by(user_id=current_user.id).first()
    if not participation:
        flash("You are not a member of this chat room.", "danger")
        return redirect(url_for('chat.index'))

    if participation.unread_count > 0:
        participation.unread_count = 0
        db.session.commit()

    messages = active_room.messages.order_by(ChatMessage.timestamp.asc()).all()
    participations = current_user.chat_participations.order_by(ChatParticipant.unread_count.desc()).all()

    chat_partner = None
    last_seen_ist = None
    is_online = False

    if active_room.room_type == 'one_to_one':
        chat_partner = next((part.user for part in active_room.participants if part.user_id != current_user.id), None)
        if chat_partner and chat_partner.last_seen:
            last_seen_ist = to_ist_str(chat_partner.last_seen)
            
            # --- ★★★ FIX for Naive vs. Aware Datetime ★★★ ---
            # Use utcnow() to get a naive datetime in UTC
            five_min_ago = datetime.utcnow() - timedelta(minutes=5)
            # Both datetimes are now naive and can be compared
            if chat_partner.last_seen > five_min_ago:
                is_online = True

    form = MessageForm() 

    return render_template('chat/room.html', 
                           title="Chat", 
                           participations=participations, 
                           active_room=active_room,
                           messages=messages, 
                           chat_partner=chat_partner,
                           form=form,
                           last_seen_ist=last_seen_ist,
                           is_online=is_online)

@bp.route('/create-group', methods=['GET', 'POST'])
@login_required
def create_group():
    form = CreateGroupForm()
    search_query = request.args.get('search_q', '')
    pre_selected_ids = request.args.getlist('members', type=int)

    employees_query = User.query.filter(
        User.is_active == True,
        User.id != current_user.id
    )

    if search_query:
        search_term = f"%{search_query}%"
        employees_query = employees_query.filter(
            or_(
                User.name.ilike(search_term),
                User.email.ilike(search_term),
                User.username.ilike(search_term),
                User.public_id.ilike(search_term)
            )
        )

    employees_to_display = employees_query.order_by(User.name).all()

    all_company_employees = User.query.filter(
        User.is_active == True, 
        User.id != current_user.id
    ).all()
    form.members.choices = [(u.id, u.name) for u in all_company_employees]

    if form.validate_on_submit():
        new_group_room = ChatRoom(
            name=form.name.data, 
            room_type='group'
        )
        db.session.add(new_group_room)

        if form.include_creator.data:
            creator_part = ChatParticipant(user=current_user, room=new_group_room)
            db.session.add(creator_part)

        selected_members = User.query.filter(User.id.in_(form.members.data)).all()
        for member in selected_members:
            part = ChatParticipant(user=member, room=new_group_room)
            db.session.add(part)

        db.session.commit()
        flash(f"Group '{new_group_room.name}' created successfully!", "success")

        if form.include_creator.data:
            return redirect(url_for('chat.view_room', room_id=new_group_room.id))
        else:
            return redirect(url_for('chat.index'))

    if request.method == 'GET' and pre_selected_ids:
        form.members.data = pre_selected_ids

    return render_template('chat/create_group.html', 
                           title="Create New Group", 
                           form=form, 
                           employees=employees_to_display,
                           search_query=search_query)

@bp.route('/upload-attachment/<int:room_id>', methods=['POST'])
@login_required
def upload_attachment(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    if not room.participants.filter_by(user_id=current_user.id).first(): return {'error': 'Unauthorized'}, 403
    file = request.files.get('file');
    if not file or file.filename == '': return {'error': 'No file selected'}, 400

    filename = secure_filename(file.filename)
    
    # 1. Create a WEB-FRIENDLY path with forward slashes
    file_path_relative_web = f"{room.id}/{filename}"
    
    # 2. Create an OS-FRIENDLY path for saving to disk
    full_path_on_disk = os.path.join(current_app.config['UPLOAD_FOLDER'], file_path_relative_web.replace('/', os.path.sep))

    os.makedirs(os.path.dirname(full_path_on_disk), exist_ok=True)
    file.save(full_path_on_disk)
    file_size = os.path.getsize(full_path_on_disk)

    new_message = ChatMessage(sender_id=current_user.id, room_id=room_id, content=f"File: {filename}"); db.session.add(new_message); db.session.flush()

    # 3. Save the WEB-FRIENDLY path to the database
    attachment = ChatMessageAttachment(message_id=new_message.id, filename=filename, file_path=file_path_relative_web, file_size_bytes=file_size); db.session.add(attachment)

    db.session.flush() # Ensure attachment has an ID

    # 1. Update unread counts BEFORE committing
    for p in room.participants:
        if p.user_id != current_user.id:
            p.unread_count = (p.unread_count or 0) + 1
            # We will send the socket emit AFTER committing

    # 2. COMMIT all changes to the database
    db.session.commit()

    is_image = any(filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])

    msg_data = {
        'id': new_message.id, 
        'content': new_message.content, 
        'sender_name': current_user.name, 
        'sender_id': current_user.id,
        'timestamp': new_message.timestamp.isoformat() + 'Z',
        'attachment': {'id': attachment.id, 'filename': attachment.filename, 'is_image': is_image, 'viewed': attachment.viewed},
        'is_forward': False 
    }
    
    # 3. NOW broadcast the message. The attachment is safely in the DB.
    socketio.send(msg_data, to=str(room_id))

    # 4. NOW broadcast the unread updates.
    for p in room.participants:
        if p.user_id != current_user.id:
            socketio.emit('unread_update', {'room_id': room_id, 'count': p.unread_count}, to=f"user_{p.user_id}")

    return {'success': 'File uploaded', 'message_data': msg_data}, 200


@bp.route('/attachment/<int:attachment_id>')
@login_required
def get_attachment(attachment_id):
    attachment = ChatMessageAttachment.query.get(attachment_id)
    if not attachment:
        flash("Attachment not found in database.", "danger")
        return redirect(request.referrer or url_for('chat.index'))

    room_id_for_redirect = attachment.message.room_id 

    if not attachment.message.room.participants.filter_by(user_id=current_user.id).first():
        flash("Unauthorized", "danger")
        return redirect(url_for('chat.index'))

    directory = current_app.config['UPLOAD_FOLDER']
    
    # 1. Get the WEB-FRIENDLY path from the DB (e.g., "1/file.jpg")
    path_relative_web = attachment.file_path
    
    # 2. Create the OS-FRIENDLY path for all disk operations
    path_relative_os = path_relative_web.replace('/', os.path.sep)
    full_file_path_on_disk = os.path.join(directory, path_relative_os)

    if not os.path.exists(full_file_path_on_disk):
        flash("This attachment is no longer available on disk.", "warning")
        try:
            msg_to_update = attachment.message
            msg_to_update.content = "[Attachment expired or missing]"
            db.session.add(msg_to_update)
            db.session.delete(attachment)
            db.session.commit()
            socketio.emit('attachment_deleted', {
                'attachment_id': attachment_id, 
                'message_id': msg_to_update.id
            }, to=str(room_id_for_redirect))
        except Exception as e:
            current_app.logger.error(f"Error cleaning orphaned attachment {attachment_id}: {e}")
            db.session.rollback()
        return redirect(url_for('chat.view_room', room_id=room_id_for_redirect))

    is_recipient = attachment.message.sender_id != current_user.id

    if attachment.viewed and is_recipient:
        flash("This attachment has already been viewed and is no longer available.", "warning")
        return redirect(url_for('chat.view_room', room_id=room_id_for_redirect))

    # --- ★★★ THIS IS THE FINAL 404 FIX ★★★ ---
    # We pass the directory and the WEB-FRIENDLY path.
    # `send_from_directory` is smart enough to handle this conversion.
    # My previous fix (path_relative_os) was wrong. This is the correct way.
    response = send_from_directory(directory, path_relative_web, as_attachment=True)
    # --- ★★★ END OF FIX ★★★ ---

    if is_recipient:
        attachment.viewed = True
        db.session.commit()
        socketio.emit('attachment_viewed', {'attachment_id': attachment.id}, to=str(room_id_for_redirect))

        def delete_file_and_record(app_instance):
            with app_instance.app_context():
                try:
                    att_to_delete = ChatMessageAttachment.query.get(attachment_id)
                    if att_to_delete:
                        msg_to_update = att_to_delete.message
                        room_id = msg_to_update.room_id
                        msg_id = msg_to_update.id
                        
                        # Use the OS-FRIENDLY path for deletion
                        file_path_to_delete = os.path.join(app_instance.config['UPLOAD_FOLDER'], att_to_delete.file_path.replace('/', os.path.sep))
                        
                        if os.path.exists(file_path_to_delete):
                            os.remove(file_path_to_delete)
                        
                        msg_to_update.content = "[Attachment downloaded and removed]"
                        db.session.add(msg_to_update)
                        db.session.delete(att_to_delete)
                        db.session.commit()
                        
                        socketio.emit('attachment_deleted', {
                            'attachment_id': attachment_id, 
                            'message_id': msg_id
                        }, to=str(room_id))
                except Exception as e:
                    app_instance.logger.error(f"Error in post-request deletion for {attachment_id}: {e}")
                    db.session.rollback()

        real_app = current_app._get_current_object()
        deleter_thread = threading.Thread(
            target=delete_file_and_record, 
            args=(real_app,)
        )
        deleter_thread.start()

    return response

@bp.route('/cleanup-attachments')
def cleanup_attachments_route():
    cleanup_viewed_attachments()
    return "Cleanup finished."

def cleanup_viewed_attachments():
    """Finds viewed attachments older than 5 minutes and deletes them."""
    # Use utcnow() for naive datetime comparison
    five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)

    attachments_to_delete = ChatMessageAttachment.query.filter(
        ChatMessageAttachment.viewed == True,
        ChatMessageAttachment.message.has(ChatMessage.timestamp < five_minutes_ago)
    ).all()

    for attachment in attachments_to_delete:
        try:
            # FIX: Use OS-friendly path for deletion
            full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], attachment.file_path.replace('/', os.path.sep))
            if os.path.exists(full_path):
                os.remove(full_path)
            db.session.delete(attachment)
        except Exception as e:
            current_app.logger.error(f"Error deleting file {attachment.file_path}: {e}")
            db.session.rollback()

    db.session.commit()


# --- START: SOCKET.IO HANDLERS ---

@socketio.on('connect')
def on_connect():
    if current_user.is_authenticated:
        join_room(f"user_{current_user.id}")
        
        # FIX for Naive vs. Aware: Use utcnow()
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        for p in current_user.chat_participations:
            emit('user_status_update', 
                 {'user_id': current_user.id, 'status': 'Online'}, 
                 to=str(p.room_id), 
                 include_self=False)

@socketio.on('disconnect')
def on_disconnect():
    if current_user.is_authenticated:
        # FIX for Naive vs. Aware: Use utcnow()
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        
        # This logic is now correct, as last_seen is naive UTC
        last_seen_utc = current_user.last_seen.replace(tzinfo=timezone.utc) 
        last_seen_ist = last_seen_utc.astimezone(ZoneInfo("Asia/Kolkata"))
        last_seen_str = f"Last seen at {last_seen_ist.strftime('%I:%M %p')}"
        
        for p in current_user.chat_participations:
            emit('user_status_update', 
                 {'user_id': current_user.id, 'status': last_seen_str}, 
                 to=str(p.room_id), 
                 include_self=False)

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)

@socketio.on('send_message')
def on_send_message(data):
    """This function is the correct pattern. Commit before send."""
    room_id = data['room']; content = data['message']
    room = ChatRoom.query.get(room_id)
    if not room or not room.participants.filter_by(user_id=current_user.id).first(): return

    new_message = ChatMessage(sender_id=current_user.id, room_id=room_id, content=content)
    db.session.add(new_message)

    for p in room.participants:
        if p.user_id != current_user.id:
            p.unread_count = (p.unread_count or 0) + 1
            # We will emit the update *after* the commit

    # 1. COMMIT FIRST
    db.session.commit() 

    msg_data = {
        'id': new_message.id, 
        'content': content, 
        'sender_name': current_user.name, 
        'sender_id': current_user.id, 
        'timestamp': new_message.timestamp.isoformat() + 'Z', 
        'attachment': None, 
        'is_forward': False
    }
    
    # 2. SEND LATER
    send(msg_data, to=str(room_id))
    
    # 3. SEND UNREAD UPDATES LATER
    for p in room.participants:
        if p.user_id != current_user.id:
            socketio.emit('unread_update', {'room_id': room_id, 'count': p.unread_count}, to=f"user_{p.user_id}")


@socketio.on('start_typing')
def on_start_typing(data):
    emit('typing_started', {'user_name': current_user.name, 'user_id': current_user.id}, to=data['room'], include_self=False)

@socketio.on('stop_typing')
def on_stop_typing(data):
    emit('typing_stopped', {'user_id': current_user.id}, to=data['room'], include_self=False)


@bp.route('/delete-room/<int:room_id>', methods=['POST'])
@login_required
def delete_conversation(room_id):
    room_to_delete = ChatRoom.query.get_or_404(room_id)
    if not room_to_delete.participants.filter_by(user_id=current_user.id).first():
        flash("Unauthorized to delete this conversation.", "danger")
        return redirect(url_for('chat.index'))
    try:
        attachments = ChatMessageAttachment.query.join(ChatMessage).filter(ChatMessage.room_id == room_id).all()
        for attachment in attachments:
            # FIX: Use OS-friendly path for deletion
            full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], attachment.file_path.replace('/', os.path.sep))
            if os.path.exists(full_path):
                os.remove(full_path)
        
        # Deleting the room will cascade and delete all participants, messages, and attachments
        db.session.delete(room_to_delete) 
        db.session.commit()
        flash('Conversation has been successfully deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting conversation {room_id}: {e}")
        flash(f'Error deleting conversation: {str(e)}', 'danger')
    return redirect(url_for('chat.index'))


# --- START: ADDED FORWARD HANDLERS ---
@socketio.on('forward_multiple_messages')
@login_required
def on_forward_multiple_messages(data):
    original_message_ids = data.get('original_message_ids', [])
    destination_room_id = data.get('destination_room_id')

    if not original_message_ids or not destination_room_id:
        return emit('error', {'message': 'Missing message IDs or room ID.'})

    destination_room = ChatRoom.query.get(destination_room_id)

    if not destination_room.participants.filter_by(user_id=current_user.id).first():
        return emit('error', {'message': 'Unauthorized to send to this room.'})

    messages_to_forward = ChatMessage.query.filter(
        ChatMessage.id.in_(original_message_ids)
    ).order_by(ChatMessage.timestamp.asc()).all()

    message_count = 0
    all_new_msg_data = [] # FIX: Create a list to hold messages
    try:
        for msg in messages_to_forward:
            if not msg.room.participants.filter_by(user_id=current_user.id).first():
                continue 

            message_count += 1
            new_content = f"[Forwarded]: {msg.content}"
            new_message = ChatMessage(
                sender_id=current_user.id,
                room_id=destination_room.id,
                content=new_content
            )
            db.session.add(new_message)
            db.session.flush() 

            original_attachment = msg.attachment
            new_attachment_data = None

            if original_attachment:
                # FIX: Use OS-friendly path for source
                original_full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], original_attachment.file_path.replace('/', os.path.sep))
                
                new_filename = f"{new_message.id}_{original_attachment.filename}" # Make unique
                
                # FIX: Use WEB-FRIENDLY path for new DB entry
                new_relative_path_web = f"{destination_room.id}/{new_filename}"
                # FIX: Use OS-FRIENDLY path for new disk location
                new_full_path_on_disk = os.path.join(current_app.config['UPLOAD_FOLDER'], new_relative_path_web.replace('/', os.path.sep))

                if os.path.exists(original_full_path):
                    os.makedirs(os.path.dirname(new_full_path_on_disk), exist_ok=True)
                    shutil.copy(original_full_path, new_full_path_on_disk)

                    new_attachment = ChatMessageAttachment(
                        message_id=new_message.id,
                        filename=new_filename,
                        file_path=new_relative_path_web, # Save web-friendly path
                        file_size_bytes=original_attachment.file_size_bytes
                    )
                    db.session.add(new_attachment)
                    db.session.flush()

                    is_image = any(new_filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'])
                    new_attachment_data = {
                        'id': new_attachment.id, 
                        'filename': new_attachment.filename, 
                        'is_image': is_image, 
                        'viewed': False
                    }
                else:
                    new_message.content += " (Original attachment was missing)"

            msg_data = {
                'id': new_message.id, 
                'content': new_message.content, 
                'sender_name': current_user.name, 
                'sender_id': current_user.id, 
                'timestamp': new_message.timestamp.isoformat() + 'Z', 
                'attachment': new_attachment_data,
                'room_type': destination_room.room_type,
                'is_forward': True
            }
            all_new_msg_data.append(msg_data) # FIX: Add to list, don't send
            
        if message_count > 0:
            for p in destination_room.participants:
                if p.user_id != current_user.id:
                    p.unread_count = (p.unread_count or 0) + message_count
                    # We will emit this update *after* the commit

        # --- FIX FOR RACE CONDITION ---
        # 1. COMMIT FIRST
        db.session.commit()

        # 2. SEND MESSAGES LATER
        for msg_data in all_new_msg_data:
            send(msg_data, to=str(destination_room.id))

        # 3. SEND UNREAD UPDATES LATER
        if message_count > 0:
            for p in destination_room.participants:
                if p.user_id != current_user.id:
                    socketio.emit('unread_update', 
                                  {'room_id': destination_room.id, 'count': p.unread_count}, 
                                  to=f"user_{p.user_id}")
        # --- END OF FIX ---

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error forwarding multiple messages: {e}")
        emit('error', {'message': f'An internal error occurred: {str(e)}'})

# --- END: ADDED FORWARD HANDLERS ---