from flask import Flask
from models import db
from routes import api_bp
import logging


def create_app():
    # Create a new Flask application instance
    app = Flask(__name__)

    # Disable the default Flask logger (Werkzeug) and application logger to prevent logging output
    log = logging.getLogger('werkzeug')
    log.disabled = True
    app.logger.disabled = True

    # Configure the SQLite database URI for SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

    # Disable the modification tracking feature of SQLAlchemy to save resources
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Set a secret key for session management and other security-related needs
    app.config['SECRET_KEY'] = '2946230ef8345ecb6ea4a41ed4d8f0bb162a89e6dcf6c77a10c48c768ce85496'

    # Initialize the database with the Flask app
    db.init_app(app)

    # Register the API blueprint with a URL prefix of '/api'
    app.register_blueprint(api_bp, url_prefix='/api')

    # Return the created Flask app instance
    return app


# Check if the script is executed directly (and not imported)
if __name__ == '__main__':
    # Create the Flask app by calling the create_app function
    main = create_app()

    # Create all database tables within the app's context
    with main.app_context():
        db.create_all()

    # Run the Flask app in debug mode on port 5001
    main.run(debug=True, port=5001)
