from flask import Flask

def create_app():
    """
    Creates and configures an instance of the Flask application.
    This is the application factory.
    """
    # Create the Flask application instance
    app = Flask(__name__)

    # In a real application, you would initialize extensions here:
    # from .extensions import db, migrate
    # db.init_app(app)
    # migrate.init_app(app, db)

    # Load the pickled data into memory at startup
    with app.app_context():
        from .database import load_pickled_data
        app.pickled_shop_data = load_pickled_data()

    # Import and register the routes from the routes.py file.
    # The import is done here to avoid circular dependencies, as routes.py
    # will need to import the 'app' instance.
    with app.app_context():
        from . import routes

    return app
