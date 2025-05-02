#!/usr/bin/env python
# coding: utf-8

import folium
import requests
from geopy.distance import geodesic
from typing import Tuple, List, Optional # Added Optional
from collections import namedtuple
from config import Config

FORMAT_VERSION = 1

DECODING_TABLE = [
    62, -1, -1, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, -1, -1, -1, -1, -1, -1, -1,
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
    22, 23, 24, 25, -1, -1, -1, -1, 63, -1, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
    36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51
]

# Use HERE API Key from config for consistency
api_key = Config.HERE_API_KEY

PolylineHeader = namedtuple('PolylineHeader', 'precision,third_dim,third_dim_precision')

# --- Polyline Decoding Functions (Unchanged) ---
def decode_header(decoder):
    # (code unchanged)
    version = next(decoder)
    if version != FORMAT_VERSION:
        raise ValueError('Invalid format version')
    value = next(decoder)
    precision = value & 15
    value >>= 4
    third_dim = value & 7
    third_dim_precision = (value >> 3) & 15
    return PolylineHeader(precision, third_dim, third_dim_precision)

def decode_char(char):
    # (code unchanged)
    char_value = ord(char)
    try:
        value = DECODING_TABLE[char_value - 45]
    except IndexError:
        raise ValueError('Invalid encoding')
    if value < 0:
        raise ValueError('Invalid encoding')
    return value

def to_signed(value):
    # (code unchanged)
    if value & 1:
        value = ~value
    value >>= 1
    return value

def decode_unsigned_values(encoded):
    # (code unchanged)
    result = shift = 0
    for char in encoded:
        value = decode_char(char)
        result |= (value & 0x1F) << shift
        if (value & 0x20) == 0:
            yield result
            result = shift = 0
        else:
            shift += 5
    if shift > 0:
        raise ValueError('Invalid encoding')

def iter_decode(encoded):
    # (code unchanged)
    last_lat = last_lng = last_z = 0
    decoder = decode_unsigned_values(encoded)
    header = decode_header(decoder)
    factor_degree = 10.0 ** header.precision
    factor_z = 10.0 ** header.third_dim_precision
    third_dim = header.third_dim
    while True:
        try:
            last_lat += to_signed(next(decoder))
        except StopIteration:
            return
        try:
            last_lng += to_signed(next(decoder))
            if third_dim:
                last_z += to_signed(next(decoder))
                yield (last_lat / factor_degree, last_lng / factor_degree, last_z / factor_z)
            else:
                yield (last_lat / factor_degree, last_lng / factor_degree)
        except StopIteration:
            raise ValueError("Invalid encoding. Premature ending reached")
# --- End Polyline Decoding ---

def get_here_directions(origin: str, destination: str, api_key: str) -> Optional[List[Tuple[float, float]]]:
    """ Gets route polyline between two points ('lat,lon' strings). """
    # Added type hints and return Optional
    url = f"https://router.hereapi.com/v8/routes?transportMode=car&origin={origin}&destination={destination}&return=polyline&apikey={api_key}"
    try:
        response = requests.get(url, timeout=15) # Added timeout
        response.raise_for_status()
        data = response.json()
        routes = data.get('routes', [])
        if routes:
            sections = routes[0].get('sections', [])
            if sections:
                polyline_str = sections[0].get('polyline')
                if polyline_str:
                     decoded_route = list(iter_decode(polyline_str))
                     return decoded_route if decoded_route else None # Return None if decode fails
    except requests.exceptions.RequestException as e:
         print(f"Error fetching HERE directions ({origin} -> {destination}): {e}")
    except (ValueError, KeyError, IndexError) as e:
         print(f"Error processing HERE directions data ({origin} -> {destination}): {e}")
    return None # Return None on any error or if no route found

def get_coordinates(place_name: str, api_key: str) -> Optional[Tuple[float, float]]:
    """ Gets coordinates ('lat,lon') for a place name using HERE Geocoder. """
    # Added return Optional
    url = f"https://geocode.search.hereapi.com/v1/geocode?q={place_name}&apiKey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'items' in data and data['items']:
            location = data['items'][0]['position']
            # Ensure lat and lon are present and floats
            lat = float(location.get('lat'))
            lng = float(location.get('lng'))
            return lat, lng
    except requests.exceptions.RequestException as e:
         print(f"Error geocoding '{place_name}' with HERE: {e}")
    except (ValueError, KeyError, IndexError, TypeError) as e:
         print(f"Error processing HERE geocoding data for '{place_name}': {e}")
    return None # Return None on error or no result

def get_fuel_station_coordinates(coords: Tuple[float, float], api_key: str) -> Optional[Tuple[float, float]]:
    """ Finds coordinates of the nearest fuel station to given coords ('lat,lon') using HERE Discover. """
    # Added return Optional
    base_url = 'https://discover.search.hereapi.com/v1/discover'
    params = {
        'q': 'fuel station',
        'apiKey': api_key,
        'at': f'{coords[0]},{coords[1]}',
        'limit': 5 # Get a few options
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        fuel_stations = response.json()
        if 'items' in fuel_stations and fuel_stations['items']:
            # Find closest station based on distance if available, else take the first
            closest_station = min(fuel_stations['items'], key=lambda x: x.get('distance', float('inf')))
            position = closest_station.get('position')
            if position:
                 lat = float(position.get('lat'))
                 lng = float(position.get('lng'))
                 return lat, lng
    except requests.exceptions.RequestException as e:
         print(f"Error finding HERE fuel stations near {coords}: {e}")
    except (ValueError, KeyError, IndexError, TypeError) as e:
         print(f"Error processing HERE fuel station data near {coords}: {e}")
    return None # Return None on error or no result


# --- MODIFIED FUNCTION ---
def get_route_with_fuel_stations(
    api_key: str,
    origin_coords: Tuple[float, float], # Changed from origin_city
    destination_coords: Tuple[float, float] # Changed from destination_city
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]]:
    """
    Calculates a route polyline and finds fuel stations along it using HERE APIs.
    Accepts origin and destination coordinates directly.

    Returns:
        Tuple containing:
        - Original route coordinates (list of (lat, lon) tuples) - MAY BE LESS USEFUL NOW
        - Final route points potentially including stations (list of (lat, lon) tuples for polyline)
        - Coordinates of found fuel stations (list of (lat, lon) tuples)
    """
    print(f"Calculating route/stations from {origin_coords} to {destination_coords}")

    # Convert coords tuples to 'lat,lon' strings for HERE API calls
    origin_coords_str = f"{origin_coords[0]},{origin_coords[1]}"
    destination_coords_str = f"{destination_coords[0]},{destination_coords[1]}"

    # 1. Get the initial direct route polyline
    route_points = get_here_directions(origin_coords_str, destination_coords_str, api_key)

    if not route_points:
        raise ValueError("Unable to retrieve initial route points from HERE API")

    # --- Station Finding Logic (largely unchanged, but uses route_points) ---
    try:
        total_distance = sum(geodesic(route_points[i], route_points[i+1]).km for i in range(len(route_points) - 1))
    except ValueError: # Handle potential issues with geodesic calculation if points are identical
        print("Warning: Could not calculate total distance, defaulting to 0.")
        total_distance = 0

    interval_distance = total_distance / 4 if total_distance > 0 else 50 # km, fallback interval
    fuel_station_coords = []
    original_route_coords_list = list(route_points) # Keep a copy

    # Get fuel station near origin (e.g., after 5km)
    cumulative_distance = 0
    for i in range(1, len(route_points)):
        try:
            segment_distance = geodesic(route_points[i-1], route_points[i]).km
            cumulative_distance += segment_distance
        except ValueError: continue # Skip if points are identical

        if cumulative_distance >= 5:
            fuel_coords = get_fuel_station_coordinates(route_points[i], api_key)
            if fuel_coords:
                fuel_station_coords.append(fuel_coords)
                print(f"Found initial fuel station near {route_points[i]}")
                break

    # Add stations roughly every quarter distance
    cumulative_distance = 0
    last_fuel_station_index = 0
    for i in range(1, len(route_points)):
        try:
            segment_distance = geodesic(route_points[i-1], route_points[i]).km
            cumulative_distance += segment_distance
        except ValueError: continue

        if cumulative_distance >= interval_distance:
            fuel_coords = get_fuel_station_coordinates(route_points[i], api_key)
            if fuel_coords and fuel_coords not in fuel_station_coords:
                fuel_station_coords.append(fuel_coords)
                print(f"Found mid-route fuel station near {route_points[i]}")
                cumulative_distance = 0 # Reset distance counter
                last_fuel_station_index = i # Track index if needed

    # Get fuel station towards destination (if needed based on remaining distance)
    # Simplified: just add stations based on interval for now
    # You could add more complex logic based on remaining distance vs interval

    # --- End Station Finding ---

    # Limit number of stations if needed (e.g., max 2-3)
    # fuel_station_coords = fuel_station_coords[:3] # Example limit

    # Return original route list, polyline points (which might be the same if no stations added), and station coords
    # The API currently rebuilds the polyline if stations are found.
    # Let's return the original route points, the direct polyline points, and station coords.
    # The API layer (`diesel_api.py`) will decide how to combine them if needed.

    return original_route_coords_list, route_points, fuel_station_coords


# --- display_route_on_map, launch_all, getdata functions are likely unused by API ---
# --- They can be kept for standalone testing or removed if desired ---
# def display_route_on_map(...): ...
# def launch_all(...): ...
# def getdata(...): ...