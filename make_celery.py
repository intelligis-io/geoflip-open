from app import create_app

# Create the Flask app using the factory function
flask_app = create_app()

# Access the Celery app instance from the Flask app
celery_app = flask_app.extensions["celery"]
