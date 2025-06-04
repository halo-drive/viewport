import folium
import requests
from geopy.distance import geodesic
from typing import Tuple, List, Optional 
from collections import namedtuple
from config import Config

FORMAT_VERSION = 1

DECODING_TABLE = [
    62, -1, -1, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, -1, -1, -1, -1, -1, -1, -1,
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
    22, 23, 24, 25, -1, -1, -1, -1, 63, -1, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
    36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51
]

api_key = Config.HERE_API_KEY

PolylineHeader = namedtuple('PolylineHeader', 'precision,third_dim,third_dim_precision')

def decode_header(decoder):
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
    char_value = ord(char)
    try:
        value = DECODING_TABLE[char_value - 45]
    except IndexError:
        raise ValueError('Invalid encoding')
    if value < 0:
        raise ValueError('Invalid encoding')
    return value

def to_signed(value):
    if value & 1:
        value = ~value
    value >>= 1
    return value

def decode_unsigned_values(encoded):
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

def get_here_directions(origin: str, destination: str, api_key: str) -> Optional[List[Tuple[float, float]]]:
    url = f"https://router.hereapi.com/v8/routes?transportMode=car&origin={origin}&destination={destination}&return=polyline&apikey={api_key}"
    try:
        response = requests.get(url, timeout=15) 
        response.raise_for_status()
        data = response.json()
        routes = data.get('routes', [])
        if routes:
            sections = routes[0].get('sections', [])
            if sections:
                polyline_str = sections[0].get('polyline')
                if polyline_str:
                     decoded_route = list(iter_decode(polyline_str))
                     return decoded_route if decoded_route else None 
    except requests.exceptions.RequestException as e:
         print(f"Error fetching HERE directions ({origin} -> {destination}): {e}")
    except (ValueError, KeyError, IndexError) as e:
         print(f"Error processing HERE directions data ({origin} -> {destination}): {e}")
    return None 

def get_coordinates(place_name: str, api_key: str) -> Optional[Tuple[float, float]]:
    url = f"https://geocode.search.hereapi.com/v1/geocode?q={place_name}&apiKey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'items' in data and data['items']:
            location = data['items'][0]['position']
            lat = float(location.get('lat'))
            lng = float(location.get('lng'))
            return lat, lng
    except requests.exceptions.RequestException as e:
         print(f"Error geocoding '{place_name}' with HERE: {e}")
    except (ValueError, KeyError, IndexError, TypeError) as e:
         print(f"Error processing HERE geocoding data for '{place_name}': {e}")
    return None 

def get_fuel_station_coordinates(coords: Tuple[float, float], api_key: str) -> Optional[Tuple[float, float]]:
    base_url = 'https://discover.search.hereapi.com/v1/discover'
    params = {
        'q': 'fuel station',
        'apiKey': api_key,
        'at': f'{coords[0]},{coords[1]}',
        'limit': 5
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        fuel_stations = response.json()
        if 'items' in fuel_stations and fuel_stations['items']:
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
    return None 


def get_route_with_fuel_stations(
    api_key: str,
    origin_coords: Tuple[float, float],
    destination_coords: Tuple[float, float] 
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]]:
    print(f"Calculating route/stations from {origin_coords} to {destination_coords}")

    origin_coords_str = f"{origin_coords[0]},{origin_coords[1]}"
    destination_coords_str = f"{destination_coords[0]},{destination_coords[1]}"

    route_points = get_here_directions(origin_coords_str, destination_coords_str, api_key)

    if not route_points:
        raise ValueError("Unable to retrieve initial route points from HERE API")

    try:
        total_distance = sum(geodesic(route_points[i], route_points[i+1]).km for i in range(len(route_points) - 1))
    except ValueError: 
        print("Warning: Could not calculate total distance, defaulting to 0.")
        total_distance = 0

    interval_distance = total_distance / 4 if total_distance > 0 else 50 
    fuel_station_coords = []
    original_route_coords_list = list(route_points) 

    cumulative_distance = 0
    for i in range(1, len(route_points)):
        try:
            segment_distance = geodesic(route_points[i-1], route_points[i]).km
            cumulative_distance += segment_distance
        except ValueError: continue 

        if cumulative_distance >= 5:
            fuel_coords = get_fuel_station_coordinates(route_points[i], api_key)
            if fuel_coords:
                fuel_station_coords.append(fuel_coords)
                print(f"Found initial fuel station near {route_points[i]}")
                break

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
                cumulative_distance = 0
                last_fuel_station_index = i 

    return original_route_coords_list, route_points, fuel_station_coords
