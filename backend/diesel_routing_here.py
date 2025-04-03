#!/usr/bin/env python
# coding: utf-8

# In[27]:


import folium
import requests
from geopy.distance import geodesic
from typing import Tuple, List
from collections import namedtuple

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
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        routes = data.get('routes', [])
        if routes:
            sections = routes[0].get('sections', [])
            if sections:
                polyline_str = sections[0].get('polyline', '')
                return list(iter_decode(polyline_str))
    return None

def get_coordinates(place_name: str, api_key: str) -> Tuple[float, float]:
    url = f"https://geocode.search.hereapi.com/v1/geocode?q={place_name}&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'items' in data and data['items']:
            location = data['items'][0]['position']
            return location['lat'], location['lng']
    return None, None

def get_fuel_station_coordinates(coords: Tuple[float, float], api_key: str) -> Tuple[float, float]:
    base_url = 'https://discover.search.hereapi.com/v1/discover'
    params = {
        'q': 'fuel station',
        'apiKey': api_key,
        'at': f'{coords[0]},{coords[1]}'
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        fuel_stations = response.json()
        if 'items' in fuel_stations and fuel_stations['items']:
            closest_station = min(fuel_stations['items'], key=lambda x: x['distance'])
            return closest_station['position']['lat'], closest_station['position']['lng']
    return None

def get_route_with_fuel_stations(api_key: str, origin_city: str, destination_city: str) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]]:
    start_coords = get_coordinates(origin_city, api_key)
    end_coords = get_coordinates(destination_city, api_key)
    route_points = get_here_directions(f"{start_coords[0]},{start_coords[1]}", f"{end_coords[0]},{end_coords[1]}", api_key)
    
    if not route_points:
        raise ValueError("Unable to retrieve route points")

    total_distance = sum(geodesic(route_points[i], route_points[i+1]).km for i in range(len(route_points) - 1))
    interval_distance = total_distance / 4
    fuel_station_coords = []
    route_coordinates = []  # Initialize route_coordinates as an empty list

    # Get fuel station around the 5 km mark from origin
    cumulative_distance = 0
    for i in range(1, len(route_points)):
        segment_distance = geodesic(route_points[i-1], route_points[i]).km
        cumulative_distance += segment_distance

        if cumulative_distance >= 5:  # Look for fuel station around the 10 km mark
            fuel_coords = get_fuel_station_coordinates(route_points[i], api_key)
            if fuel_coords:
                fuel_station_coords.append(fuel_coords)
                break  # Stop searching once found

    # Add fuel stations approximately every quarter of the total route distance
    cumulative_distance = 0
    last_fuel_station_index = 0

    for i in range(1, len(route_points)):
        route_coordinates.append(route_points[i])
        
        segment_distance = geodesic(route_points[i-1], route_points[i]).km
        cumulative_distance += segment_distance

        if cumulative_distance >= interval_distance:
            fuel_coords = get_fuel_station_coordinates(route_points[i], api_key)
            if fuel_coords and fuel_coords not in fuel_station_coords:
                fuel_station_coords.append(fuel_coords)
                cumulative_distance = 0
                last_fuel_station_index = i

    # Get fuel station towards destination
    # Calculate the remaining distance to the destination
    remaining_distance = total_distance
    for i in range(last_fuel_station_index, len(route_points) - 1):
        segment_distance = geodesic(route_points[i], route_points[i+1]).km
        remaining_distance -= segment_distance
        if remaining_distance <= interval_distance:
            fuel_coords_destination = get_fuel_station_coordinates(route_points[i+1], api_key)
            if fuel_coords_destination:
                fuel_station_coords.append(fuel_coords_destination)
            break

    route_coordinates.insert(0, start_coords)  # Insert start_coords at the beginning

    return route_coordinates, route_points, fuel_station_coords

def display_route_on_map(route_coordinates, fuel_station_coords, origin_city, destination_city, route_points):
    start_coords = route_coordinates[0]
    end_coords = route_coordinates[-1]
    map_center = (start_coords[0], start_coords[1])
    route_map = folium.Map(location=map_center, zoom_start=6)

    # Add red marker for origin
    folium.Marker(location=start_coords, popup=origin_city, icon=folium.Icon(color='red')).add_to(route_map)
    
    # Add red marker for destination
    folium.Marker(location=end_coords, popup=destination_city, icon=folium.Icon(color='red')).add_to(route_map)

    # Add blue markers for fuel stops
    for fuel_stop in fuel_station_coords:
        folium.Marker(location=fuel_stop, popup='Fuel Stop', icon=folium.Icon(color='blue')).add_to(route_map)

    # Add the route polyline
    folium.PolyLine(locations=route_points, color='blue', weight=5, opacity=0.7).add_to(route_map)
    route_map.save("templates/droute.html")
    return route_map

def launch_all(origin_city, destination_city):
    api_key = "PGQ79WQSjN1KIbgRY_LdG9O1WlQ1WinCp7hhCY_IMbw"  # Replace with your API key
    route_coords, route_points, fuel_station_coords = get_route_with_fuel_stations(
        api_key, origin_city=origin_city, destination_city=destination_city
    )
    return display_route_on_map(route_coords, fuel_station_coords, origin_city, destination_city, route_points)

# Launch the script
def getdata(orgc,dstc):
    start_place=orgc
    destination_place= dstc
    launch_all(
    origin_city=start_place,  #(User entered input)
    
        
    destination_city=destination_place, #(User entered input)
     
)

# Display the map

