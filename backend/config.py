# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# Assumes .env file is in the directory where the app is run (usually 'backend')
# or in the parent directory.
load_dotenv()

class Config:
    # API Keys
    MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN")
    WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
    HERE_API_KEY = os.environ.get("HERE_API_KEY")
    GEOCODING_API_KEY = os.environ.get("GEOCODING_API_KEY")
    API_KEY = os.environ.get("API_KEY")

    # Flask configurations
    SECRET_KEY = os.environ.get("SECRET_KEY") # Set a strong default in .env

    # <<<--- ADD THESE LINES FOR ADMIN CREDS --->>>
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
    # <<<--------------------------------------->>>

    # Database settings
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "users.db")

    # Default values for production (can be overridden by .env for development)
    # <<<--- CHANGE DEBUG DEFAULT TO False --->>>
    DEBUG = os.environ.get("DEBUG", "False") == "True"
    # <<<------------------------------------->>>