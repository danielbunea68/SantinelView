import json
import pytest
from app import create_app
from models import db


# Fixture to set up and tear down the test client
@pytest.fixture
def client():
    # Create a test application and set it to testing mode
    app = create_app()
    app.config['TESTING'] = True
    # Use an in-memory SQLite database for testing
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_database.db'
    with app.test_client() as client:
        # Create all database tables before each test
        with app.app_context():
            db.create_all()
        yield client
        # Drop all database tables after each test
        with app.app_context():
            db.drop_all()


# Test user registration functionality
def test_register_user(client):
    data = {'username': 'test_user', 'email': 'test@example.com', 'password': 'pwd'}
    response = client.post('/api/register', json=data)
    assert response.status_code == 201  # Check for HTTP 201 Created status
    assert b"User registered successfully" in response.data  # Verify success message in response


# Test user login functionality
def test_login_user(client):
    data = {'username': 'test_user', 'email': 'test@example.com', 'password': 'pwd'}
    client.post('/api/register', json=data)  # Register the user first
    response = client.post('/api/login', json=data)
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"token" in response.data  # Verify that a token is returned


# Test fetching user details
def test_get_user_details(client):
    user_data = {'username': 'test_user', 'email': 'test@example.com', 'password': 'pwd'}
    client.post('/api/register', json=user_data)
    login_data = {'username': 'test_user', 'password': 'pwd'}
    login_response = client.post('/api/login', json=login_data)
    token = json.loads(login_response.data)['token']

    response = client.get('/api/user', headers={'Authorization': f'{token}'})
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"test_user" in response.data  # Verify user details in the response


# Test adding a new camera
def test_add_camera(client):
    user_data = {'username': 'test_user', 'email': 'test@example.com', 'password': 'pwd'}
    client.post('/api/register', json=user_data)
    login_data = {'username': 'test_user', 'password': 'pwd'}
    login_response = client.post('/api/login', json=login_data)
    token = json.loads(login_response.data)['token']

    camera_data = {'name': 'Test Camera', 'location': 'Test Location', 'ip_address': '192.168.1.1'}
    response = client.post('/api/add_camera', json=camera_data, headers={'Authorization': f'{token}'})
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"Camera added successfully" in response.data  # Verify success message in response


# Test retrieving the list of cameras
def test_get_cameras(client):
    user_data = {'username': 'test_user', 'email': 'test@example.com', 'password': 'pwd'}
    client.post('/api/register', json=user_data)
    login_data = {'username': 'test_user', 'password': 'pwd'}
    login_response = client.post('/api/login', json=login_data)
    token = json.loads(login_response.data)['token']

    camera_data = {'name': 'Test Camera', 'location': 'Test Location', 'ip_address': '192.168.1.1'}
    client.post('/api/add_camera', json=camera_data, headers={'Authorization': f'{token}'})

    response = client.get('/api/get_cameras', headers={'Authorization': f'{token}'})
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"Test Camera" in response.data  # Verify camera details in the response


# Test updating a camera's details
def test_update_camera(client):
    user_data = {'username': 'test_user', 'email': 'test@example.com', 'password': 'pwd'}
    client.post('/api/register', json=user_data)
    login_data = {'username': 'test_user', 'password': 'pwd'}
    login_response = client.post('/api/login', json=login_data)
    token = json.loads(login_response.data)['token']

    camera_data = {'name': 'Test Camera', 'location': 'Test Location', 'ip_address': '192.168.1.1'}
    client.post('/api/add_camera', json=camera_data, headers={'Authorization': f'{token}'})

    update_data = {'name': 'Updated Camera Name'}
    response = client.put('/api/update_camera/1', json=update_data, headers={'Authorization': f'{token}'})
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"Camera updated successfully" in response.data  # Verify success message in response


# Test deleting a camera
def test_delete_camera(client):
    user_data = {'username': 'test_user', 'email': 'test@example.com', 'password': 'pwd'}
    client.post('/api/register', json=user_data)
    login_data = {'username': 'test_user', 'password': 'pwd'}
    login_response = client.post('/api/login', json=login_data)
    token = json.loads(login_response.data)['token']

    camera_data = {'name': 'Test Camera', 'location': 'Test Location', 'ip_address': '192.168.1.1'}
    client.post('/api/add_camera', json=camera_data, headers={'Authorization': f'{token}'})

    response = client.delete('/api/delete_camera/1', headers={'Authorization': f'{token}'})
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"Camera deleted successfully" in response.data  # Verify success message in response


# Test retrieving all events
def test_get_events(client):
    response = client.get('/api/get_events')
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"events" in response.data  # Verify that 'events' key is present in the response


# Test retrieving details of a specific event
def test_get_event_details(client):
    # First, insert footage to obtain a valid footage_id
    footage_data = {'file_path': '/path/to/footage.mp4', 'duration': 60}
    footage_response = client.post('/api/insert_footage', json=footage_data)
    assert footage_response.status_code == 200  # Check for HTTP 200 OK status
    footage_id = json.loads(footage_response.data)['id']

    # Insert an event linked to the footage
    event_data = {'event_type': 'Test Event', 'title': 'Test title', 'footage_id': footage_id}
    client.post('/api/insert_event', json=event_data)

    # Retrieve event details
    response = client.get('/api/get_event_details/1')
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"Test Event" in response.data  # Verify event details in the response


# Test inserting a new event
def test_insert_event(client):
    # Insert footage to obtain a valid footage_id
    footage_data = {'file_path': '/path/to/footage.mp4', 'duration': 60}
    footage_response = client.post('/api/insert_footage', json=footage_data)
    assert footage_response.status_code == 200  # Check for HTTP 200 OK status
    footage_id = json.loads(footage_response.data)['id']

    # Insert an event
    event_data = {'event_type': 'Test Event', 'title': 'Test title', 'footage_id': footage_id}
    response = client.post('/api/insert_event', json=event_data)
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"Event inserted successfully" in response.data  # Verify success message in response


# Test retrieving all footage records
def test_get_footage(client):
    response = client.get('/api/get_footage')
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"footage" in response.data  # Verify that 'footage' key is present in the response


# Test retrieving details of a specific footage
def test_get_footage_details(client):
    footage_data = {'file_path': '/path/to/footage.mp4', 'duration': 60}
    client.post('/api/insert_footage', json=footage_data)

    response = client.get('/api/get_footage_details/1')
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"/path/to/footage.mp4" in response.data  # Verify footage details in the response


# Test inserting a new footage record
def test_insert_footage(client):
    footage_data = {'file_path': '/path/to/footage.mp4', 'duration': 60}
    response = client.post('/api/insert_footage', json=footage_data)
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"Footage inserted successfully" in response.data  # Verify success message in response


# Test retrieving all notifications
def test_get_notifications(client):
    response = client.get('/api/get_notifications')
    assert response.status_code == 200  # Check for HTTP 200 OK status
    assert b"notifications" in response.data  # Verify that 'notifications' key is present in the response
