import jwt
from flask import current_app
from datetime import datetime, timedelta


def generate_token(user_id):
    try:
        # Create the payload for the JWT, which includes:
        # 'exp' (Expiration time): The token's expiration time, set to 1 day from now
        # 'iat' (Issued at time): The time the token is issued
        # 'sub' (Subject): The user ID, representing the token's subject
        payload = {
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
            'sub': user_id
        }
        # Encode the JWT using the SECRET_KEY from the Flask application's config and return it
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    except Exception as e:
        # If an exception occurs during token generation, return the exception message as a string
        return str(e)


def decode_token(token):
    try:
        # Decode the JWT using the SECRET_KEY from the Flask application's config
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        # Return the 'sub' field from the payload, which contains the user ID
        return payload['sub']
    except jwt.ExpiredSignatureError:
        # If the token has expired, return an appropriate error message
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        # If the token is invalid for any other reason, return an appropriate error message
        return 'Invalid token. Please log in again.'
