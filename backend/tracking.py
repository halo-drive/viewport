# tracking.py - Modified to act as a utility module for diesel_api.py

import requests
import re
from typing import Tuple, List
from datetime import datetime
from config import Config # Keep Config import for API keys

# URLs for the APIs needed by the functions below
GEOCODING_API_URL = "https://geocode.maps.co/search"
MAPBOX_DIRECTIONS_API_URL = "https://api.mapbox.com/directions/v5/mapbox/driving-traffic/"
WEATHER_API_URL = "http://api.weatherapi.com/v1/forecast.json"

# API tokens from config needed by the functions below
# Note: WEATHER_API_KEY is retrieved directly in diesel_api.py, so not needed here.
MAPBOX_ACCESS_TOKEN = Config.MAPBOX_TOKEN
geocoding_api = Config.GEOCODING_API_KEY

# --- Functions imported by diesel_api.py ---

def get_coordinates(place_name: str) -> Tuple[float, float]:
    """Gets coordinates using Geocode.maps.co API."""
    params = {
        "q": f"{place_name}",
        "api_key": geocoding_api
    }

    try:
        response = requests.get(GEOCODING_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        # Handle cases where data might be empty or not structured as expected
        if not data:
             print(f"Error: No data received from geocoding API for {place_name}")
             return None, None
        # Find the place with the highest importance, requires data to be a list of dicts
        if isinstance(data, list) and data:
             max_importance_place = max(data, key=lambda place: place.get('importance', 0))
             coords = (float(max_importance_place['lat']), float(max_importance_place['lon']))
             return coords
        else:
             # Attempt to handle non-list response if possible, or return error
             print(f"Error: Unexpected data format from geocoding API for {place_name}")
             return None, None


    except requests.exceptions.RequestException as e:
        print(f"Error retrieving coordinates: {e}")
        return None, None
    except (KeyError, ValueError, TypeError) as e:
        print(f"Error processing coordinate data for {place_name}: {e}")
        return None, None


def calculate_distances(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Tuple[float, float]:
    """Calculates city/highway distances using Mapbox Directions API."""
    # Check for valid coordinates
    if start_coords is None or end_coords is None or start_coords[0] is None or start_coords[1] is None or end_coords[0] is None or end_coords[1] is None:
        print("Error: Invalid start or end coordinates provided for distance calculation.")
        return 0.0, 0.0

    city_distance_m = 0
    highway_distance_m = 0
    # Corrected Regex: Uses raw string r'' and matches A, B, or M followed by digits
    # Matches common UK road classifications (e.g., M1, A40, B123)
    highway_pattern = re.compile(r'\b[ABM]\d+\b', re.IGNORECASE)


    params = {
        "access_token": MAPBOX_ACCESS_TOKEN,
        "alternatives": "false",
        "geometries": "geojson",
        "language": "en",
        "overview": "simplified", # Consider 'full' for more detail if needed
        "steps": "true",
        "notifications": "none",
        # Consider adding profile: 'driving-traffic' for consistency if MAPBOX_DIRECTIONS_API_URL uses it
    }

    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    # Ensure URL encoding is correct for coordinates
    url = f"{MAPBOX_DIRECTIONS_API_URL}{start_lon},{start_lat};{end_lon},{end_lat}"


    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Raises HTTPError for bad responses (4XX, 5XX)
        route_data = response.json()

        # Check if routes are found
        if not route_data.get("routes"):
             print("Error: No routes found between the specified coordinates.")
             return 0.0, 0.0

        for route in route_data["routes"]:
            # Check legs exist
             if not route.get("legs"): continue
             for leg in route["legs"]:
                 # Check steps exist
                 if not leg.get("steps"): continue
                 for step in leg["steps"]:
                     # Ensure necessary keys exist before accessing
                     if "maneuver" not in step or "instruction" not in step["maneuver"] or "distance" not in step:
                         continue

                     instruction = step["maneuver"]["instruction"]
                     distance_m = step["distance"]
                     # Use .get() with a default value for optional keys like 'name'
                     name = step.get("name", "")

                     # Check for road name or highway pattern match
                     # Consider refining highway detection logic based on Mapbox data specifics
                     # E.g., 'rotary', 'roundabout' might be city, 'motorway' refs highway
                     is_highway = False
                     if highway_pattern.search(name) or highway_pattern.search(step.get('ref', '')): # Check 'ref' field too
                         is_highway = True
                     elif 'motorway' in instruction.lower(): # Explicit check for motorway instructions
                         is_highway = True
                     # Add more specific highway checks if needed based on Mapbox response analysis

                     if is_highway:
                         highway_distance_m += distance_m
                     else:
                         city_distance_m += distance_m


        # Conversion factor from meters to miles
        m_to_mi = 0.000621371
        city_distance_mi = city_distance_m * m_to_mi
        highway_distance_mi = highway_distance_m * m_to_mi
        return city_distance_mi, highway_distance_mi

    except requests.exceptions.RequestException as e:
        print(f"Error calculating distances: {e}")
        return 0.0, 0.0
    except (KeyError, ValueError, TypeError) as e:
        # Catch errors during JSON parsing or data access
        print(f"Error processing distance data: {e}")
        return 0.0, 0.0


def get_route_traffic_data(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Tuple[List[Tuple[float, float]], float]:
    """Gets route coordinates and traffic delay using Mapbox Directions API."""
     # Validate coordinates
    if start_coords is None or end_coords is None or start_coords[0] is None or start_coords[1] is None or end_coords[0] is None or end_coords[1] is None:
        print("Error: Invalid coordinates for traffic data.")
        return [], 0.0

    traffic_delay = 0
    coordinates_list = [] # This will store coordinates for weather checks

    params = {
        "access_token": MAPBOX_ACCESS_TOKEN,
        "geometries": "geojson",
        "steps": "true",
        "overview": "full" # Request full overview for potentially better coordinate sampling
         # Add annotations=duration,distance,congestion? Might give more direct traffic info
    }

    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    url = f"{MAPBOX_DIRECTIONS_API_URL}{start_lon},{start_lat};{end_lon},{end_lat}"


    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("routes") or not data["routes"][0].get("geometry") or not data["routes"][0]["geometry"].get("coordinates"):
             print("Error: Route geometry not found in Mapbox response.")
             return [], 0.0

        # --- Coordinate Sampling Logic (Revised) ---
        # Get all coordinates from the main route geometry
        all_coords = data["routes"][0]["geometry"]["coordinates"]
        if not all_coords:
             return [], 0.0 # No coordinates to sample

        num_coords = len(all_coords)
        # Aim for around 10-20 points for weather checks, adjust as needed
        target_points = 15
        step = max(1, num_coords // target_points) # Ensure step is at least 1

        # Sample coordinates reasonably evenly, including start and end
        sampled_indices = list(range(0, num_coords, step))
        if num_coords - 1 not in sampled_indices: # Ensure the last point is included
            sampled_indices.append(num_coords - 1)

        # Extract sampled coordinates (Mapbox returns lon, lat) -> swap to lat, lon
        coordinates_list = [(coord[1], coord[0]) for i, coord in enumerate(all_coords) if i in sampled_indices]

        # --- Traffic Delay Calculation ---
        # Use duration_typical vs duration if available (requires annotations=duration)
        # If not available, this calculation might remain 0 or need alternative logic
        duration_typical = data['routes'][0].get('duration_typical')
        actual_duration = data['routes'][0].get('duration')

        # Calculate traffic delay in minutes
        if duration_typical is not None and actual_duration is not None:
            # Ensure positive delay, typical might be lower if traffic is unusually light
            traffic_delay = max(0, actual_duration - duration_typical) / 60
        else:
            traffic_delay = 0 # Default value if duration data is missing


        return coordinates_list, traffic_delay

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving route traffic data: {e}")
        return [], 0.0
    except (KeyError, ValueError, IndexError, TypeError) as e:
        print(f"Error processing route traffic data: {e}")
        return [], 0.0

def get_weather_data(api_key: str, coordinates_list: List[Tuple[float, float]], target_date: str) -> Tuple[float, str, str]:
    """Gets forecast weather data for a list of coordinates on a target date."""
     # Validate inputs
    if not api_key or not coordinates_list or not target_date:
        print("Error: Missing API key, coordinates, or target date for weather data.")
        return 0.0, "Low", "Low" # Return default values

    temperature_sum = 0
    snow_sum = 0
    rain_sum = 0
    visibility_sum = 0
    valid_coordinates = 0

    # Attempt to parse the target date once
    try:
        target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid target date format: {target_date}. Use YYYY-MM-DD.")
        return 0.0, "Low", "Low"

    for lat, lon in coordinates_list:
        # Validate individual coordinate pair
        if lat is None or lon is None:
             print("Warning: Skipping invalid coordinate pair (None) for weather check.")
             continue

        params = {
            "key": api_key,
             # WeatherAPI expects "lat,lon"
            "q": f"{lat},{lon}",
             # Request only necessary days if target_date logic is robust
             # Or request 'future.json' endpoint for a specific date? Check WeatherAPI docs.
            "days": 4, # Check if requesting fewer days is possible/better
            "aqi": "no",
            "alerts": "no"
        }

        try:
            response = requests.get(WEATHER_API_URL, params=params)
            # Consider adding timeout to requests.get(..., timeout=10)
            response.raise_for_status()
            weather_data = response.json()

            # Check for forecast data existence
            if not weather_data.get('forecast', {}).get('forecastday'):
                print(f"Warning: No forecast data found for {lat}, {lon}")
                continue

            forecast_days = weather_data['forecast']['forecastday']

            found_date = False
            for day in forecast_days:
                 # Check date string exists and parse it
                 date_str = day.get('date')
                 if not date_str: continue
                 try:
                     date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                 except ValueError:
                     continue # Skip if date format is incorrect

                 if date_obj == target_date_obj:
                     day_data = day.get('day', {})
                     if not day_data: continue # Skip if 'day' data is missing

                     # Use .get with default 0.0 for numerical fields
                     temperature = day_data.get('avgtemp_c', 0.0)
                     # WeatherAPI uses 'totalsnow_cm'. Convert cm to mm if needed, or adjust categories.
                     # Let's keep it in cm for now and assume categories handle it.
                     snow_cm = day_data.get('totalsnow_cm', 0.0)
                     # WeatherAPI 'precip_mm' is total for the day in 'day' object
                     rain_mm = day_data.get('totalprecip_mm', 0.0)
                     visibility = day_data.get('avgvis_km', 0.0)

                     # Ensure values are numeric before summing
                     if isinstance(temperature, (int, float)): temperature_sum += temperature
                     if isinstance(snow_cm, (int, float)): snow_sum += snow_cm # Summing cm
                     if isinstance(rain_mm, (int, float)): rain_sum += rain_mm
                     if isinstance(visibility, (int, float)): visibility_sum += visibility

                     valid_coordinates += 1
                     found_date = True
                     break # Exit the inner loop after finding the target date

            # if not found_date:
            #      print(f"Warning: Target date {target_date} not found in forecast for {lat}, {lon}")


        except requests.exceptions.RequestException as e:
            # Log specific API request errors
            print(f"Error retrieving weather data for {lat}, {lon}: {e}")
            continue # Skip to the next coordinate
        except (KeyError, ValueError, TypeError) as e:
            # Log errors during data processing for a specific coordinate
            print(f"Error processing weather data for {lat}, {lon}: {e}")
            continue


    if valid_coordinates > 0:
        average_temperature = temperature_sum / valid_coordinates
        average_snow_cm = snow_sum / valid_coordinates # Average is in cm
        average_rain_mm = rain_sum / valid_coordinates
        average_visibility = visibility_sum / valid_coordinates
    else:
        # No valid data collected, return defaults
        print("Warning: No valid weather data collected for any coordinate.")
        return 0.0, "Low", "Low"


    # Pass average snow (in cm) and visibility to categorization functions
    snow_classification = categorize_snow_level(average_snow_cm, average_visibility)
    rain_classification = categorize_rain_level(average_rain_mm)

    return average_temperature, snow_classification, rain_classification

# --- Helper functions for get_weather_data ---

def categorize_snow_level(snow_cm: float, visibility: float) -> str:
    """Categorizes snow level based on average cm and visibility in km."""
    # Categories adjusted slightly for cm input, assuming visibility affects impact
    # These thresholds might need tuning based on real-world impact
    if snow_cm <= 0.1: # Trace or no snow
        return "Low"
    elif snow_cm <= 2.5: # Light snow (up to ~1 inch)
        # Visibility check for light snow impact
        if visibility >= 1.0: return "Low" # Good visibility
        else: return "Medium" # Reduced visibility even with light snow
    elif 2.5 < snow_cm <= 10: # Moderate snow (~1-4 inches)
        # Visibility crucial here
        if visibility >= 1.0: return "Medium"
        elif 0.5 <= visibility < 1.0: return "Medium" # Still medium impact overall
        else: return "Heavy" # Poor visibility makes moderate snow heavy impact
    else: # Heavy snow (> 10cm / 4 inches)
        return "Heavy"

def categorize_rain_level(rain_mm: float) -> str:
    """Categorizes rain level based on average mm."""
    # Standard definitions (approximate):
    # Light: <= 2.5 mm/hr
    # Moderate: 2.6 to 7.6 mm/hr
    # Heavy: > 7.6 mm/hr
    # Since input is daily total, thresholds are higher. These are indicative.
    if rain_mm <= 0.1: # Trace or no rain
        return "Low"
    elif rain_mm <= 5.0: # Generally light rain over the day
        return "Low"
    elif 5.0 < rain_mm <= 15.0: # Moderate amount, could imply periods of moderate/heavy rain
        return "Medium"
    else: # Significant rainfall total
        return "Heavy"


# --- Removed Code ---
# Removed: Flask imports, Blueprint, model loading, fuel price logic (duplicated in api),
# encodings (duplicated in api), hydrogen route, main route (web UI),
# convert_time_to_window (duplicated in api), plot generation, CSV saving.