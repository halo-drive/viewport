import folium
import requests
import os
from geopy.distance import geodesic
from typing import Tuple, List
from collections import namedtuple
from config import Config

# HERE Maps API key from config
api_key = Config.HERE_API_KEY

# Polyline decoding functions (same as in diesel_routing_here.py)
FORMAT_VERSION = 1
DECODING_TABLE = [
    62, -1, -1, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, -1, -1, -1, -1, -1, -1, -1,
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
    22, 23, 24, 25, -1, -1, -1, -1, 63, -1, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
    36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51
]

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

def get_here_directions(origin, destination, api_key):
    url = f"https://router.hereapi.com/v8/routes?transportMode=car&origin={origin}&destination={destination}&return=polyline&apikey={api_key}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            routes = data.get('routes', [])
            
            if routes:
                sections = routes[0].get('sections', [])
                
                if sections:
                    polyline_str = sections[0].get('polyline', '')
                    route_points = list(iter_decode(polyline_str))
                    return route_points
        else:
            print(f"API request failed with status code {response.status_code}")
    
    except Exception as e:
        print(f"Error getting directions: {str(e)}")
    
    return None

def get_coordinates(place_name: str, api_key: str = None) -> Tuple[float, float]:
    api_key = api_key or Config.HERE_API_KEY
    
    url = f"https://geocode.search.hereapi.com/v1/geocode?q={place_name}&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'items' in data and data['items']:
                location = data['items'][0]['position']
                coords = (location['lat'], location['lng'])
                return coords
        else:
            print(f"Geocoding request failed with status {response.status_code}")
    
    except Exception as e:
        print(f"Error getting coordinates for {place_name}: {str(e)}")
    
    return None, None

def get_charging_station_coordinates(coords: Tuple[float, float], api_key: str) -> Tuple[float, float]:
    base_url = 'https://discover.search.hereapi.com/v1/discover'
    params = {
        'q': 'ev charging station',  # Search query for EV charging stations
        'apiKey': api_key,
        'at': f'{coords[0]},{coords[1]}',  # Coordinates to search near
        'limit': 5  # Get a few results to ensure we find one
    }
    
    try:
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            charging_stations = response.json()
            
            if 'items' in charging_stations and charging_stations['items']:
                # Find the closest station
                closest_station = min(charging_stations['items'], key=lambda x: x.get('distance', float('inf')))
                station_coords = (closest_station['position']['lat'], closest_station['position']['lng'])
                
                # Get the station name for logging
                station_name = closest_station.get('title', 'Unknown Station')
                station_address = closest_station.get('address', {}).get('label', 'No address')
                
                #print(f"Found charging station: {station_name}")
                #print(f"Station address: {station_address}")
                
                return station_coords
    
    except Exception as e:
        print(f"Error finding charging station: {str(e)}")
    
    return None

def display_route_on_map(route_coordinates, charging_station_coords, origin_city, destination_city, route_points):
    print(f"Creating map for route from {origin_city} to {destination_city}")
    
    start_coords = route_coordinates[0]
    end_coords = route_coordinates[-1]
    map_center = (start_coords[0], start_coords[1])
    
    # Create the map centered on the starting point
    route_map = folium.Map(location=map_center, zoom_start=6)

    # Add green marker for origin
    folium.Marker(
        location=start_coords, 
        popup=origin_city, 
        icon=folium.Icon(color='green')
    ).add_to(route_map)
    
    # Add red marker for destination
    folium.Marker(
        location=end_coords, 
        popup=destination_city, 
        icon=folium.Icon(color='red')
    ).add_to(route_map)

    # Add blue markers for charging stops
    for i, charging_stop in enumerate(charging_station_coords):
        folium.Marker(
            location=charging_stop, 
            popup=f'Charging Station {i+1}', 
            icon=folium.Icon(color='blue', icon='plug', prefix='fa')
        ).add_to(route_map)

    # Add the route polyline
    folium.PolyLine(
        locations=route_points, 
        color='blue', 
        weight=5, 
        opacity=0.7
    ).add_to(route_map)
    
    # Save the map to HTML file
    output_path = "templates/eroute.html"
    route_map.save(output_path)
    
    return route_map

def launch_all(origin_city, destination_city):
    print(f"Launching route mapping from {origin_city} to {destination_city}")
    
    try:
        route_coords, route_points, charging_station_coords = get_route_with_charging_stations(
            api_key, origin_city=origin_city, destination_city=destination_city
        )
        
        result_map = display_route_on_map(
            route_coords, 
            charging_station_coords, 
            origin_city, 
            destination_city, 
            route_points
        )
        
        print("Route mapping completed successfully")
        return result_map
    
    except Exception as e:
        print(f"Error in launch_all: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

# Utility function for the main module to call
def getdata(orgc, dstc):
    print(f"getdata called with origin={orgc}, destination={dstc}")
    
    start_place = orgc
    destination_place = dstc
    
    result = launch_all(
        origin_city=start_place,
        destination_city=destination_place,
    )
    
    if result:
        print("Route map created successfully")
    else:
        print("Failed to create route map")
        
    return result

def get_route_with_charging_stations(api_key: str, origin_city: str, destination_city: str) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]]:
    print(f"Finding route from {origin_city} to {destination_city}")
    
    start_coords = get_coordinates(origin_city, api_key)
    end_coords = get_coordinates(destination_city, api_key)
    
    if not start_coords[0] or not end_coords[0]:
        print("Failed to get coordinates for origin or destination")
        raise ValueError("Unable to retrieve coordinates for origin or destination")
    
    print(f"Origin coordinates: {start_coords}")
    print(f"Destination coordinates: {end_coords}")
    
    # Get the main route
    route_points = get_here_directions(f"{start_coords[0]},{start_coords[1]}", f"{end_coords[0]},{end_coords[1]}", api_key)
    
    if not route_points:
        print("Failed to retrieve route points")
        raise ValueError("Unable to retrieve route points")
    
    print(f"Retrieved main route with {len(route_points)} points")
    
    # Calculate total route distance
    total_distance = sum(geodesic(route_points[i], route_points[i+1]).km for i in range(len(route_points) - 1))
    print(f"Total route distance: {total_distance} km")
    
    # For electric vehicles, we need more frequent charging stops
    # We'll aim for stops approximately every 100-150 km
    interval_distance = 120  # km between charging stations
    
    charging_station_coords = []
    route_coordinates = []  # Initialize route_coordinates as an empty list

    # Get charging station around the 5 km mark from origin
    cumulative_distance = 0
    for i in range(1, len(route_points)):
        segment_distance = geodesic(route_points[i-1], route_points[i]).km
        cumulative_distance += segment_distance

        if cumulative_distance >= 5:  # Look for charging station around the 5 km mark
            charging_coords = get_charging_station_coordinates(route_points[i], api_key)
            if charging_coords:
                charging_station_coords.append(charging_coords)
                #print(f"Added initial charging station")
                break  # Stop searching once found

    # Add charging stations approximately every interval_distance
    cumulative_distance = 0
    last_charging_station_index = 0

    for i in range(1, len(route_points)):
        route_coordinates.append(route_points[i])
        
        segment_distance = geodesic(route_points[i-1], route_points[i]).km
        cumulative_distance += segment_distance

        if cumulative_distance >= interval_distance:
            charging_coords = get_charging_station_coordinates(route_points[i], api_key)
            if charging_coords and charging_coords not in charging_station_coords:
                charging_station_coords.append(charging_coords)
                #print(f"Added mid-route charging station")
                #print(f"Distance from previous station: {cumulative_distance} km")
                cumulative_distance = 0
                last_charging_station_index = i

    # Get charging station towards destination
    # Calculate the remaining distance to the destination
    remaining_distance = total_distance
    for i in range(last_charging_station_index, len(route_points) - 1):
        segment_distance = geodesic(route_points[i], route_points[i+1]).km
        remaining_distance -= segment_distance
        if remaining_distance <= interval_distance / 2:  # Add a station if we're halfway to interval
            charging_coords_destination = get_charging_station_coordinates(route_points[i+1], api_key)
            if charging_coords_destination and charging_coords_destination not in charging_station_coords:
                charging_station_coords.append(charging_coords_destination)
                #print(f"Added destination-area charging station")
                #print(f"Distance from previous station: {total_distance - remaining_distance} km")
            break

    # Limit the number of charging stations to 4 maximum
    if len(charging_station_coords) > 3:
        #print(f"Found {len(charging_station_coords)} charging stations, limiting to 4")
        
        # Always keep the first station
        indices_to_keep = [0]
        
        # Add middle stations if we have them
        if len(charging_station_coords) > 2:
            # Define the middle stations (all except first and last)
            middle_indices = list(range(1, len(charging_station_coords) - 1))
            
            # Calculate how to distribute 2 stations among the middle points
            step_size = max(1, len(middle_indices) // 2)
            
            # Add up to 2 middle stations
            for i in range(0, len(middle_indices), step_size):
                if len(indices_to_keep) < 3:  # We want 2 middle stations at most
                    indices_to_keep.append(middle_indices[i])
        
        # Add the last station if we have space and if it exists
        if len(indices_to_keep) < 3 and len(charging_station_coords) > 1:
            indices_to_keep.append(len(charging_station_coords) - 1)
        
        # Extract only the stations we want to keep
        charging_station_coords = [charging_station_coords[i] for i in indices_to_keep]
        #print(f"Limited to {len(charging_station_coords)} stations")

    route_coordinates.insert(0, start_coords)  # Insert start_coords at the beginning
    print(f"Final route has {len(route_coordinates)} points and {len(charging_station_coords)} charging stations")

    return route_coordinates, route_points, charging_station_coords