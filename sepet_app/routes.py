import os
from loguru import logger
import random
import time
from datetime import datetime
from flask import render_template, current_app, redirect, request
import pandas as pd
from pathlib import Path
from .scraper import A101Scraper, Scraper

# By using current_app, we access the application instance created by the factory.
# This is a clean way to access the app without circular imports.
@current_app.route('/')
@current_app.route('/index')
def index():
    """Renders the home page."""
    # The render_template function automatically looks in the 'templates' folder.
    return render_template('index.html', title='Home')


@current_app.route('/about')
def about():
    """Renders a simple about page."""
    return "<h1>About This Application</h1>"


@current_app.route('/test')
def test():
    """Renders a simple about page."""
    dummy = request.args.to_dict()
    print(dummy['shop_name'])
    #combine_and_deduplicate_csvs(base_downloads_path=Path(os.path.join('sepet_app', 'downloads', '2025-test', 'A101')))
    return "<h1>You reached the Test endpoint</h1>"
