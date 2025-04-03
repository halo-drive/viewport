# %%
from geopy.distance import geodesic
import folium
import requests
import pandas as pd
from geopy.geocoders import Nominatim
from collections import namedtuple
from flask import Blueprint, render_template
from config import Config




# HERE Maps API key
here_api_key = Config.HERE_API_KEY

# Polyline decoding functions and constants
FORMAT_VERSION = 1
DECODING_TABLE = [62, -1, -1, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, -1, -1, -1, -1, -1, -1, -1,
                  0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
                  22, 23, 24, 25, -1, -1, -1, -1, 63, -1, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
                  36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51]

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
    url = f"https://router.hereapi.com/v8/routes?transportMode=car&origin={origin[0]},{origin[1]}&destination={destination[0]},{destination[1]}&return=polyline&apikey={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'routes' in data and len(data['routes']) > 0:
            route = data['routes'][0]
            if 'sections' in route and len(route['sections']) > 0:
                section = route['sections'][0]
                if 'polyline' in section:
                    polyline_str = section['polyline']
                    decoded_geometry = list(iter_decode(polyline_str))
                    return decoded_geometry
    return None

def get_coordinates(city):
    geolocator = Nominatim(user_agent="my_app", timeout=10)
    location = geolocator.geocode(f"{city}, UK", exactly_one=True)
    if location:
        return location.latitude, location.longitude
    else:
        return None, None

def find_nearest_stations(origin_city, station_cities, destination_city):
    origin_coords = get_coordinates(origin_city)
    dest_coords = get_coordinates(destination_city)
    valid_stations = {}

    # Add stations within 40 miles to the valid_stations list
    for station_city in station_cities:
        station_coords = get_coordinates(station_city)
        if station_coords[0] is not None and station_coords[1] is not None:
            distance = geodesic(origin_coords, station_coords).miles
            if distance <= 40:
                valid_stations[station_city] = distance

    # Calculate direction
    if dest_coords[0] > origin_coords[0]:
        direction = "northbound"
    else:
        direction = "southbound"

    for station_city in station_cities:
        station_coords = get_coordinates(station_city)
        if station_coords[0] is not None and station_coords[1] is not None:
            # Check if the station is in the correct direction
            if direction == "northbound" and station_coords[0] > origin_coords[0]:
                distance = geodesic(origin_coords, station_coords).miles
                if distance <= 150:
                    valid_stations[station_city] = distance
            elif direction == "southbound" and station_coords[0] < origin_coords[0]:
                distance = geodesic(origin_coords, station_coords).miles
                if distance <= 150:
                    valid_stations[station_city] = distance

    if not valid_stations:
        return []

    nearest_stations = sorted(valid_stations.items(), key=lambda x: x[1])
    return nearest_stations

def launch_all(origin_city, Fuel_range_at_origin, destination_city, fuel_consumption, Fuel_range_at_nearest_stations1, Fuel_range_at_nearest_stations2):
    station_cities = ['Aberdeen', 'Birmingham', 'Cardiff', 'Glasgow', 'Leeds', 'Manchester', 'Liverpool', 'London']
    nearest_stations = find_nearest_stations(origin_city, station_cities, destination_city)

    if len(nearest_stations) != 0:
        origin_coords = get_coordinates(origin_city)
        dest_coords = get_coordinates(destination_city)
        origin_dest_distance = geodesic(origin_coords, dest_coords).miles

        if Fuel_range_at_origin > fuel_consumption:
            origin_to_dest = get_here_directions(origin_coords, dest_coords, here_api_key)

            if origin_to_dest:
                map_osm = folium.Map(location=origin_coords, zoom_start=6)
                folium.Marker(location=origin_coords, icon=folium.Icon(color='blue'), popup=f"Origin: {origin_city}").add_to(map_osm)
                folium.Marker(location=dest_coords, icon=folium.Icon(color='blue'), popup=f"Destination: {destination_city}").add_to(map_osm)
                folium.PolyLine(locations=origin_to_dest, color='cornflowerblue', weight=8).add_to(map_osm)

                df_locations = pd.DataFrame(origin_to_dest, columns=['Latitude', 'Longitude'])
                df0 = df_locations.to_json(orient='records')
                map_osm.save("templates/hroute.html")
                return map_osm

        if len(nearest_stations) == 1:
            a = nearest_stations[0]
            a1 = a[0]
            origin_coords = get_coordinates(origin_city)
            near_station1_coords = get_coordinates(a1)
            dest_coords = get_coordinates(destination_city)

            origin_dest_distance = geodesic(origin_coords, dest_coords).miles

            distance3 = geodesic(origin_coords, near_station1_coords).miles
            distance4 = geodesic(near_station1_coords, dest_coords).miles
            distance6 = geodesic(origin_coords, near_station1_coords).miles

            Fuel_range_at_nearest_stations_1m = (Fuel_range_at_nearest_stations1*8 + Fuel_range_at_origin*8) - distance6
            Fuel_range_req_from_nearest_stations1 = distance4
            Fuel_req_from_nearest_stations1 = Fuel_range_req_from_nearest_stations1*0.33
            Fuel_at_nearest_stations_1m = Fuel_range_at_nearest_stations_1m*0.33

            if Fuel_at_nearest_stations_1m > Fuel_req_from_nearest_stations1:
                print("The Fuel_range_at_nearest_stations1 ", Fuel_range_at_nearest_stations1)
                print("The Fuel_req_from_nearest_stations1 ", Fuel_req_from_nearest_stations1)

                origin_to_station1 = get_here_directions(origin_coords, near_station1_coords, here_api_key)
                station1_to_dest = get_here_directions(near_station1_coords, dest_coords, here_api_key)

                if origin_to_station1 and station1_to_dest:
                    map_osm = folium.Map(location=origin_coords, zoom_start=6)
                    folium.Marker(location=origin_coords, icon=folium.Icon(color='cornflowerblue'), popup=f"Origin: {origin_city}").add_to(map_osm)
                    folium.Marker(location=near_station1_coords, icon=folium.Icon(color='blue'), popup=f"Station 1: {a1}").add_to(map_osm)
                    folium.Marker(location=dest_coords, icon=folium.Icon(color='blue'), popup=f"Destination: {destination_city}").add_to(map_osm)
                    folium.Marker(location=near_station1_coords, icon=folium.Icon(color='pink'), popup="1").add_to(map_osm)

                    folium.PolyLine(locations=origin_to_station1, color='cornflowerblue', weight=8).add_to(map_osm)
                    folium.PolyLine(locations=station1_to_dest, color='cornflowerblue', weight=8).add_to(map_osm)

                    df_locations = pd.DataFrame(origin_to_station1 + station1_to_dest, columns=['Latitude', 'Longitude'])
                    df0 = df_locations.to_json(orient='records')
                    station_coords = [near_station1_coords[0], near_station1_coords[1]]
                    df_coords = pd.DataFrame([station_coords], columns=['Latitude', 'Longitude'])

                    map_osm.save("templates/hroute.html")
                    return map_osm

        elif len(nearest_stations) > 1:
            a = nearest_stations[0]
            a1 = a[0]
            b = nearest_stations[1]
            b1 = b[0]
            origin_coords = get_coordinates(origin_city)
            near_station1_coords = get_coordinates(a1)
            near_station2_coords = get_coordinates(b1)
            dest_coords = get_coordinates(destination_city)
            origin_dest_distance = fuel_consumption*7
            distance3 = geodesic(origin_coords, near_station1_coords).miles
            distance4 = geodesic(near_station1_coords, dest_coords).miles
            distance6 = geodesic(origin_coords, near_station1_coords).miles
            distance7 = geodesic(near_station1_coords, near_station2_coords).miles
            distance8 = geodesic(near_station2_coords, dest_coords).miles
            distance9 = geodesic(near_station2_coords, dest_coords).miles
            distance10 = geodesic(origin_coords, near_station2_coords).miles

            Fuel_range_at_nearest_stations_1m = (Fuel_range_at_nearest_stations1 + Fuel_range_at_origin*8) - distance6
            Fuel_range_req_from_nearest_stations1 = distance4
            Fuel_range_req_from_nearest_stations2 = distance8
            Fuel_range_at_nearest_stations_2m = (Fuel_range_at_nearest_stations1 + Fuel_range_at_nearest_stations2) - (distance6 + distance7)
            Fuel_range_at_nearest_stations_2m1 = Fuel_range_at_nearest_stations2 - distance10
            Fuel_at_nearest_stations_1m = Fuel_range_at_nearest_stations_1m*0.33
            Fuel_req_from_nearest_stations1 = Fuel_range_req_from_nearest_stations1*0.33
            Fuel_at_nearest_stations_2m1 = Fuel_range_at_nearest_stations_2m1*0.33
            Fuel_req_from_nearest_stations2 = Fuel_range_req_from_nearest_stations2*0.33
            Fuel_at_nearest_stations_2m = Fuel_range_at_nearest_stations_2m
            
            if Fuel_range_at_nearest_stations1 > Fuel_req_from_nearest_stations1:
                print("The Fuel_range_at_nearest_stations1 ", Fuel_range_at_nearest_stations1)
                print("The Fuel_req_from_nearest_stations1 ", Fuel_req_from_nearest_stations1)

                origin_to_station1 = get_here_directions(origin_coords, near_station1_coords, here_api_key)
                station1_to_dest = get_here_directions(near_station1_coords, dest_coords, here_api_key)

                if origin_to_station1 and station1_to_dest:
                    map_osm = folium.Map(location=origin_coords, zoom_start=6)
                    folium.Marker(location=origin_coords, icon=folium.Icon(color='cornflowerblue'), popup=f"Origin: {origin_city}").add_to(map_osm)
                    folium.Marker(location=near_station1_coords, icon=folium.Icon(color='blue'), popup=f"Station 1: {a1}").add_to(map_osm)
                    folium.Marker(location=dest_coords, icon=folium.Icon(color='blue'), popup=f"Destination: {destination_city}").add_to(map_osm)
                    folium.Marker(location=near_station1_coords, icon=folium.Icon(color='pink'), popup="1").add_to(map_osm)

                    folium.PolyLine(locations=origin_to_station1, color='cornflowerblue', weight=8).add_to(map_osm)
                    folium.PolyLine(locations=station1_to_dest, color='cornflowerblue', weight=8).add_to(map_osm)

                    df_locations = pd.DataFrame(origin_to_station1 + station1_to_dest, columns=['Latitude', 'Longitude'])
                    df0 = df_locations.to_json(orient='records')
                    station_coords = [near_station1_coords[0], near_station1_coords[1]]
                    df_coords = pd.DataFrame([station_coords], columns=['Latitude', 'Longitude'])
                    map_osm.save("templates/hroute.html")
                    return map_osm

            if Fuel_at_nearest_stations_2m1 > Fuel_range_req_from_nearest_stations2:
                print("The Fuel_at_nearest_stations_2m1 ", Fuel_at_nearest_stations_2m1)
                print("The Fuel_range_req_from_nearest_stations2 ", Fuel_range_req_from_nearest_stations2)              

                origin_to_station2 = get_here_directions(origin_coords, near_station2_coords, here_api_key)
                station2_to_dest = get_here_directions(near_station2_coords, dest_coords, here_api_key)

                if origin_to_station2 and station2_to_dest:
                    map_osm = folium.Map(location=origin_coords, zoom_start=6)
                    folium.Marker(location=origin_coords, icon=folium.Icon(color='blue'), popup=f"Origin: {origin_city}").add_to(map_osm)
                    folium.Marker(location=near_station2_coords, icon=folium.Icon(color='pink'), popup=f"Station 2: {b1}").add_to(map_osm)
                    folium.Marker(location=dest_coords, icon=folium.Icon(color='blue'), popup=f"Destination: {destination_city}").add_to(map_osm)

                    folium.PolyLine(locations=origin_to_station2, color='cornflowerblue', weight=8).add_to(map_osm)
                    folium.PolyLine(locations=station2_to_dest, color='cornflowerblue', weight=8).add_to(map_osm)

                    df_locations = pd.DataFrame(origin_to_station2 + station2_to_dest, columns=['Latitude', 'Longitude'])
                    df0 = df_locations.to_json(orient='records')
                    station_coords = [near_station2_coords[0], near_station2_coords[1]]
                    df_coords = pd.DataFrame([station_coords], columns=['Latitude', 'Longitude'])
                    map_osm.save("templates/hroute.html")
                    return map_osm

            if ((Fuel_at_nearest_stations_2m + Fuel_at_nearest_stations_1m) > Fuel_req_from_nearest_stations2) & (Fuel_range_at_nearest_stations1 != 0):
                print("The Fuel_at_nearest_stations_2m and 1m ", (Fuel_at_nearest_stations_2m + Fuel_at_nearest_stations_1m))
                print("The Fuel_req_from_nearest_stations2 ", Fuel_req_from_nearest_stations2)

                origin_to_station1 = get_here_directions(origin_coords, near_station1_coords, here_api_key)
                station1_to_station2 = get_here_directions(near_station1_coords, near_station2_coords, here_api_key)
                station2_to_dest = get_here_directions(near_station2_coords, dest_coords, here_api_key)

                if origin_to_station1 and station1_to_station2 and station2_to_dest:
                    map_osm = folium.Map(location=origin_coords, zoom_start=6)
                    folium.Marker(location=origin_coords, icon=folium.Icon(color='blue'), popup=f"Origin: {origin_city}").add_to(map_osm)
                    folium.Marker(location=near_station1_coords, icon=folium.Icon(color='pink'), popup=f"Station 1: {a1}").add_to(map_osm)
                    folium.Marker(location=near_station2_coords, icon=folium.Icon(color='pink'), popup=f"Station 2: {b1}").add_to(map_osm)
                    folium.Marker(location=dest_coords, icon=folium.Icon(color='blue'), popup=f"Destination: {destination_city}").add_to(map_osm)

                    folium.PolyLine(locations=origin_to_station1, color='cornflowerblue', weight=8).add_to(map_osm)
                    folium.PolyLine(locations=station1_to_station2, color='cornflowerblue', weight=8).add_to(map_osm)
                    folium.PolyLine(locations=station2_to_dest, color='cornflowerblue', weight=8).add_to(map_osm)

                    df_locations = pd.DataFrame(origin_to_station1 + station1_to_station2 + station2_to_dest, columns=['Latitude', 'Longitude'])
                    df0 = df_locations.to_json(orient='records')
                    station_coords = [(near_station1_coords[0], near_station1_coords[1]), (near_station2_coords[0], near_station2_coords[1])]
                    df_coords = pd.DataFrame(station_coords, columns=['Latitude', 'Longitude'])
                    map_osm.save("templates/hroute.html")
                    return map_osm

    with open("templates/hroute.html", "w") as f:
        f.write("<html><head><title>No Route Found</title></head><body><h1 style='text-align: center; color: aliceblue;'>No suitable route found with the given fuel range.</h1></body></html>")

    print("No suitable route found with the given fuel range.")
    
    return None

# Example usage

def getdatah(orgc,dstc,fcmspt,feff,fuorgn,fuelrng1,fuelrng2):
    origin_city = orgc
    Fuel_range_at_origin = fuorgn
    destination_city = dstc
    Fuel_range_at_nearest_stations1 = fuelrng1
    Fuel_range_at_nearest_stations2 = fuelrng2
    Fuel_Efficiency = feff
    fuel_consumption = fcmspt
    launch_all(origin_city, Fuel_range_at_origin, destination_city, fuel_consumption, Fuel_range_at_nearest_stations1, Fuel_range_at_nearest_stations2)