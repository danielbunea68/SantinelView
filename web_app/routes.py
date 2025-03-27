import os
import cv2
from flask import Blueprint, render_template, request, redirect, url_for, session, Response
import requests
from datetime import datetime, timedelta
from collections import Counter

# Create a Blueprint for the routes, which allows for modular application design
routes = Blueprint('routes', __name__)

# Define the directory for storing analysis files, relative to the current file's directory
ANALYSES_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'analyses'))

# Base URL for the API that the application will communicate with
API_BASE_URL = "http://127.0.0.1:5001/api"


# Route for the home page
@routes.route('/')
def home():
    # Redirect to the login page if the user is not logged in
    if 'user' not in session:
        return redirect(url_for('routes.login'))

    # Fetch events from the API
    response = requests.get(f"{API_BASE_URL}/get_events")
    data = response.json() if response.status_code == 200 else {}

    # Filter events that occurred in the last 24 hours
    now = datetime.now()
    recent_events = [
        event for event in data['events']
        if datetime.strptime(event['timestamp'], '%a, %d %b %Y %H:%M:%S %Z') >= now - timedelta(hours=24)
    ]
    # Sort recent events by ID in descending order
    recent_events.sort(key=lambda x: x['id'], reverse=True)

    # Generate dates for the last two weeks
    today = now.date()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(13, -1, -1)]

    # Count the number of events per day in the last two weeks
    event_counts_dict = Counter(
        datetime.strptime(event['timestamp'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y-%m-%d')
        for event in data['events'] if
        datetime.strptime(event['timestamp'], '%a, %d %b %Y %H:%M:%S %Z').date() in [today - timedelta(days=i) for i in
                                                                                     range(14)]
    )

    # Create a list of event counts corresponding to each date in the `dates` list
    event_counts = [event_counts_dict.get(date, 0) for date in dates]

    # Render the home page template with the recent events and their counts
    return render_template('index.html',
                           recent_events=recent_events,
                           recent_events_count=len(recent_events),
                           dates=dates,
                           event_counts=event_counts)


# Route to log the user out
@routes.route('/logout')
def logout():
    # Remove the user from the session if logged in
    if 'user' in session:
        session.pop('user', None)
    return redirect(url_for('routes.home'))


# Route to browse all events
@routes.route('/browse-events')
def browse_events():
    # Redirect to the login page if the user is not logged in
    if 'user' not in session:
        return redirect(url_for('routes.login'))

    # Fetch all events from the API
    response = requests.get(f"{API_BASE_URL}/get_events")
    events = response.json()['events'] if response.status_code == 200 else []
    # Sort events by ID in descending order
    events.sort(key=lambda x: x['id'], reverse=True)

    # Render the browse events page with the list of events
    return render_template('browse_events.html', events=events)


# Route to view details of a specific event by event ID
@routes.route('/event/<int:event_id>', methods=['GET'])
def event_details(event_id):
    # Redirect to the login page if the user is not logged in
    if 'user' not in session:
        return redirect(url_for('routes.login'))

    # Fetch event details from the API
    response_event = requests.get(f"{API_BASE_URL}/get_event_details/{event_id}")
    event = response_event.json() if response_event.status_code == 200 else {}

    video_url = ''
    analysis = ''
    if event:
        footage_id = event.get('footage_id')
        if footage_id:
            # Fetch the associated footage details from the API
            response_footage = requests.get(f"{API_BASE_URL}/get_footage_details/{footage_id}")
            footage_path = response_footage.json() if response_footage.status_code == 200 else None
            video_url = footage_path['file_path']

            # Construct the path to the summary analysis file
            base_name = os.path.splitext(footage_path['file_path'])[0].rsplit('_', 1)[0]
            new_filename = f"{base_name}_summary.txt"
            analysis_path = os.path.join(ANALYSES_FOLDER, new_filename)

            # Read the analysis summary from the file
            with open(analysis_path, 'r') as file:
                analysis = file.read()

    # Render the event details page, including the footage and analysis
    return render_template('event_details.html', event=event, video_url=video_url, analysis=analysis)


# Route for user login
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle the login form submission
        username = request.form['username']
        password = request.form['password']
        # Attempt to authenticate with the API
        response = requests.post(f"{API_BASE_URL}/login", json={'username': username, 'password': password})
        if response.status_code == 200:
            token = response.json().get('token')
            session['user'] = {'username': username, 'token': token,
                               'profile_photo': response.json().get('profile_photo')}
            return redirect(url_for('routes.home'))
        else:
            # Render the login page with an error message if authentication fails
            return render_template('login.html', message="Invalid credentials")

    # Render the login page for GET requests
    return render_template('login.html')


# Route for user registration
@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Handle the registration form submission
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # Attempt to register the user with the API
        response = requests.post(f"{API_BASE_URL}/register",
                                 json={'username': username, 'email': email, 'password': password})
        if response.status_code == 201:
            return redirect(url_for('routes.login'))
        else:
            # Render the registration page with an error message if registration fails
            return render_template('register.html', message="Registration failed")

    # Render the registration page for GET requests
    return render_template('register.html')


# Route for viewing and updating the user profile
@routes.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        return redirect(url_for('routes.login'))

    user = session['user']
    if request.method == 'POST':
        # Handle profile update
        username = request.form.get('username')
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        current_password = request.form.get('current_password')
        profile_picture = request.files.get('profile_picture')

        if new_password and (new_password != confirm_password):
            # Handle password mismatch error
            return render_template('profile.html', user=user, error="Passwords do not match")

        if current_password:
            # Validate current password if changing the password
            response = requests.post(f"{API_BASE_URL}/validate_password", json={'password': current_password},
                                     headers={'Authorization': f"{user['token']}"})
            if response.status_code != 200:
                # Handle current password validation error
                return render_template('profile.html', user=user, error="Current password is incorrect")

        if username and username != user['username'] or email and email != user['email'] or new_password:
            # Update the user information if there are changes
            user_update_payload = {'username': username, 'email': email}
            if new_password:
                user_update_payload['password'] = new_password

            response = requests.post(f"{API_BASE_URL}/user", json=user_update_payload,
                                     headers={'Authorization': f"{user['token']}"})
            if response.status_code == 200:
                user['username'] = username
                user['email'] = email
                if new_password:
                    # Log the user out if the password was changed
                    session.pop('user', None)
                    return redirect(url_for('routes.login'))

        if profile_picture:
            # Handle profile picture upload
            file = {'profile_picture': (profile_picture.filename, profile_picture.stream, profile_picture.content_type)}
            response = requests.post(f"{API_BASE_URL}/upload_profile_picture", files=file,
                                     headers={'Authorization': f"{user['token']}"})
            if response.status_code == 200:
                user['profile_photo'] = response.json().get('profile_photo_url')
            else:
                # Handle profile picture upload error
                return render_template('profile.html', user=user, error="Failed to upload profile picture")

        # Update the session with the new user information
        session['user'] = user
        return redirect(url_for('routes.profile'))

    # Fetch the current user's information from the API
    response = requests.get(f"{API_BASE_URL}/user", headers={'Authorization': f"{user['token']}"})
    if response.status_code == 200:
        user_info = response.json()
        return render_template('profile.html', user=user_info)

    # Redirect to the login page if the user information couldn't be fetched
    return redirect(url_for('routes.login'))


# Route for displaying the live video feed
@routes.route('/live-feed')
def live_feed():
    if 'user' not in session:
        return redirect(url_for('routes.login'))

    return render_template('live_feed.html')


# Route that provides the video feed stream
@routes.route('/video_feed')
def video_feed():
    # Return the video stream as a multipart response
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# Function to generate frames for the live video feed
def generate_frames():
    camera = cv2.VideoCapture(2)  # Open the external camera

    while True:
        success, frame = camera.read()  # Capture frame-by-frame
        if not success:
            break  # Exit the loop if the frame is not captured successfully
        else:
            ret, buffer = cv2.imencode('.jpg', frame)  # Encode the frame as JPEG
            frame = buffer.tobytes()  # Convert the frame to bytes
            yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'  # Yield the frame as a response
