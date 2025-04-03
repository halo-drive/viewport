import requests
from flask import Blueprint, jsonify
from config import Config

weather_test_bp = Blueprint('weather_test', __name__)

@weather_test_bp.route('/api/test/weather')
def test_weather_api():
    # Weather API key and endpoint
    weather_api_key = Config.WEATHER_API_KEY
    WEATHER_API_URL = "http://api.weatherapi.com/v1/forecast.json"
    
    # Test coordinates (London)
    lat, lon = 51.5074, -0.1278
    
    # Parameters for the request
    params = {
        "key": weather_api_key,
        "q": f"{lat},{lon}",
        "days": 1,
        "aqi": "no",
        "alerts": "no"
    }
    
    try:
        # Make the request
        response = requests.get(WEATHER_API_URL, params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            weather_data = response.json()
            
            # Extract some basic weather info for the response
            location = weather_data.get('location', {}).get('name', 'Unknown')
            current_temp = weather_data.get('current', {}).get('temp_c', 'Unknown')
            condition = weather_data.get('current', {}).get('condition', {}).get('text', 'Unknown')
            
            return jsonify({
                "success": True,
                "message": "Weather API is working correctly",
                "data": {
                    "location": location,
                    "temperature": current_temp,
                    "condition": condition
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Weather API returned status code {response.status_code}",
                "error": response.text
            })
    
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error connecting to Weather API",
            "error": str(e)
        })