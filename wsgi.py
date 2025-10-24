"""
WSGI Entry Point for Swath Movers Application

This file serves as the entry point for Gunicorn to load the Flask application.
It imports the Flask app instance and makes it available for the WSGI server.
"""

from app import app

if __name__ == "__main__":
    app.run()
