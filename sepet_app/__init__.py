from flask import Flask
from config import Config


def create_app(config_class=Config):
    """
    Creates and configures an instance of the Flask application.
    This is the application factory.
    """
    # Create the Flask application instance
    app = Flask(__name__)

    # Load the configuration from the config.py file
    app.config.from_object(config_class)

    # In a real application, you would initialize extensions here:
    # from .extensions import db, migrate
    # db.init_app(app)
    # migrate.init_app(app, db)

    # Import and register the routes from the routes.py file.
    # The import is done here to avoid circular dependencies, as routes.py
    # will need to import the 'app' instance.
    with app.app_context():
        from . import routes

    return app
