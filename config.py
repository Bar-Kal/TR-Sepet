import os


class Config:
    """Base configuration settings."""
    # A secret key is required for session management and other security features.
    # It's best practice to set this from an environment variable.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess-this-secret'

    # Example for database configuration
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #     'sqlite:///site.db'
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
