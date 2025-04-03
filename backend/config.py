# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # API Keys
    MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN")
    WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
    HERE_API_KEY = os.environ.get("HERE_API_KEY")
    GEOCODING_API_KEY = os.environ.get("GEOCODING_API_KEY")
    
    # Flask configurations
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24))
    
    # Database settings
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "users.db")
    
    # Default values for development (will be overridden by env vars if set)
    DEBUG = os.environ.get("DEBUG", "True") == "True"