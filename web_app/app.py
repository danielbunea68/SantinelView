from flask import Flask, send_from_directory
import os
import logging
from routes import routes

# Define the directory paths for uploads and analyses
UPLOAD_FOLDER = '../uploads/profile_pictures'
ANALYSES_FOLDER = 'analyses/'

# Ensure that the upload folder exists, create it if it doesn't
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the Flask application
app = Flask(__name__)

# Disable the default Flask logging to clean up console output
log = logging.getLogger('werkzeug')
log.disabled = True
app.logger.disabled = True

# Configure the app with the upload and analyses folders
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ANALYSES_FOLDER'] = ANALYSES_FOLDER

# Set a secret key for session management and other security-related features
app.config['SECRET_KEY'] = '2946230ef8345ecb6ea4a41ed4d8f0bb162a89e6dcf6c77a10c48c768ce85496'


# Route to serve profile pictures from the uploads folder
@app.route('/uploads/profile_pictures/<filename>')
def uploaded_file(filename):
    # Send the requested file from the configured upload folder
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# Route to serve analysis files from the analyses folder
@routes.route('/analyses/<filename>')
def get_analysis_file(filename):
    # Build the full path to the analyses folder
    full_path = os.path.join(os.getcwd(), app.config['ANALYSES_FOLDER'])
    # Send the requested file from the analyses folder
    return send_from_directory(full_path, filename)


# Register the routes from the external 'routes' module
app.register_blueprint(routes)

# Run the application if this script is executed directly
if __name__ == '__main__':
    app.run(debug=True, port=5000)
