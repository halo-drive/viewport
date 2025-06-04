import requests
import re
from typing import Tuple, List
from datetime import datetime
from config import Config
from requests.exceptions import HTTPError, RequestException

GEOCODING_API_URL = "https://geocode.maps.co/search"
MAPBOX_DIRECTIONS_API_URL = "https://api.mapbox.com/directions/v5/mapbox/driving-traffic/"
WEATHER_API_URL = "http://api.weatherapi.com/v1/forecast.json"

MAPBOX_ACCESS_TOKEN = Config.MAPBOX_TOKEN
geocoding_api = Config.GEOCODING_API_KEY


def get_coordinates(place_name: str) -> Tuple[float, float]:
    params = {
        "q": f"{place_name}",
        "api_key": geocoding_api
    }
    try:
        response = requests.get(GEOCODING_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if not data:
             print(f"Error: No data received from geocoding API for {place_name}")
             return None, None
        if isinstance(data, list) and data:
             max_importance_place = max(data, key=lambda place: place.get('importance', 0))
             coords = (float(max_importance_place['lat']), float(max_importance_place['lon']))
             return coords
        else:
             print(f"Error: Unexpected data format from geocoding API for {place_name}")
             return None, None
    except HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 429:
            raise
        else:
            print(f"Error retrieving coordinates (HTTPError): {http_err}")
            return None, None
    except RequestException as e:
        print(f"Error retrieving coordinates (RequestException): {e}")
        return None, None
    except (KeyError, ValueError, TypeError) as e:
        print(f"Error processing coordinate data for {place_name}: {e}")
        return None, None


def calculate_distances(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Tuple[float, float]:
    if start_coords is None or end_coords is None or start_coords[0] is None or start_coords[1] is None or end_coords[0] is None or end_coords[1] is None:
        print("Error: Invalid start or end coordinates provided for distance calculation.")
        return 0.0, 0.0

    city_distance_m = 0
    highway_distance_m = 0
    highway_pattern = re.compile(r'\b[ABM]\d+\b', re.IGNORECASE)

    params = {
        "access_token": MAPBOX_ACCESS_TOKEN,
        "alternatives": "false",
        "geometries": "geojson",
        "language": "en",
        "overview": "simplified",
        "steps": "true",
        "notifications": "none",
    }

    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    url = f"{MAPBOX_DIRECTIONS_API_URL}{start_lon},{start_lat};{end_lon},{end_lat}"

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        route_data = response.json()

        if not route_data.get("routes"):
             print("Error: No routes found between the specified coordinates.")
             return 0.0, 0.0

        for route in route_data["routes"]:
             if not route.get("legs"): continue
             for leg in route["legs"]:
                 if not leg.get("steps"): continue
                 for step in leg["steps"]:
                     if "maneuver" not in step or "instruction" not in step["maneuver"] or "distance" not in step:
                         continue

                     instruction = step["maneuver"]["instruction"]
                     distance_m = step["distance"]
                     name = step.get("name", "")

                     is_highway = False
                     if highway_pattern.search(name) or highway_pattern.search(step.get('ref', '')):
                         is_highway = True
                     elif 'motorway' in instruction.lower():
                         is_highway = True
                     if is_highway:
                         highway_distance_m += distance_m
                     else:
                         city_distance_m += distance_m

        m_to_mi = 0.000621371
        city_distance_mi = city_distance_m * m_to_mi
        highway_distance_mi = highway_distance_m * m_to_mi
        return city_distance_mi, highway_distance_mi
    except HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 429:
            raise
        else:
            print(f"Error calculating distances (HTTPError): {http_err}")
            return 0.0, 0.0
    except RequestException as e:
        print(f"Error calculating distances (RequestException): {e}")
        return 0.0, 0.0
    except (KeyError, ValueError, TypeError) as e:
        print(f"Error processing distance data: {e}")
        return 0.0, 0.0


def get_route_traffic_data(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Tuple[List[Tuple[float, float]], float]:
    if start_coords is None or end_coords is None or start_coords[0] is None or start_coords[1] is None or end_coords[0] is None or end_coords[1] is None:
        print("Error: Invalid coordinates for traffic data.")
        return [], 0.0

    traffic_delay = 0
    coordinates_list = []

    params = {
        "access_token": MAPBOX_ACCESS_TOKEN,
        "geometries": "geojson",
        "steps": "true",
        "overview": "full"
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

        all_coords = data["routes"][0]["geometry"]["coordinates"]
        if not all_coords:
             return [], 0.0
        num_coords = len(all_coords)
        target_points = 15
        step = max(1, num_coords // target_points)

        sampled_indices = list(range(0, num_coords, step))
        if num_coords - 1 not in sampled_indices:
            sampled_indices.append(num_coords - 1)

        coordinates_list = [(coord[1], coord[0]) for i, coord in enumerate(all_coords) if i in sampled_indices]

        duration_typical = data['routes'][0].get('duration_typical')
        actual_duration = data['routes'][0].get('duration')

        if duration_typical is not None and actual_duration is not None:
            traffic_delay = max(0, actual_duration - duration_typical) / 60
        else:
            traffic_delay = 0

        return coordinates_list, traffic_delay
    except HTTPError as http_err:
        if http_err.response is not None and http_err.response.status_code == 429:
            raise
        else:
            print(f"Error retrieving route traffic data (HTTPError): {http_err}")
            return [], 0.0
    except RequestException as e:
        print(f"Error retrieving route traffic data (RequestException): {e}")
        return [], 0.0
    except (KeyError, ValueError, IndexError, TypeError) as e:
        print(f"Error processing route traffic data: {e}")
        return [], 0.0

def get_weather_data(api_key: str, coordinates_list: List[Tuple[float, float]], target_date: str) -> Tuple[float, str, str]:
    if not api_key or not coordinates_list or not target_date:
        print("Error: Missing API key, coordinates, or target date for weather data.")
        return 0.0, "Low", "Low"
    temperature_sum = 0
    snow_sum = 0
    rain_sum = 0
    visibility_sum = 0
    valid_coordinates = 0

    try:
        target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid target date format: {target_date}. Use YYYY-MM-DD.")
        return 0.0, "Low", "Low"

    for lat, lon in coordinates_list:
        if lat is None or lon is None:
             print("Warning: Skipping invalid coordinate pair (None) for weather check.")
             continue

        params = {
            "key": api_key,
            "q": f"{lat},{lon}",
            "days": 4,
            "aqi": "no",
            "alerts": "no"
        }

        try:
            response = requests.get(WEATHER_API_URL, params=params)
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
                 except ValueError:
                     continue

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
        except HTTPError as http_err:
            if http_err.response is not None and http_err.response.status_code == 429:
                raise
            else:
                print(f"Error retrieving weather data for {lat}, {lon} (HTTPError): {http_err}")
                continue
        except RequestException as e:
            print(f"Error retrieving weather data for {lat}, {lon} (RequestException): {e}")
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
    if snow_cm <= 0.1:
        return "Low"
    elif snow_cm <= 2.5:
        if visibility >= 1.0: return "Low"
        else: return "Medium"
    elif 2.5 < snow_cm <= 10:
        if visibility >= 1.0: return "Medium"
        elif 0.5 <= visibility < 1.0: return "Medium"
        else: return "Heavy"
    else:
        return "Heavy"

def categorize_rain_level(rain_mm: float) -> str:
    if rain_mm <= 0.1:
        return "Low"
    elif rain_mm <= 5.0:
        return "Low"
    elif 5.0 < rain_mm <= 15.0:
        return "Medium"
    else:
        return "Heavy"