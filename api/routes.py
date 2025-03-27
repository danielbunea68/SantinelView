from flask import Blueprint, jsonify, request
from email_helper import send_notifications
from models import User, Camera, Event, Footage, Notification, db
from auth import generate_token, decode_token
from datetime import datetime
from werkzeug.utils import secure_filename
import os

# Create a Blueprint named 'api' to handle routes
api_bp = Blueprint('api', __name__)

# Define the folder where profile pictures will be uploaded
UPLOAD_FOLDER = 'uploads/profile_pictures'
# Set allowed file extensions for profile pictures
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


# Route to greet users
@api_bp.route('/', methods=['GET'])
def greet_user():
    return jsonify({'message': 'Welcome to the API!'})


# Route to register a new user
@api_bp.route('/register', methods=['POST'])
def register_user():
    # Extract user data from the request
    data = request.get_json()
    # Create a new User instance
    new_user = User(username=data['username'], email=data['email'], password=data['password'])
    # Add the new user to the database
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully', 'id': new_user.id}), 201


# Route to login a user
@api_bp.route('/login', methods=['POST'])
def login_user():
    # Extract login credentials from the request
    data = request.get_json()
    # Query the database for a user with the provided credentials
    user = User.query.filter_by(username=data['username'], password=data['password']).first()
    if user:
        # Generate a token for the authenticated user
        token = generate_token(user.id)
        return jsonify({'token': token, 'profile_photo': user.profile_photo})
    else:
        return jsonify({'message': 'Invalid credentials'}), 401


# Route to validate a user's password
@api_bp.route('/validate_password', methods=['POST'])
def validate_password():
    # Extract the token from the request headers
    token = request.headers.get('Authorization')
    user_id = decode_token(token)

    if user_id:
        user = User.query.get(user_id)
        if user:
            data = request.get_json()
            provided_password = data.get('password')

            # Check if the provided password matches the user's password
            if user.password == provided_password:
                return jsonify({'message': 'Password is valid'}), 200
            return jsonify({'message': 'Invalid password'}), 401

        return jsonify({'message': 'User not found'}), 404

    return jsonify({'message': 'User not authenticated'}), 401


# Route to get or update user details
@api_bp.route('/user', methods=['GET', 'POST'])
def user_details():
    if request.method == 'GET':
        # Handle GET request to fetch user details
        token = request.headers.get('Authorization')
        user_id = decode_token(token)
        if user_id:
            user = User.query.get(user_id)
            if user:
                return jsonify({'username': user.username, 'email': user.email, 'profile_photo': user.profile_photo})
        return jsonify({'message': 'User not found'}), 404

    elif request.method == 'POST':
        # Handle POST request to update user details
        token = request.headers.get('Authorization')
        user_id = decode_token(token)
        if user_id:
            user = User.query.get(user_id)
            if user:
                data = request.get_json()
                if 'username' in data:
                    user.username = data['username']
                if 'email' in data:
                    user.email = data['email']
                if 'password' in data:
                    user.password = data['password']
                db.session.commit()
                return jsonify({'message': 'User details updated successfully'}), 200
        return jsonify({'message': 'User not found'}), 404


# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Route to upload a profile picture
@api_bp.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    # Extract the token from the request headers
    token = request.headers.get('Authorization')
    user_id = decode_token(token)

    if user_id:
        user = User.query.get(user_id)
        if user:
            # Check if a file is part of the request
            if 'profile_picture' not in request.files:
                return jsonify({'message': 'No file part'}), 400

            file = request.files['profile_picture']
            if file.filename == '':
                return jsonify({'message': 'No selected file'}), 400

            # Validate the file type and save the file
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(file_path)

                # Update user's profile photo URL
                user.profile_photo = file_path
                db.session.commit()

                return jsonify(
                    {'message': 'Profile picture uploaded successfully', 'profile_photo_url': file_path}), 200

            return jsonify({'message': 'Invalid file type'}), 400

        return jsonify({'message': 'User not found'}), 404

    return jsonify({'message': 'User not authenticated'}), 401


# Route to add a new camera
@api_bp.route('/add_camera', methods=['POST'])
def add_camera():
    token = request.headers.get('Authorization')
    user_id = decode_token(token)
    if user_id:
        data = request.get_json()
        new_camera = Camera(name=data['name'], location=data['location'], ip_address=data['ip_address'])
        db.session.add(new_camera)
        db.session.commit()
        return jsonify({'message': 'Camera added successfully', 'id': new_camera.id})
    return jsonify({'message': 'User not authenticated'}), 401


# Route to get all cameras
@api_bp.route('/get_cameras', methods=['GET'])
def get_cameras():
    token = request.headers.get('Authorization')
    user_id = decode_token(token)
    if user_id:
        cameras = Camera.query.all()
        camera_list = [
            {'id': camera.id, 'name': camera.name, 'location': camera.location, 'ip_address': camera.ip_address} for
            camera in cameras]
        return jsonify({'cameras': camera_list})
    return jsonify({'message': 'User not authenticated'}), 401


# Route to update a specific camera
@api_bp.route('/update_camera/<int:camera_id>', methods=['PUT'])
def update_camera(camera_id):
    token = request.headers.get('Authorization')
    user_id = decode_token(token)
    if user_id:
        camera = Camera.query.get(camera_id)
        if camera:
            data = request.get_json()
            camera.name = data.get('name', camera.name)
            camera.location = data.get('location', camera.location)
            camera.ip_address = data.get('ip_address', camera.ip_address)
            db.session.commit()
            return jsonify({'message': 'Camera updated successfully'})
        return jsonify({'message': 'Camera not found'}), 404
    return jsonify({'message': 'User not authenticated'}), 401


# Route to delete a specific camera
@api_bp.route('/delete_camera/<int:camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    token = request.headers.get('Authorization')
    user_id = decode_token(token)
    if user_id:
        camera = Camera.query.get(camera_id)
        if camera:
            db.session.delete(camera)
            db.session.commit()
            return jsonify({'message': 'Camera deleted successfully'})
        return jsonify({'message': 'Camera not found'}), 404
    return jsonify({'message': 'User not authenticated'}), 401


# Route to get all events
@api_bp.route('/get_events', methods=['GET'])
def get_events():
    events = Event.query.all()
    event_list = [{'id': event.id, 'event_type': event.event_type, 'timestamp': event.timestamp, 'title': event.title}
                  for event in events]
    return jsonify({'events': event_list})


# Route to get details of a specific event
@api_bp.route('/get_event_details/<int:event_id>', methods=['GET'])
def get_event_details(event_id):
    event = Event.query.get(event_id)
    if event:
        return jsonify(
            {'id': event.id, 'event_type': event.event_type, 'timestamp': event.timestamp, 'title': event.title,
             'footage_id': event.footage_id})
    return jsonify({'message': 'Event not found'}), 404


# Route to insert a new event
@api_bp.route('/insert_event', methods=['POST'])
def insert_event():
    data = request.get_json()
    new_event = Event(event_type=data['event_type'], timestamp=datetime.utcnow(), title=data.get('title'),
                      footage_id=data['footage_id'])
    db.session.add(new_event)
    db.session.commit()

    # Send notifications about the new event
    send_notifications(new_event.id)

    return jsonify({'message': 'Event inserted successfully', 'id': new_event.id})


# Route to get all footage records
@api_bp.route('/get_footage', methods=['GET'])
def get_footage():
    footages = Footage.query.all()
    footage_list = [{'id': footage.id, 'file_path': footage.file_path, 'duration': footage.duration,
                     'creation_timestamp': footage.creation_timestamp} for footage in footages]
    return jsonify({'footage': footage_list})


# Route to get details of a specific footage
@api_bp.route('/get_footage_details/<int:footage_id>', methods=['GET'])
def get_footage_details(footage_id):
    footage = Footage.query.get(footage_id)
    if footage:
        return jsonify({'id': footage.id, 'file_path': footage.file_path, 'duration': footage.duration,
                        'creation_timestamp': footage.creation_timestamp})
    return jsonify({'message': 'Footage not found'}), 404


# Route to insert new footage
@api_bp.route('/insert_footage', methods=['POST'])
def insert_footage():
    data = request.get_json()
    new_footage = Footage(file_path=data['file_path'], duration=data['duration'], creation_timestamp=datetime.utcnow())
    db.session.add(new_footage)
    db.session.commit()
    return jsonify({'message': 'Footage inserted successfully', 'id': new_footage.id})


# Route to get all notifications
@api_bp.route('/get_notifications', methods=['GET'])
def get_notifications():
    notifications = Notification.query.all()
    notification_list = [{'id': notification.id, 'user_id': notification.user_id, 'event_id': notification.event_id,
                          'notification_type': notification.notification_type,
                          'creation_timestamp': notification.creation_timestamp} for notification in notifications]
    return jsonify({'notifications': notification_list})
