import os
import requests
from flask import Flask, request, redirect, url_for, render_template
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

    # Load app url
    app.config['INTERNAL_APP_DOMAIN'] = os.getenv('INTERNAL_APP_DOMAIN')

    @app.route('/', methods=['GET', 'POST'])
    def upload_file():
        message = None
        category = None
        if request.method == 'POST':
            if 'file' not in request.files or 'secret_key' not in request.form:
                message = 'File or secret key not provided'
                category = 'danger'
                return render_template('upload.html', title='Dosya Yükle', message=message, category=category)

            file = request.files['file']
            secret_key = request.form.get('secret_key')

            if file.filename == '' or secret_key == '':
                message = 'No selected file or secret key'
                category = 'warning'
                return render_template('upload.html', title='Dosya Yükle', message=message, category=category)

            if file:
                try:
                    files = {'file': (file.filename, file.read(), file.content_type)}
                    data = {'secret_key': secret_key}
                    response = requests.post(app.config['INTERNAL_APP_DOMAIN'], files=files, data=data)
                    
                    if response.status_code == 200:
                        message = 'File successfully uploaded'
                        category = 'success'
                    else:
                        message = f"Failed to upload file: {response.json().get('error', 'Unknown error')}"
                        category = 'danger'

                except requests.exceptions.RequestException as e:
                    message = f"An error occurred: {e}"
                    category = 'danger'
                
                return render_template('upload.html', title='Dosya Yükle', message=message, category=category)

        return render_template('upload.html', title='Dosya Yükle', message=message, category=category)

    @app.route('/index')
    def index():
        return redirect('http://localhost:5001')

    @app.route('/about')
    def about():
        return redirect('http://localhost:5001/about')

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
