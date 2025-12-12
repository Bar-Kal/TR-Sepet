from flask import Flask

def create_app():
    """
    Creates and configures an instance of the Flask application.
    This is the application factory.
    """
    # Create the Flask application instance
    app = Flask(__name__)

    # Data will be loaded on-demand.
    with app.app_context():
        from . import routes

    return app
