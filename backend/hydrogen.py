# hydrogen.py - Modified to act as a utility module for hydrogen_api.py

# Keep necessary imports for the functions used by hydrogen_api.py
from typing import Tuple, List
import requests
import re
from geopy.distance import geodesic
import joblib
import time
from datetime import datetime
import pandas as pd
import numpy as np
# Removed: Flask imports, matplotlib, os, json, hydrogen_here_map

from config import Config

# Keep Constants needed by functions below
GEOCODING_API_URL = "https://geocode.maps.co/search"
MAPBOX_DIRECTIONS_API_URL = "https://api.mapbox.com/directions/v5/mapbox/driving-traffic/"
MAPBOX_GEOCODING_API_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/"
WEATHER_API_URL = "http://api.weatherapi.com/v1/forecast.json" # Note: space at end removed
DATE_FORMAT = "%Y-%m-%d" # Keep if used internally, otherwise might remove

# Keep API Keys needed by functions below
# mapbox_token is defined locally as it's used directly in functions here
mapbox_token = Config.MAPBOX_TOKEN # Assuming Config has MAPBOX_TOKEN
weather_api_key = Config.WEATHER_API_KEY
geocoding_api = Config.GEOCODING_API_KEY

# Keep Model loading as it's part of the analysis logic eventually needed
# Although hydrogen_api.py loads it too, keeping it here doesn't break anything
# and reflects that this module contains the core logic associated with the model.
# If strict deduplication is desired later, this could be removed and only loaded in the API.
model = joblib.load('Hydrogen_model.pkl')

# --- Keep Functions Used by hydrogen_api.py ---

def get_coordinates(place_name: str) -> Tuple[float, float]:
    """Gets coordinates using Geocode.maps.co API."""
    start_time = time.time()
    params = {
        "q": f"{place_name}",
        "api_key": geocoding_api
    }
    try:
        response = requests.get(GEOCODING_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if not data:
             print(f"Warning: No data received from geocoding API for {place_name}")
             return None, None
        if isinstance(data, list) and data:
             max_importance_place = max(data, key=lambda place: place.get('importance', 0))
             coords = (float(max_importance_place['lat']), float(max_importance_place['lon']))
             return coords
        else:
             print(f"Warning: Unexpected data format from geocoding API for {place_name}")
             return None, None
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving coordinates: {e}")
        return None, None
    except (KeyError, ValueError, TypeError) as e:
        print(f"Error processing coordinate data for {place_name}: {e}")
        return None, None


def get_traffic_data(origin_coordinates, destination_coordinates, fuelstation_coordinates, mapbox_token):
    """Gets traffic congestion level using Mapbox Directions API."""
    # Add input validation
    if not all([origin_coordinates, destination_coordinates, fuelstation_coordinates, mapbox_token]):
         print("Warning: Missing input for get_traffic_data")
         return "Low" # Return default or raise error
    if None in origin_coordinates or None in destination_coordinates or None in fuelstation_coordinates:
         print("Warning: None coordinate found in get_traffic_data input")
         return "Low" # Return default

    try:
        start_time = time.time()
        url = f"{MAPBOX_DIRECTIONS_API_URL}{origin_coordinates[1]},{origin_coordinates[0]};{fuelstation_coordinates[1]},{fuelstation_coordinates[0]};{destination_coordinates[1]},{destination_coordinates[0]}?annotations=congestion_numeric&overview=full&waypoints=0;2&access_token={mapbox_token}"
        response = requests.get(url)
        response.raise_for_status() # Check for HTTP errors
        data = response.json()

        # Safer data access
        routes = data.get("routes", [])
        if not routes: return "Low"
        legs = routes[0].get("legs", [])
        if not legs: return "Low"
        # Assuming first leg, first segment annotation needed. Adjust if logic differs.
        annotation = legs[0].get("annotation", {})
        congestion_numeric = annotation.get("congestion_numeric", [])

        valid_congestion_values = [value for value in congestion_numeric if isinstance(value, (int, float))] # Ensure numeric
        if not valid_congestion_values:
             average_congestion = 0 # Default if no valid data
        else:
            average_congestion = sum(valid_congestion_values) / len(valid_congestion_values)

        end_time = time.time()
        if average_congestion >= 0 and average_congestion < 40:
            return "Low"
        elif average_congestion >= 40 and average_congestion < 60:
            return "Medium"
        else:
            return "Heavy"
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving traffic data: {e}")
        return "Low" # Default on error
    except (IndexError, KeyError, TypeError, ZeroDivisionError) as e:
         print(f"Error processing traffic data: {e}")
         return "Low" # Default on processing error

def find_nearest_station(given_location, station_postal_codes, mapbox_token):
    """Finds nearest station from a list of postal codes using Mapbox Geocoding."""
    # Add input validation
    if not all([given_location, station_postal_codes, mapbox_token]):
        print("Warning: Missing input for find_nearest_station")
        return None

    start_time = time.time()
    given_location_url = f'{MAPBOX_GEOCODING_API_URL}{given_location}.json?access_token={mapbox_token}'
    try:
        given_location_response = requests.get(given_location_url)
        given_location_response.raise_for_status()
        given_location_data = given_location_response.json()
        # Safer access to features
        features = given_location_data.get('features', [])
        if not features:
            print(f"Warning: No features found for given location {given_location}")
            return None
        given_location_coords = features[0].get('geometry', {}).get('coordinates')
        if not given_location_coords or len(given_location_coords) < 2:
             print(f"Warning: Could not extract coordinates for {given_location}")
             return None

        nearest_station = None
        min_distance = float('inf')

        for postal_code in station_postal_codes:
            postal_code_url = f'{MAPBOX_GEOCODING_API_URL}{postal_code}.json?access_token={mapbox_token}'
            try:
                postal_code_response = requests.get(postal_code_url)
                postal_code_response.raise_for_status()
                postal_code_data = postal_code_response.json()
                pc_features = postal_code_data.get('features', [])
                if not pc_features:
                    print(f"Warning: No features found for postal code {postal_code}")
                    continue # Skip this postal code
                postal_code_coords = pc_features[0].get('geometry', {}).get('coordinates')
                if not postal_code_coords or len(postal_code_coords) < 2:
                     print(f"Warning: Could not extract coordinates for {postal_code}")
                     continue

                # Simple Euclidean distance (note: inaccurate for large distances, but kept as per instruction)
                # Mapbox returns [lon, lat]
                distance = ((given_location_coords[0] - postal_code_coords[0]) ** 2 + (given_location_coords[1] - postal_code_coords[1]) ** 2) ** 0.5

                if distance < min_distance:
                    min_distance = distance
                    nearest_station = postal_code
            except requests.exceptions.RequestException as e:
                 print(f"Error geocoding postal code {postal_code}: {e}")
                 continue # Skip this postal code on error
            except (IndexError, KeyError, TypeError) as e:
                 print(f"Error processing postal code data {postal_code}: {e}")
                 continue


        end_time = time.time()
        return nearest_station
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving coordinates for given location {given_location}: {e}")
        return None
    except (IndexError, KeyError, TypeError) as e:
         print(f"Error processing given location data {given_location}: {e}")
         return None

def calculate_distances(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Tuple[float, float]:
    """Calculates city/highway distances using Mapbox Directions API."""
    # This function is identical to the one kept in the modified tracking.py
    # Ideally, it should live in a shared utility file. Keeping it here for now.
    # Check for valid coordinates
    if start_coords is None or end_coords is None or start_coords[0] is None or start_coords[1] is None or end_coords[0] is None or end_coords[1] is None:
        print("Error: Invalid start or end coordinates provided for distance calculation.")
        return 0.0, 0.0

    start_time = time.time()
    city_distance_m = 0
    highway_distance_m = 0
     # Corrected Regex: Uses raw string r'' and matches A, B, or M followed by digits
    # Matches common UK road classifications (e.g., M1, A40, B123)
    highway_pattern = re.compile(r'\b[ABM]\d+\b', re.IGNORECASE)


    params = {
        "access_token": mapbox_token,
        "alternatives": "false",
        "geometries": "geojson",
        "language": "en",
        "overview": "simplified", # Consider 'full' for more detail if needed
        "steps": "true",
        "notifications": "none",
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
                     is_highway = False
                     if highway_pattern.search(name) or highway_pattern.search(step.get('ref', '')): # Check 'ref' field too
                         is_highway = True
                     elif 'motorway' in instruction.lower(): # Explicit check for motorway instructions
                         is_highway = True

                     if is_highway:
                         highway_distance_m += distance_m
                     else:
                         city_distance_m += distance_m

        # Conversion factor from meters to miles
        m_to_mi = 0.000621371
        city_distance_mi = city_distance_m * m_to_mi
        highway_distance_mi = highway_distance_m * m_to_mi
        end_time = time.time()
        return city_distance_mi, highway_distance_mi

    except requests.exceptions.RequestException as e:
        print(f"Error calculating distances: {e}")
        return 0.0, 0.0
    except (KeyError, ValueError, TypeError) as e:
        # Catch errors during JSON parsing or data access
        print(f"Error processing distance data: {e}")
        return 0.0, 0.0


def get_route_coordinates(start_coords, end_coords, steps=50):
    """Gets sampled coordinates along a route using Mapbox Directions API."""
    # This function is identical to the revised one potentially in modified tracking.py
    # Validate coordinates
    if start_coords is None or end_coords is None or start_coords[0] is None or start_coords[1] is None or end_coords[0] is None or end_coords[1] is None:
        print("Error: Invalid coordinates for route coordinate sampling.")
        return []

    start_time = time.time()
    params = {
        "access_token": mapbox_token,
        "geometries": "geojson",
        "steps": "true", # Keep steps=true if original logic relied on it, otherwise overview=full might be enough
        "overview": "full" # Get full geometry for better sampling
    }

    try:
        url = f"{MAPBOX_DIRECTIONS_API_URL}{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("routes") or not data["routes"][0].get("geometry") or not data["routes"][0]["geometry"].get("coordinates"):
             print("Error: Route geometry not found in Mapbox response for coordinate sampling.")
             return []

        # --- Coordinate Sampling Logic (Same as potential revised tracking.py) ---
        all_coords = data["routes"][0]["geometry"]["coordinates"]
        if not all_coords: return []

        num_coords = len(all_coords)
        target_points = steps # Use the 'steps' parameter as the target number of points
        step_interval = max(1, num_coords // target_points)

        sampled_indices = list(range(0, num_coords, step_interval))
        if num_coords - 1 not in sampled_indices:
            sampled_indices.append(num_coords - 1)

        # Mapbox returns [lon, lat] -> swap to [lat, lon] for consistency if needed elsewhere
        # Keeping as [lon, lat] as returned by API for now, assuming caller handles it.
        # If consistency needed, swap here: route_coordinates = [(coord[1], coord[0]) ... ]
        route_coordinates = [all_coords[i] for i in sampled_indices]

        end_time = time.time()
        return route_coordinates

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving route coordinates : {e}")
        return []
    except (KeyError, ValueError, IndexError, TypeError) as e:
         print(f"Error processing route coordinate data: {e}")
         return []

def get_weather_data(api_key: str, coordinates_list: List[Tuple[float, float]], target_date: str) -> Tuple[float, str, str]:
    """Gets forecast weather data for a list of coordinates on a target date."""
    # This function is identical to the one kept in the modified tracking.py
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

    # Coordinates from get_route_coordinates might be [lon, lat], WeatherAPI needs "lat,lon"
    for coord_pair in coordinates_list:
         if coord_pair is None or len(coord_pair) < 2:
             print("Warning: Skipping invalid coordinate pair (None or <2 elements) for weather check.")
             continue
         # Assuming input is [lon, lat] based on common geojson/mapbox format
         lon, lat = coord_pair[0], coord_pair[1]
         # If input was [lat, lon], swap the above line

         params = {
            "key": api_key,
            "q": f"{lat},{lon}", # WeatherAPI expects "lat,lon"
            "days": 4,
            "aqi": "no",
            "alerts": "no"
         }

         try:
            response = requests.get(WEATHER_API_URL.strip(), params=params) # Added strip() to URL
            response.raise_for_status()
            weather_data = response.json()

            if not weather_data.get('forecast', {}).get('forecastday'):
                print(f"Warning: No forecast data found for {lat}, {lon}")
                continue

            forecast_days = weather_data['forecast']['forecastday']
            found_date = False
            for day in forecast_days:
                 date_str = day.get('date')
                 if not date_str: continue
                 try:
                     date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                 except ValueError: continue

                 if date_obj == target_date_obj:
                     day_data = day.get('day', {})
                     if not day_data: continue

                     temperature = day_data.get('avgtemp_c', 0.0)
                     snow_cm = day_data.get('totalsnow_cm', 0.0)
                     rain_mm = day_data.get('totalprecip_mm', 0.0)
                     visibility = day_data.get('avgvis_km', 0.0)

                     if isinstance(temperature, (int, float)): temperature_sum += temperature
                     if isinstance(snow_cm, (int, float)): snow_sum += snow_cm
                     if isinstance(rain_mm, (int, float)): rain_sum += rain_mm
                     if isinstance(visibility, (int, float)): visibility_sum += visibility

                     valid_coordinates += 1
                     found_date = True
                     break
         except requests.exceptions.RequestException as e:
            print(f"Error retrieving weather data for {lat}, {lon}: {e}")
            continue
         except (KeyError, ValueError, TypeError) as e:
            print(f"Error processing weather data for {lat}, {lon}: {e}")
            continue

    if valid_coordinates > 0:
        average_temperature = temperature_sum / valid_coordinates
        average_snow_cm = snow_sum / valid_coordinates
        average_rain_mm = rain_sum / valid_coordinates
        average_visibility = visibility_sum / valid_coordinates
    else:
        print("Warning: No valid weather data collected for any coordinate.")
        return 0.0, "Low", "Low"

    snow_classification = categorize_snow_level(average_snow_cm, average_visibility)
    rain_classification = categorize_rain_level(average_rain_mm)

    return average_temperature, snow_classification, rain_classification


def categorize_snow_level(snow_cm: float, visibility: float) -> str:
    """Categorizes snow level based on average cm and visibility in km."""
    # This function is identical to the one potentially in modified tracking.py
    if snow_cm <= 0.1: return "Low"
    elif snow_cm <= 2.5:
        if visibility >= 1.0: return "Low"
        else: return "Medium"
    elif 2.5 < snow_cm <= 10:
        if visibility >= 1.0: return "Medium"
        elif 0.5 <= visibility < 1.0: return "Medium"
        else: return "Heavy"
    else: return "Heavy"

def categorize_rain_level(rain_mm: float) -> str:
    """Categorizes rain level based on average mm."""
    # This function is identical to the one potentially in modified tracking.py
    if rain_mm <= 0.1: return "Low"
    elif rain_mm <= 5.0: return "Low"
    elif 5.0 < rain_mm <= 15.0: return "Medium"
    else: return "Heavy"

# --- Keep Encodings used by get_raw_input ---
vehicle_type_encoded = ['HVS HGV', 'HVS MCV', 'Hymax Series']
origin_encoded = {'Aberdeen': 0, 'Birmingham': 1, 'Cardiff': 2, 'Glasgow': 3,
                  'Leeds': 4, 'Liverpool': 5, 'London': 6, 'Manchester': 7}
nearest_station_encoded = {'AB12 3SH': 0, 'B25 8DW': 1, 'S60 5WG': 2, 'SN3 4QS': 3, 'TW6 2GE': 4}
dispatch_encoded = {'morning': 0, 'night': 1, 'noon': 2}
traffic_congestion_encoded = {'low': 0, 'medium': 1, 'high': 2}
rain_encoded = {'low': 0, 'medium': 1, 'high': 2}
snow_encoded = {'low': 0, 'medium': 1, 'high': 2}


# --- Keep get_raw_input function used by hydrogen_api.py ---
def get_raw_input(Origin_depot, Destination_depot, nearest_fuel_station, total_highway_distance,
                  total_city_distance, traffic_congestion_level, average_temperature, rain_classification,
                  snow_classification, pallets, Vehicle_age, Goods_weight, Avg_Speed_mph, dispatch_time, vehicle_type,
                  vehicle_range, Tank_capacity, total_payload):
    """Prepares the input DataFrame for the Hydrogen prediction model."""
    start_time = time.time() # Keep time if needed, otherwise remove

    # Print statements for debugging (can be removed if not needed)
    # print(f"Avg_Temp: {average_temperature:.2f}")
    # print(f"Avg_Precipitation:", rain_classification)
    # print(f"Avg_snow:", snow_classification)
    # print(f"Distance_highway: {total_highway_distance:.2f}")
    # print(f"Distance_city: {total_city_distance:.2f}")
    # print(f"Avg_traffic_congestion:", traffic_congestion_level)
    # print(f"Nearest fuel station:", nearest_fuel_station)
    # print("Tank capacity of vehicle(kg):", Tank_capacity)

    # Encode categorical variables using global dicts defined above
    encoded_origin = origin_encoded.get(Origin_depot, -1) # Use -1 or other indicator for unknown
    encoded_destination = origin_encoded.get(Destination_depot, -1)
    encoded_dispatch_time = dispatch_encoded.get(dispatch_time, -1)
    encoded_nearest_station = nearest_station_encoded.get(nearest_fuel_station, -1)
    # Ensure keys are lowercase for lookup if needed
    encoded_avg_traffic_congestion = traffic_congestion_encoded.get(traffic_congestion_level.lower() if isinstance(traffic_congestion_level, str) else traffic_congestion_level, -1)
    encoded_avg_rain = rain_encoded.get(rain_classification.lower() if isinstance(rain_classification, str) else rain_classification, -1)
    encoded_avg_snow = snow_encoded.get(snow_classification.lower() if isinstance(snow_classification, str) else snow_classification, -1)

    dummy_variables = {vehicle: (1 if vehicle == vehicle_type else 0) for vehicle in vehicle_type_encoded}

    # Recalculate/override values as done in the original function
    Goods_weight = pallets * 0.88
    Avg_Speed_mph = 65 # Overrides passed Avg_Speed_mph

    input_data = {
        "Vehicle_age": [Vehicle_age],
        "Goods_weight": [Goods_weight],
        "Avg_traffic_congestion": [encoded_avg_traffic_congestion],
        "Avg_temp": [average_temperature],
        "Avg_Precipitation": [encoded_avg_rain],
        "Avg_snow": [encoded_avg_snow],
        "Origin_depot": [encoded_origin],
        "Destination_depot": [encoded_destination],
        "Avg_Speed_mph": [Avg_Speed_mph], # Uses the overridden value
        "Distance_highway": [total_highway_distance],
        "Distance_city": [total_city_distance],
        "dispatch_time": [encoded_dispatch_time],
        "total_payload": [total_payload],
        "tank_capacity": [Tank_capacity],
        "range": [vehicle_range],
        "Closest_station": [encoded_nearest_station],
        "Total_distance_miles": [total_city_distance + total_highway_distance]
    }

    input_data.update(dummy_variables) # Add one-hot encoded vehicle types
    end_time = time.time() # Keep time if needed

    # Ensure columns match the model's training order if necessary
    # Example: feature_order = ['Vehicle_age', 'Goods_weight', ...]
    # return pd.DataFrame(input_data, columns=feature_order)
    return pd.DataFrame(input_data)


# --- Removed Code ---
# Removed: find_vehicle_type_range_and_capacity (used input())
# Removed: convert_time_to_window (defined in hydrogen_api.py)
# Removed: hydrogen_bp Blueprint definition
# Removed: hydrogenanalytics Flask route (@hydrogen_bp.route)
# Removed: Plotting logic, CSV saving, call to getdatah inside the old route