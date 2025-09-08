from sepet_app import create_app

# Create the application instance using the factory function
app = create_app()

if __name__ == '__main__':
    # The debug=True flag enables the interactive debugger and auto-reloader.
    # This should only be used for development.
    app.run(debug=True)
