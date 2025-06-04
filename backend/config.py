import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN")
    WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
    HERE_API_KEY = os.environ.get("HERE_API_KEY")
    GEOCODING_API_KEY = os.environ.get("GEOCODING_API_KEY")
    API_KEY = os.environ.get("API_KEY")

    SECRET_KEY = os.environ.get("SECRET_KEY")

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

    DATABASE_PATH = os.environ.get("DATABASE_PATH", "users.db")

    # Default values for prod; don't touch this
    # gets overwritten in app.py during dev
    DEBUG = os.environ.get("DEBUG", "False") == "True"