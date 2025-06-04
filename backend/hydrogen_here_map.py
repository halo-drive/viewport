from geopy.distance import geodesic
import requests
from geopy.geocoders import Nominatim 
from collections import namedtuple
import time 

from config import Config

here_api_key = Config.HERE_API_KEY

FORMAT_VERSION = 1
DECODING_TABLE = [62, -1, -1, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, -1, -1, -1, -1, -1, -1, -1,
                  0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
                  22, 23, 24, 25, -1, -1, -1, -1, 63, -1, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
                  36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

PolylineHeader = namedtuple('PolylineHeader', 'precision,third_dim,third_dim_precision')

def decode_header(decoder):
    try:
        version = next(decoder)
        if version != FORMAT_VERSION:
            raise ValueError('Invalid format version')
        value = next(decoder)
        precision = value & 15
        value >>= 4
        third_dim = value & 7
        third_dim_precision = (value >> 3) & 15
        return PolylineHeader(precision, third_dim, third_dim_precision)
    except StopIteration:
        raise ValueError("Invalid encoding. Empty string or missing header.")


def decode_char(char):
    char_value = ord(char)
    try:
        value = DECODING_TABLE[char_value - 45]
    except IndexError:
        raise ValueError('Invalid encoding character')
    if value < 0:
        raise ValueError('Invalid encoding character')
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
            if shift > 30: 
                 raise ValueError("Invalid encoding. Possible corruption detected.")
    if shift > 0:
        raise ValueError('Invalid encoding. Unfinished sequence.')

def iter_decode(encoded):
    if not encoded: 
         return iter([]) 

    last_lat = last_lng = last_z = 0
    decoder = decode_unsigned_values(encoded)
    try:
        header = decode_header(decoder)
    except ValueError as e: 
         print(f"Error decoding polyline header: {e}")
         return iter([])
    except StopIteration: 
         print("Error decoding polyline: No data after header.")
         return iter([])

    factor_degree = 10.0 ** header.precision
    factor_z = 10.0 ** header.third_dim_precision
    third_dim = header.third_dim
    while True:
        try:
            last_lat += to_signed(next(decoder))
        except StopIteration:
            return 
        except ValueError as e: 
             print(f"Error decoding latitude delta: {e}")
             return iter([])

        try:
            last_lng += to_signed(next(decoder))
            if third_dim:
                try:
                    last_z += to_signed(next(decoder))
                    yield (last_lat / factor_degree, last_lng / factor_degree, last_z / factor_z)
                except StopIteration:
                     print("Error decoding polyline: Premature ending before Z delta.")
                     raise ValueError("Invalid encoding. Premature ending before Z delta.")
            else:
                yield (last_lat / factor_degree, last_lng / factor_degree)
        except StopIteration:
             print("Error decoding polyline: Premature ending after latitude delta.")
             raise ValueError("Invalid encoding. Premature ending reached after latitude delta.")
        except ValueError as e: 
             print(f"Error decoding longitude/z delta: {e}")
             return iter([])


def get_here_directions(origin, destination, api_key):
    if not all([origin, destination, api_key]):
        print("Warning: Missing input for get_here_directions")
        return None
    if origin is None or destination is None or origin[0] is None or origin[1] is None or destination[0] is None or destination[1] is None:
        print("Warning: None coordinate found in get_here_directions input")
        return None

    url = f"https://router.hereapi.com/v8/routes?transportMode=car&origin={origin[0]},{origin[1]}&destination={destination[0]},{destination[1]}&return=polyline&apikey={api_key}"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

        routes = data.get('routes', [])
        if routes:
            sections = routes[0].get('sections', [])
            if sections:
                polyline_str = sections[0].get('polyline')
                if polyline_str:
                    decoded_route = list(iter_decode(polyline_str))
                    if not decoded_route: 
                         print("Warning: Polyline decoding resulted in empty list.")
                         return None
                    return decoded_route
        print("Warning: Polyline not found in HERE directions response.")
        return None
    except requests.exceptions.Timeout:
         print(f"Error fetching HERE directions: Request timed out")
         return None
    except requests.exceptions.RequestException as e:
         print(f"Error fetching HERE directions: {e}")
         return None
    except (ValueError, KeyError, IndexError, TypeError) as e:
         print(f"Error processing HERE directions data: {e}")
         return None


def get_coordinates(city):
    if not city: return None, None
    try:
        user_agent = getattr(Config, 'NOMINATIM_USER_AGENT', 'h2_route_app_v1')
        geolocator = Nominatim(user_agent=user_agent, timeout=10)
        query = city if "uk" in city.lower() else f"{city}, UK"
        location = geolocator.geocode(query, exactly_one=True)
        if location:
            return location.latitude, location.longitude
        else:
            print(f"Warning: Nominatim could not geocode city: {city}")
            return None, None
    except Exception as e: 
         print(f"Error during Nominatim geocoding for {city}: {e}")
         return None, None


def find_nearest_stations(origin_city, station_cities, destination_city):
    print(f"Finding nearest stations: Origin={origin_city}, Dest={destination_city}") 
    if not all([origin_city, station_cities, destination_city]):
         print("Warning: Missing input for find_nearest_stations")
         return []

    origin_coords = get_coordinates(origin_city)
    dest_coords = get_coordinates(destination_city)

    if origin_coords is None or dest_coords is None or origin_coords[0] is None or dest_coords[0] is None:
        print("Error: Could not geocode origin or destination city.")
        return []
    print(f"  Origin Coords: {origin_coords}")
    print(f"  Dest Coords: {dest_coords}")

    station_coords_cache = {}
    print(f"  Geocoding {len(station_cities)} potential station cities...")
    for city in station_cities:
        coords = get_coordinates(city)
        if coords and coords[0] is not None:
            station_coords_cache[city] = coords
    print(f"  Geocoded {len(station_coords_cache)} cities successfully.")

    valid_stations = {} 

    direction = "northbound" if dest_coords[0] > origin_coords[0] else "southbound"
    print(f"  Direction: {direction}")

    for city, coords in station_coords_cache.items():
        try:
            distance = geodesic(origin_coords, coords).miles

            is_close_enough = (distance <= 40)
            is_directional = False
            if distance <= 150:
                 if direction == "northbound" and coords[0] >= origin_coords[0] - 0.01:
                     is_directional = True
                 elif direction == "southbound" and coords[0] <= origin_coords[0] + 0.01: 
                     is_directional = True

            if is_close_enough or is_directional:
                 valid_stations[city] = distance

        except ValueError as e: 
             print(f"Warning: Could not calculate distance for {city}: {e}")

    if not valid_stations:
        print("  No valid stations found meeting criteria.")
        return []

    nearest_stations = sorted(valid_stations.items(), key=lambda item: item[1])
    print(f"  Found {len(nearest_stations)} nearest stations meeting criteria.")
    return nearest_stations


