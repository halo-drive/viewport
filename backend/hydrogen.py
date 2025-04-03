import random
from flask import Flask, render_template, request, Response, Blueprint
import json
#!/usr/bin/env python
# coding: utf-8

# In[5]:


from typing import Tuple, List
import requests
import re
from geopy.distance import geodesic
import joblib
import time
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from hydrogen_here_map import getdatah


# In[6]:


GEOCODING_API_URL = "https://geocode.maps.co/search"
MAPBOX_DIRECTIONS_API_URL = "https://api.mapbox.com/directions/v5/mapbox/driving-traffic/"
MAPBOX_GEOCODING_API_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/"
WEATHER_API_URL = "http://api.weatherapi.com/v1/forecast.json "
DATE_FORMAT = "%Y-%m-%d"


# In[7]:


mapbox_token = "pk.eyJ1IjoiY2hlc2hpcmV0ZWNoIiwiYSI6ImNsdWppd2xuMTBja3cya2w1dmd5N2pybXkifQ.gPKzd8EEX8DTwmO0oBRQ1Q"
# weather_api_key = "f82511f3a0934ec8b7790510243003"
weather_api_key = "c6b99eb5ae4943a2a85140655250104"
geocoding_api = "66053a1a9d7ef949143373sibb51465"


# In[8]:


model = joblib.load('Hydrogen_model.pkl')


# In[9]:


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
#         print(f"get_coordinates() for {place_name} executed in {end_time - start_time} seconds")
        return max_importance_place['lat'], max_importance_place['lon']
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving coordinates: {e}")
        return None, None


# In[10]:


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
#         print(f"get_traffic_data() executed in {end_time - start_time} seconds")
        if average_congestion >= 0 and average_congestion < 40:
            return "Low"
        elif average_congestion >= 40 and average_congestion < 60:
            return "Medium"
        else:
            return "Heavy"    
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving coordinates: {e}")
        return None, None


# In[11]:


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
#         print(f"find_nearest_station() executed in {end_time - start_time} seconds")
        return nearest_station
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving coordinates: {e}")
        return None, None


# In[12]:


def calculate_distances(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Tuple[float, float]:
    start_time = time.time() 
    city_distance_m = 0
    highway_distance_m = 0
    highway_pattern = re.compile(r'\\b\[A,B,M\]\\d+')

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
#         print(f"calculate_distances() executed in {end_time - start_time} seconds")
        return city_distance_mi, highway_distance_mi

    except requests.exceptions.RequestException as e:
        print(f"Error calculating distances: {e}")
        return 0.0, 0.0


# In[13]:


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
#             print(f"get_route_coordinates() executed in {end_time - start_time} seconds")
            return route_coordinates

        else:
            print("Error:", response.status_code)
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving route coordinates : {e}")
        return []


# In[14]:


import requests
from typing import List, Tuple
from datetime import datetime

WEATHER_API_URL = "http://api.weatherapi.com/v1/forecast.json"

def get_weather_data(api_key: str, coordinates_list: List[Tuple[float, float]], target_date: str) -> Tuple[float, str, str]:
    temperature_sum = 0
    snow_sum = 0
    rain_sum = 0
    visibility_sum = 0
    valid_coordinates = 0

    for idx, (lat, lon) in enumerate(coordinates_list, start=1):
        params = {
            "key": api_key,
            "q": f"{lon},{lat}",
            "days": 4,
            "aqi": "no",
            "alerts": "no"
        }

        try:
            response = requests.get(WEATHER_API_URL, params=params)
            response.raise_for_status()
            weather_data = response.json()

            forecast_days = weather_data.get('forecast', {}).get('forecastday', [])

            # Find the forecast data for the target date
            target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()

            for day in forecast_days:
                date_obj = datetime.strptime(day.get('date'), "%Y-%m-%d").date()

                if date_obj == target_date_obj:
                    day_data = day.get('day', {})
                    temperature = day_data.get('avgtemp_c', 0.0)
                    snow = day_data.get('totalsnow_cm', 0.0)
                    rain = sum(hour.get('precip_mm', 0.0) for hour in day.get('hour', []))
                    visibility = day_data.get('avgvis_km', 0.0)

                    temperature_sum += temperature
                    snow_sum += snow
                    rain_sum += rain
                    visibility_sum += visibility
                    valid_coordinates += 1

                    break  # Exit the loop after finding the target date

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

# Define encodings
vehicle_type_encoded = ['HVS HGV', 'HVS MCV', 'Hymax Series']
origin_encoded = {'Aberdeen': 0, 'Birmingham': 1, 'Cardiff': 2, 'Glasgow': 3,
                  'Leeds': 4, 'Liverpool': 5, 'London': 6, 'Manchester': 7}
nearest_station_encoded = {'AB12 3SH': 0, 'B25 8DW': 1, 'S60 5WG': 2, 'SN3 4QS': 3, 'TW6 2GE': 4}
dispatch_encoded = {'morning': 0, 'night': 1, 'noon': 2}
traffic_congestion_encoded = {'low': 0, 'medium': 1, 'high': 2}
rain_encoded = {'low': 0, 'medium': 1, 'high': 2}
snow_encoded = {'low': 0, 'medium': 1, 'high': 2}


def find_vehicle_type_range_and_capacity(total_payload):
    if total_payload <= 16:
        vehicle_type = input("Enter vehicle type (HVS HGV / HVS MCV / Hymax Series): ")
        if vehicle_type == 'HVS HGV':
            return vehicle_type, 300, 51
        elif vehicle_type == 'HVS MCV':
            return vehicle_type, 370, 51
        elif vehicle_type == 'Hymax Series':
            return vehicle_type, 422, 60
        else:
            raise ValueError("Invalid vehicle type: {}".format(vehicle_type))
    else:
        vehicle_type = input("Enter vehicle type (HVS HGV / Hymax Series): ")
        if vehicle_type == 'HVS HGV' or vehicle_type == 'Hymax Series':
            return vehicle_type, 300, 51 if vehicle_type == 'HVS HGV' else 60
        else:
            raise ValueError("Invalid vehicle type: {}".format(vehicle_type))


def get_raw_input(Origin_depot, Destination_depot, nearest_fuel_station, total_highway_distance,
                  total_city_distance, traffic_congestion_level, average_temperature, rain_classification,
                  snow_classification, pallets, Vehicle_age, Goods_weight, Avg_Speed_mph, dispatch_time, vehicle_type,
                  vehicle_range, Tank_capacity, total_payload):
    start_time = time.time()

    print(f"Avg_Temp: {average_temperature:.2f}")
    print(f"Avg_Precipitation:", rain_classification)
    print(f"Avg_snow:", snow_classification)
    print(f"Distance_highway: {total_highway_distance:.2f}")
    print(f"Distance_city: {total_city_distance:.2f}")
    print(f"Avg_traffic_congestion:", traffic_congestion_level)
    print(f"Nearest fuel station:", nearest_fuel_station)
#     print(f"Range of vehicle:", vehicle_range)
    print("Tank capacity of vehicle(kg):", Tank_capacity)

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
#     print(f"get_raw_input() executed in {end_time - start_time} seconds")

    return pd.DataFrame(input_data)


def convert_time_to_window(time_str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    if 4 <= hours < 12:
        return "morning"
    elif 12 <= hours < 20:
        return "noon"
    else:
        return "night"

hydrogen_bp = Blueprint('hydrogen', __name__)


@hydrogen_bp.route('/hydrogenanalytics', methods=['GET', 'POST'])
def hydrogenanalytics():
    try:
        # Get data from form
        station_postal_codes = ['AB12 3SH', 'S60 5WG', 'B25 8DW', 'SN3 4QS', 'TW6 2GE']
        pallets = float(request.form['pallets'])
        vehicle_type = request.form['vehicle_type']
        Origin_depot = request.form['start_place']
        Origin_depot_uk = f"{Origin_depot}, UK"
        Destination_depot = request.form['destination_place']
        Destination_depot_uk = f"{Destination_depot}, UK"
        Vehicle_age = float(request.form['vehicle_age'])
        time_str = request.form['dispatch_time']
        dispatch_time = convert_time_to_window(time_str)
        target_date = request.form['journey_date']
        fuel_origin = float(request.form['fuel_origin'])
        fuel_range1 = float(request.form['fuel_range1'])
        fuel_range2 = float(request.form['fuel_range2'])
        total_payload = pallets * 0.88
        if vehicle_type == 'HVS HGV':
            vehicle_range=300
            Tank_capacity = 51
        
        elif vehicle_type == 'HVS MCV':
            vehicle_range=370
            Tank_capacity = 51
        elif vehicle_type == 'Hymax Series':
            vehicle_range=422
            Tank_capacity = 60
        else:
            raise ValueError("Invalid vehicle type: {}".format(vehicle_type))
        Avg_Speed_mph = 80
        Goods_weight = total_payload

        print(Origin_depot)
        print(Destination_depot)

        # Get coordinates for start and destination places
        origin_coordinates = get_coordinates(Origin_depot_uk)
        destination_coordinates = get_coordinates(Destination_depot_uk)

        # Find nearest fuel station
        nearest_fuel_station = find_nearest_station(Origin_depot_uk, station_postal_codes, mapbox_token)
        fuel_station_coordinates = get_coordinates(nearest_fuel_station)

        # Calculate distances for city and highway
        origin_to_fuel_station = calculate_distances(origin_coordinates, fuel_station_coordinates)
        fuel_station_to_destination = calculate_distances(fuel_station_coordinates, destination_coordinates)
        total_city_distance = origin_to_fuel_station[0] + fuel_station_to_destination[0]
        total_highway_distance = origin_to_fuel_station[1] + fuel_station_to_destination[1]

        # Get traffic congestion level
        traffic_congestion_level = get_traffic_data(origin_coordinates, destination_coordinates, fuel_station_coordinates, mapbox_token)

        # Get coordinates along the route
        coordinates = get_route_coordinates(origin_coordinates, destination_coordinates)

        # Get average weather data for route coordinates
        average_temperature, snow_classification, rain_classification = get_weather_data(weather_api_key, coordinates, target_date)

        # Get input and make predictions
        raw_input_df = get_raw_input(Origin_depot, Destination_depot, nearest_fuel_station, total_highway_distance,
                                     total_city_distance, traffic_congestion_level, average_temperature,
                                     rain_classification, snow_classification, pallets, Vehicle_age, Goods_weight,
                                     Avg_Speed_mph, dispatch_time, vehicle_type, vehicle_range, Tank_capacity, total_payload)
        prediction = model.predict(raw_input_df)
        efficiency_prediction = prediction[0]

        Total_dist = total_city_distance + total_highway_distance
        Total_Required_Fuel = Total_dist / efficiency_prediction
        Total_cost_hydrogen = Total_Required_Fuel * 12
        total_cost =  Total_cost_hydrogen+(Total_cost_hydrogen*0.1)
        Cost_per_mile = Total_cost_hydrogen / Total_dist
        overhead_cost = Total_cost_hydrogen * 0.1
        total_final_cost = Total_cost_hydrogen + overhead_cost

        # Feature importance
        feature_importance = model.feature_importances_
        sorted_idx = np.argsort(feature_importance)[::-1]  # Sort in descending order

        # Get the indices of the top 8 features
        top_8_idx = sorted_idx[:8]

        # generating the random values 
        good_value_fuel = random.uniform(1.0, total_cost)
        insurance_fuel_cost = random.uniform(1.0, good_value_fuel) 
        goods_loading_time = random_time = random.randint(10, 60)
        is_goods_secured = random.choice(['✔️', '❌'])
        check_safety = random.choice(['✔️', '❌'])

    

        fig = plt.figure(figsize=(12, 6))
        ax = fig.add_subplot()

        # Set a dark navy blue background for the figure and plot area
        fig.patch.set_facecolor('#000128')  # Dark navy color
        ax.set_facecolor('#000128')         # Dark navy color

        # Create the horizontal bar plot with white bars
        ax.barh(range(len(top_8_idx)), feature_importance[top_8_idx], align='center', color='white')
        ax.set_yticks(range(len(top_8_idx)))
        ax.set_yticklabels(np.array(raw_input_df.columns)[top_8_idx], color='white')
        ax.set_title('Top 8 Features by Importance', color='white')
        ax.set_xlabel('Feature Importance', color='white')

        # Change tick label colors to white for visibility
        ax.tick_params(axis='y', colors='white')
        ax.tick_params(axis='x', colors='white')

        plt.tight_layout()
        plt.savefig('static/feature_importance_h.png')


        model_data = {
            'total_dist': [Total_dist],
            'vehicle_age': [Vehicle_age],
            'goods_weight': [Goods_weight],
            'city_distance': [total_city_distance],
            'highway_distance': [total_highway_distance],
            'avg_speed_mph': [65],  # You may need to update this value based on your logic
            "average_temperature": [average_temperature],
            'rain_classification': [rain_classification],
            'snow_classification': [snow_classification],
            'traffic_severity': [traffic_congestion_level],
            'start_place': [Origin_depot],
            'destination_place': [Destination_depot],
            'vehicle_type': [vehicle_type],
            'fuel_price_per_kilogram': [12],
            'total_fuel_cost': [Total_cost_hydrogen],
            'efficiency_prediction': [efficiency_prediction],
            'total_required_fuel':[Total_Required_Fuel],
            'total_cost':[total_cost],
            'cost_per_mile':[Cost_per_mile],
            'good_value_fuel':[good_value_fuel],
            'insurance_fuel_cost': [insurance_fuel_cost],
            'goods_loading_time':[goods_loading_time],
            'is_goods_secured':[is_goods_secured],
            'check_safety':[check_safety]


        }
        
        # Create a DataFrame with the specified column names
        csv_columns = ['total_dist', 'vehicle_age', 'goods_weight', 'city_distance', 'highway_distance',
                       'avg_speed_mph', 'rain_classification', 'snow_classification', 'traffic_severity',
                       'start_place', 'destination_place', 'vehicle_type', 'fuel_price_per_kilogram','average_temperature',
                       'total_fuel_cost', 'efficiency_prediction','insurance_fuel_cost','good_value_fuel','cost_per_mile','total_cost','total_required_fuel',
                       'goods_loading_time','is_goods_secured','check_safety']
        df = pd.DataFrame(model_data, columns=csv_columns)
        
        # Save the DataFrame to a CSV file
        csv_filename = 'Hydrogen_Model_Data.csv'
        df.to_csv(csv_filename)
        print(f"Data appended to {csv_filename}")
        # pd.to_csv(csv_columns.csv)
        hydrogen_data = {
            "average_temperature": f"{average_temperature:.2f}",
            "rain_classification": rain_classification,
            "snow_classification": snow_classification,
            "highway_distance": f"{total_highway_distance:.2f}",
            "city_distance": f"{total_city_distance:.2f}",
            "efficiency_prediction": f"{efficiency_prediction:.2f}",
            "total_required_fuel": f"{Total_Required_Fuel:.2f}",
            "total_fuel_cost": f"{Total_cost_hydrogen:.2f}",
            "total_cost": f"{total_cost:.2f}",
            "cost_per_mile": f"{Cost_per_mile:.2f}",
            "overhead_cost": f"{total_cost * 0.1:.2f}",
            "total_final_cost": f"{total_cost + (total_cost * 0.1):.2f}",
            "feature_importance": 'static/feature_importance_h.png',
            "fuel_price": f"{total_cost:.2f}",
            "good_value_fuel": f"{good_value_fuel:.2f}",
            "insurance_fuel_cost": f"{insurance_fuel_cost:.2f}",
            "goods_loading_time": goods_loading_time,
            "is_goods_secured": is_goods_secured,
            "check_safety": check_safety
        }

        #passing data for map
        getdatah(Origin_depot,Destination_depot,Total_Required_Fuel,efficiency_prediction,fuel_origin,fuel_range1,fuel_range2)

        return render_template("hydrogenanalytics.html", **hydrogen_data)
       

    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return "Error in processing the request. Please try again."

    except Exception as e:
        print("Error:", e)
        return "An unexpected error occurred. Please try again."

    return render_template("hydrogen.html")

  