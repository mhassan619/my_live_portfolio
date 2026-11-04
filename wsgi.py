"""
WSGI configuration for PythonAnywhere and production WSGI servers.
Exposes the WSGI callable named `application`.
"""
import os
import sys

# Ensure project root is in Python's import path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Import application factory and instantiate application
from app import create_app

application = create_app()

if __name__ == "__main__":
    application.run()
