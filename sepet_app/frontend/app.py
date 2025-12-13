import os
from flask import Flask

def create_app():
    """
    Creates and configures an instance of the Flask application.
    This is the application factory.
    """
    # Create the Flask application instance
    app = Flask(__name__)

    # Load secret from environment variable
    app.config['UPLOAD_SECRET_KEY'] = os.getenv('UPLOAD_SECRET_KEY')

    # Define the database folder
    database_folder = os.path.abspath(os.path.join(app.root_path, 'database'))
    app.config['DATABASE_FOLDER'] = database_folder

    # The data will be loaded on-demand per request.
    with app.app_context():
        import routes

    return app

# Create the application instance using the factory function
app = create_app()

if __name__ == '__main__':
    # The debug=True flag enables the interactive debugger and auto-reloader.
    # This should only be used for development.
    app.run(debug=True, host='0.0.0.0', port=os.getenv("PORT", default=5000))
