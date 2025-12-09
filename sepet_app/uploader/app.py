import os
from flask import Flask, request, redirect, url_for, flash, render_template
from werkzeug.utils import secure_filename

from jinja2 import ChoiceLoader, FileSystemLoader

def create_app():
    """
    Creates and configures an instance of the Flask application for file uploading.
    """
    # Create the Flask application instance
    app = Flask(__name__, static_folder='../frontend/static')
    
    # Set up the template loader to look in both the uploader's and the frontend's template folders
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(os.path.join(app.root_path, 'templates')),
        FileSystemLoader(os.path.join(app.root_path, '../frontend/templates'))
    ])

    # Path for uploaded files
    upload_folder = os.path.abspath(os.path.join(app.root_path, '..', 'frontend', 'database'))
    app.config['UPLOAD_FOLDER'] = upload_folder
    
    # Secret key for flashing messages
    app.config['SECRET_KEY'] = 'supersecretkey'

    # Ensure the upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    @app.route('/', methods=['GET', 'POST'])
    def upload_file():
        if request.method == 'POST':
            # Check if the post request has the file part
            if 'file' not in request.files:
                flash('No file part', 'danger')
                return redirect(request.url)
            file = request.files['file']
            # If the user does not select a file, the browser submits an
            # empty file without a filename.
            if file.filename == '':
                flash('No selected file', 'warning')
                return redirect(request.url)
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                flash('File successfully uploaded', 'success')
                return redirect(url_for('upload_file'))
        return render_template('upload.html', title='Dosya Yükle')

    @app.route('/index')
    def index():
        return redirect('http://localhost:5000')

    @app.route('/about')
    def about():
        return redirect('http://localhost:5000/about')

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.getenv("PORT", default=5001))
