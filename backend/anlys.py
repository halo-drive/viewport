from typing import Tuple, List
import requests, re, joblib, time
from geopy.distance import geodesic
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import lightgbm
from config import Config

def launch_not_all(pall, vhtype, strtpl, destpl, vhyage, disptm):
    GEOCODING_API_URL = "https://geocode.maps.co/search"
    MAPBOX_DIRECTIONS_API_URL = "https://api.mapbox.com/directions/v5/mapbox/driving-traffic/"
    MAPBOX_GEOCODING_API_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/"
    WEATHER_API_URL = "http://api.weatherapi.com/v1/current.json"
    # Get API keys from config
    mapbox_token = Config.MAPBOX_TOKEN
    weather_api_key = Config.WEATHER_API_KEY
    geocoding_api = Config.GEOCODING_API_KEY
    model = joblib.load('Hydrogen_model.pkl')


    def get_coordinates(place_name: str) -> Tuple[float, float]:
        start_time = time.time() 
        params = {
            "q": f"{place_name}",
            "api_key": geocoding_api
        }
        try:
            response = requests.get(GEOCODING_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            max_importance_place = max(data, key=lambda place: place['importance'])
            end_time = time.time()
            return max_importance_place['lat'], max_importance_place['lon']
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving coordinates: {e}")
            return None, None

    def get_traffic_data(origin_coordinates, destination_coordinates, fuelstation_coordinates, mapbox_token):
        try:
            start_time = time.time() 
            url = f"{MAPBOX_DIRECTIONS_API_URL}{origin_coordinates[1]},{origin_coordinates[0]};{fuelstation_coordinates[1]},{fuelstation_coordinates[0]};{destination_coordinates[1]},{destination_coordinates[0]}?annotations=congestion_numeric&overview=full&waypoints=0;2&access_token={mapbox_token}"
            response = requests.get(url)
            data = response.json()
            congestion_numeric = data.get("routes", [])[0].get("legs", [])[0].get("annotation", {}).get("congestion_numeric", [])
            # Filter out null and unknown values
            valid_congestion_values = [value for value in congestion_numeric if value is not None]
            average_congestion = sum(valid_congestion_values) / len(valid_congestion_values)
            end_time = time.time()
            if average_congestion >= 0 and average_congestion < 40:
                return "Low"
            elif average_congestion >= 40 and average_congestion < 60:
                return "Medium"
            else:
                return "Heavy"    
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving coordinates: {e}")

    def find_nearest_station(given_location, station_postal_codes, mapbox_token):
        start_time = time.time() 
        given_location_url = f'{MAPBOX_GEOCODING_API_URL}{given_location}.json?access_token={mapbox_token}'
        try:
            given_location_response = requests.get(given_location_url).json()
            given_location_coords = given_location_response['features'][0]['geometry']['coordinates']
            # Geocode the station postal codes and calculate distances
            nearest_station = None
            min_distance = float('inf')
            for postal_code in station_postal_codes:
                postal_code_url = f'https://api.mapbox.com/geocoding/v5/mapbox.places/{postal_code}.json?access_token={mapbox_token}'
                postal_code_response = requests.get(postal_code_url).json()
                postal_code_coords = postal_code_response['features'][0]['geometry']['coordinates']
                # Calculate the distance between the given location and the station postal code
                # This example uses a simple Euclidean distance calculation for simplicity
                distance = ((given_location_coords[0] - postal_code_coords[0]) ** 2 + (given_location_coords[1] - postal_code_coords[1]) ** 2) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    nearest_station = postal_code
            end_time = time.time()
            return nearest_station
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving coordinates: {e}")
            return None, None
    
    def calculate_distances(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Tuple[float, float]:
        start_time = time.time() 
        city_distance_m = 0
        highway_distance_m = 0
        highway_pattern = re.compile(r'\\\\b\\[A,B,M\\]\\\\d+')
        params = {
            "access_token": mapbox_token,
            "alternatives": "false",
            "geometries": "geojson",
            "language": "en",
            "overview": "simplified",
            "steps": "true",
            "notifications": "none",
        }
        start_lat, start_lon = start_coords
        end_lat, end_lon = end_coords
        url = f"{MAPBOX_DIRECTIONS_API_URL}{start_lon}%2C{start_lat}%3B{end_lon}%2C{end_lat}"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            route_data = response.json()
            for route in route_data["routes"]:
                for leg in route["legs"]:
                    for step in leg["steps"]:
                        instruction = step["maneuver"]["instruction"]
                        distance_m = step["distance"]
                        name = step.get("name", "")
                        if highway_pattern.search(instruction) or not name:
                            highway_distance_m += distance_m
                        else:
                            city_distance_m += distance_m
            city_distance_mi = city_distance_m * 0.000621371
            highway_distance_mi = highway_distance_m * 0.000621371
            end_time = time.time()
            return city_distance_mi, highway_distance_mi
        except requests.exceptions.RequestException as e:
            print(f"Error calculating distances: {e}")
            return 0.0, 0.0
    
    def get_route_coordinates(start_coords, end_coords, steps=50):
        start_time = time.time()
        params = {
            "access_token": mapbox_token,
            "geometries": "geojson",
            "steps": "true"
        }
        try:
            # Construct URL with sample start and end coordinates
            url = f"{MAPBOX_DIRECTIONS_API_URL}{start_coords[1]}%2C{start_coords[0]}%3B{end_coords[1]}%2C{end_coords[0]}"
            # Send request to Mapbox Directions API
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                # Initialize list to store extracted coordinates
                extracted_coordinates = []
                accumulated_distance = 0
                prev_coord = None
                # Loop through routes, legs, and steps to extract coordinates
                for route in data["routes"]:
                    for leg in route["legs"]:
                        for step in leg["steps"]:
                            if "geometry" in step and "coordinates" in step["geometry"]:
                                step_coordinates = step["geometry"]["coordinates"]
                                for coord in step_coordinates:
                                    if prev_coord:
                                        # Calculate distance between previous and current coordinate
                                        distance = geodesic((prev_coord[1], prev_coord[0]), (coord[1], coord[0])).meters
                                        accumulated_distance += distance
                                        if accumulated_distance >= 20000:
                                            extracted_coordinates.append(coord)
                                            accumulated_distance = 0
                                    prev_coord = coord
                # Calculate interval for extracting coordinates
                interval = max(len(extracted_coordinates) // (steps + 1), 1)
                # Initialize list to store final route coordinates
                route_coordinates = []
                if len(extracted_coordinates) <= steps:
                    # If extracted coordinates are fewer than steps, use all coordinates
                    route_coordinates = extracted_coordinates
                else:
                    # Extract coordinates evenly with calculated interval
                    for i in range(1, steps + 1):
                        index = i * interval
                        route_coordinates.append(extracted_coordinates[index])
                end_time = time.time()
                return route_coordinates
            else:
                print("Error:", response.status_code)
                return []
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving route coordinates : {e}")
            return []
    
    def get_weather_data(api_key: str, coordinates_list: List[Tuple[float, float]]) -> Tuple[float, str, str]:
        start_time = time.time()
        temperature_sum = 0
        snow_sum = 0
        rain_sum = 0
        visibility_sum = 0
        valid_coordinates = 0
        for lat, lon in coordinates_list:
            params = {
                "key": api_key,
                "q": f"{lon},{lat}"  # Swap the order of lat and lon if necessary
            }
            try:
                response = requests.get(WEATHER_API_URL, params=params)
                response.raise_for_status()
                weather_data = response.json()
                current_weather_data = weather_data.get('current', {})
                temperature = current_weather_data.get('temp_c', 0.0)
                snow = current_weather_data.get('snow_mm', 0.0)
                rain = current_weather_data.get('precip_mm', 0.0)
                visibility = current_weather_data.get('vis_km', 0.0)
                temperature_sum += temperature
                snow_sum += snow
                rain_sum += rain
                visibility_sum += visibility
                valid_coordinates += 1
            except requests.exceptions.RequestException as e:
                print(f"Error retrieving weather data for {lat}, {lon}: {e}")
                continue  # Skip to the next coordinate
    
        if valid_coordinates > 0:
            average_temperature = temperature_sum / valid_coordinates
            average_snow = snow_sum / valid_coordinates
            average_rain = rain_sum / valid_coordinates
            average_visibility = visibility_sum / valid_coordinates
        else:
            average_temperature = 0.0
            average_snow = 0.0
            average_rain = 0.0
            average_visibility = 0.0
    
        snow_classification = categorize_snow_level(average_snow, average_visibility)
        rain_classification = categorize_rain_level(average_rain)
    
        end_time = time.time()
        return average_temperature, snow_classification, rain_classification
    
    def categorize_snow_level(snow: float, visibility: float) -> str:
        # Categorize snow level
        if snow == 0:
            return "Low"
        elif snow <= 1:
            return "Low"
        elif 1 < snow <= 5:
            if visibility >= 1:
                return "Low"
            elif 0.5 <= visibility < 1:
                return "Medium"
            else:
                return "Heavy"
        else:
            return "Heavy"
    
    def categorize_rain_level(rain: float) -> str:
        # Categorize rain level
        if rain == 0:
            return "Low"
        elif rain <= 2.5:
            return "Low"
        elif 2.5 < rain <= 7.6:
            return "Medium"
        else:
            return "Heavy"
    
    def main(pall, vhtype, strtpl, destpl, vhyage, disptm):
        station_postal_codes = ['AB12 3SH', 'S60 5WG', 'B25 8DW', 'SN3 4QS', 'TW6 2GE']
        # Get user inputs
        pallets = float(pall)
        total_payload = pallets * 0.88
        vehicle_type, vehicle_range, Tank_capacity = find_vehicle_type_range_and_capacity(total_payload, vhtype)
        Origin_depot = strtpl
        Origin_depot_uk = Origin_depot + ", UK"
        Destination_depot = destpl
        Destination_depot_uk = Destination_depot + ", UK"
        Vehicle_age = float(vhyage)
        Goods_weight = total_payload
        Avg_Speed_mph = 60
        dispatch_time = disptm
        # Get coordinates for start and destination places
        try:
            origin_coordinates = get_coordinates(Origin_depot_uk)
            destination_coordinates = get_coordinates(Destination_depot_uk)
            print("")
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return
        try:
            nearest_fuel_station = find_nearest_station(Origin_depot_uk, station_postal_codes, mapbox_token)
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return
        try:
            fuel_station_coordinates = get_coordinates(nearest_fuel_station)
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return
        # Calculate distances for city and highway
        try:
            origin_to_fuel_station = calculate_distances(origin_coordinates, fuel_station_coordinates)
            fuel_station_to_destination = calculate_distances(fuel_station_coordinates, destination_coordinates)
            total_city_distance = origin_to_fuel_station[0] + fuel_station_to_destination[0]
            total_highway_distance = origin_to_fuel_station[1] + fuel_station_to_destination[1]
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return
        # Get coordinates along the route and city and highway distances
        try:
            traffic_congestion_level = get_traffic_data(origin_coordinates, destination_coordinates, fuel_station_coordinates, mapbox_token)
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return
        try:
            coordinates = get_route_coordinates(origin_coordinates, destination_coordinates)
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return
        # Get average weather data for route coordinates
        try:
            average_temperature, snow_classification, rain_classification = get_weather_data(weather_api_key, coordinates)
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return
        # Get input and make predictions
        raw_input_df = get_raw_input(Origin_depot, Destination_depot, nearest_fuel_station, total_highway_distance, total_city_distance, traffic_congestion_level, average_temperature, rain_classification, snow_classification, pallets, Vehicle_age, Goods_weight, Avg_Speed_mph, dispatch_time, vehicle_type, vehicle_range, Tank_capacity, total_payload)
        prediction = model.predict(raw_input_df)
        
        print(f"Prediction from model: {prediction}")
        efficiency_prediction = prediction[0]
        print(f"Efficiency prediction: {efficiency_prediction}")
        
        eff_pred = f"{efficiency_prediction:.2f}" ###############
            
        print(f"Total city distance: {total_city_distance}, Total highway distance: {total_highway_distance}")
        Total_dist = total_city_distance + total_highway_distance
        print(f"Total distance: {Total_dist}")
        
            
        Total_Required_Fuel = Total_dist / efficiency_prediction
        print(f"Total required fuel: {Total_Required_Fuel}")
        
        ttl_rqfl = f"{Total_Required_Fuel:.2f}"
            
        Total_cost_hydrogen = Total_Required_Fuel * 12
        print(f"Total cost hydrogen: {Total_cost_hydrogen}")
        
        ttl_csthyd = f"{Total_cost_hydrogen:.2f}"
            
        Cost_per_mile = Total_cost_hydrogen / Total_dist
        print(f"Cost per mile: {Cost_per_mile}")
            
        over_cst = f"{Total_cost_hydrogen*0.1:.2f}"
        print(f"Overhead cost: {over_cst}")
            
        ttl_cst = f"{Total_cost_hydrogen+(Total_cost_hydrogen*0.1):.2f}"
        print(f"Total cost: {ttl_cst}")
            
        cst_pm = f"{Cost_per_mile:.2f}"
        print(f"Cost per mile: {cst_pm}")
    
        # Feature importance
        feature_importance = model.feature_importances_
        sorted_idx = np.argsort(feature_importance)
        fig = plt.figure(figsize=(12, 6))
        plt.barh(range(len(sorted_idx)), feature_importance[sorted_idx], align='center')
        plt.yticks(range(len(sorted_idx)), np.array(raw_input_df.columns)[sorted_idx])
        plt.title('Feature Importance')
        avg_tm = f"{average_temperature:.2f}"
        dst_hg = f"{total_highway_distance:.2f}"
        ttl_cty = f"{total_city_distance:.2f}"
        resultia = []
        resultia.append("fulls")
        resultia.append(avg_tm)
        resultia.append(rain_classification)
        resultia.append(snow_classification)
        resultia.append(dst_hg)
        resultia.append(ttl_cty)
        resultia.append(traffic_congestion_level)
        resultia.append(nearest_fuel_station)
        resultia.append(Tank_capacity)
        resultia.append(eff_pred)
        resultia.append(ttl_rqfl)
        resultia.append(ttl_csthyd)
        resultia.append(over_cst)
        resultia.append(ttl_cst)
        resultia.append(cst_pm)
        return resultia
    
    # Define encodings
    vehicle_type_encoded = ['HVS HGV', 'HVS MCV', 'Hymax Series']
    origin_encoded = {'Aberdeen': 0, 'Birmingham': 1, 'Cardiff': 2, 'Glasgow': 3, 'Leeds': 4, 'Liverpool': 5, 'London': 6, 'Manchester': 7}
    nearest_station_encoded = {'AB12 3SH': 0, 'B25 8DW': 1, 'S60 5WG': 2, 'SN3 4QS': 3, 'TW6 2GE': 4}
    dispatch_encoded = {'morning': 0, 'night': 1, 'noon': 2}
    traffic_congestion_encoded = {'low': 0, 'medium': 1, 'high': 2}
    rain_encoded = {'low': 0, 'medium': 1, 'high': 2}
    snow_encoded = {'low': 0, 'medium': 1, 'high': 2}
    
    def find_vehicle_type_range_and_capacity(total_payload, vhtype):
        if total_payload <= 16:
            vehicle_type = vhtype
            if vehicle_type == 'HVS HGV':
                return vehicle_type, 300, 51
            elif vehicle_type == 'HVS MCV':
                return vehicle_type, 370, 51
            elif vehicle_type == 'Hymax Series':
                return vehicle_type, 422, 60
            else:
                raise ValueError("Invalid vehicle type: {}".format(vehicle_type))
        else:
            vehicle_type = vhtype
            if vehicle_type == 'HVS HGV' or vehicle_type == 'Hymax Series':
                return vehicle_type, 300, 51 if vehicle_type == 'HVS HGV' else 60
            else:
                raise ValueError("Invalid vehicle type: {}".format(vehicle_type))
    
    def get_raw_input(Origin_depot, Destination_depot, nearest_fuel_station, total_highway_distance, total_city_distance, traffic_congestion_level, average_temperature, rain_classification, snow_classification, pallets, Vehicle_age, Goods_weight, Avg_Speed_mph, dispatch_time, vehicle_type, vehicle_range, Tank_capacity, total_payload):
        start_time = time.time()
        # Encode categorical variables
        encoded_origin = origin_encoded.get(Origin_depot, -1)
        encoded_destination = origin_encoded.get(Destination_depot, -1)
        encoded_dispatch_time = dispatch_encoded.get(dispatch_time, -1)
        encoded_nearest_station = nearest_station_encoded.get(nearest_fuel_station, -1)
        # Encode traffic congestion, temperature, precipitation, and snow
        encoded_avg_traffic_congestion = traffic_congestion_encoded.get(traffic_congestion_level, -1)
        encoded_avg_rain = rain_encoded.get(rain_classification, -1)
        encoded_avg_snow = snow_encoded.get(snow_classification, -1)
        dummy_variables = {vehicle: (1 if vehicle == vehicle_type else 0) for vehicle in vehicle_type_encoded}
        Goods_weight = pallets * 0.88
        Avg_Speed_mph = 65
        input_data = {
            "Vehicle_age": [Vehicle_age],
            "Goods_weight": [Goods_weight],
            "Avg_traffic_congestion": [encoded_avg_traffic_congestion],
            "Avg_temp": [average_temperature],
            "Avg_Precipitation": [encoded_avg_rain],
            "Avg_snow": [encoded_avg_snow],
            "Origin_depot": [encoded_origin],
            "Destination_depot": [encoded_destination],
            "Avg_Speed_mph": [Avg_Speed_mph],
            "Distance_highway": [total_highway_distance],
            "Distance_city": [total_city_distance],
            "dispatch_time": [encoded_dispatch_time],
            "total_payload": [total_payload],
            "tank_capacity": [Tank_capacity],
            "range": [vehicle_range],
            "Closest_station": [encoded_nearest_station],
            "Total_distance_miles": [total_city_distance + total_highway_distance]
        }
        input_data.update(dummy_variables)
        end_time = time.time()
        return pd.DataFrame(input_data)
    return main(pall, vhtype, strtpl, destpl, vhyage, disptm)