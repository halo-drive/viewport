from flask import Blueprint, render_template, request, Response, jsonify, flash, session, redirect, url_for
import json
import random
import os
import time
import joblib
import requests
import pandas as pd
import re
from typing import Tuple, List
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
from diesel_routing_here import getdata
from config import Config


# Load the model
model = joblib.load('Fossil_model.pkl')

# URLs for the APIs
GEOCODING_API_URL = "https://geocode.maps.co/search"
MAPBOX_DIRECTIONS_API_URL = "https://api.mapbox.com/directions/v5/mapbox/driving-traffic/"
WEATHER_API_URL = "http://api.weatherapi.com/v1/forecast.json"

# API tokens from config
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
        max_importance_place = max(data, key=lambda place: place['importance'])
        
        coords = (max_importance_place['lat'], max_importance_place['lon'])
        return coords
    
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving coordinates: {e}")
        return None, None


def calculate_distances(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Tuple[float, float]:
    city_distance_m = 0
    highway_distance_m = 0
    highway_pattern = re.compile(r'\\b\[A,B,M\]\\d+')

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
        return city_distance_mi, highway_distance_mi

    except requests.exceptions.RequestException as e:
        print(f"Error calculating distances: {e}")
        return 0.0, 0.0


def get_route_traffic_data(start_coords: Tuple[float, float], end_coords: Tuple[float, float]) -> Tuple[List[Tuple[float, float]], float]:
    traffic_delay = 0
    coordinates_list = []

    params = {
        "access_token": MAPBOX_ACCESS_TOKEN,
        "geometries": "geojson",
        "steps": "true"
    }

    start_lat, start_lon = start_coords
    end_lat, end_lon = end_coords
    url = f"{MAPBOX_DIRECTIONS_API_URL}{start_lon}%2C{start_lat}%3B{end_lon}%2C{end_lat}"

    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()

            # Extract start and destination coordinates
            start_coordinate = data["routes"][0]["legs"][0]["steps"][0]["geometry"]["coordinates"][0]
            destination_coordinate = data["routes"][0]["legs"][0]["steps"][-1]["geometry"]["coordinates"][-1]

            # Initialize variables for accumulated distance and coordinates
            accumulated_distance = 0
            coordinate = None
            extracted_coordinates = []

            for route in data["routes"]:
                for leg in route["legs"]:
                    for step in leg["steps"]:
                        distance_m = step["distance"]
                        if "distance" in step:
                            accumulated_distance += distance_m
                        if "geometry" in step and "coordinates" in step["geometry"]:
                            step_coordinates = step["geometry"]["coordinates"]
                        if coordinate is None:
                             coordinate = step_coordinates[0]

                        # Check if accumulated distance exceeds 10,000 meters
                        if accumulated_distance >= 0:
                            extracted_coordinates.append(coordinate)
                            coordinate = None
                            accumulated_distance = 0

            typical_duration = data['routes'][0]['duration_typical']
            actual_duration = data['routes'][0]['duration']

            # Calculate traffic delay in minutes
            if typical_duration is not None and actual_duration is not None:
                traffic_delay = abs(typical_duration - actual_duration) / 60
            else:
                traffic_delay = 0  # Default value if missing data

            return extracted_coordinates, traffic_delay

        else:
            print("Error:", response.status_code)
            return [], 0.0

    except requests.exceptions.RequestException as e:
        print(f"Error retrieving route traffic data: {e}")
        return [], 0.0


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

# Get fuel price data
url = "https://fuel.motorfuelgroup.com/fuel_prices_data.json"
try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
except:
    data = None

# Function to get average diesel price for a specific city
def get_average_diesel_price_by_city(data, city):
    if not data:
        return 175.9  # Default value if API fails
    
    city = city.upper()
    prices = []

    for station in data["stations"]:
        address = station["address"].upper()
        if city in address:
            price = station["prices"].get("B7")  # Assuming "B7" represents diesel fuel
            if price:
                prices.append(price)

    if prices:
        return sum(prices) / len(prices)
    else:
        return 175.9  # Default value if no prices found

# Encodings for the model
vehicle_type_encoded = ['DAF XF 105.510', 'DAF XG 530', 'IVECO EuroCargo ml180e28',
        'IVECO NP 460', 'MAN TGM 18.250', 'MAN TGX 18.400', 'SCANIA G 460',
        'SCANIA R 450', 'VOLVO FH 520', 'VOLVO FL 420']
origin_encoded = {'Aberdeen': 0, 'Birmingham': 1, 'Cardiff': 2, 'Glasgow': 3,
                  'Leeds': 4, 'Liverpool': 5, 'London': 6, 'Manchester': 7}
dispatch_encoded = {'morning': 0, 'night': 1, 'noon': 2}
traffic_congestion_encoded = {'low': 0, 'medium': 1, 'high': 2}
temp_encoded = {'low': 0, 'medium': 1, 'high': 2}
precipitation_encoded = {'low': 0, 'medium': 1, 'high': 2}
snow_encoded = {'low': 0, 'medium': 1, 'high': 2}

tracking_bp = Blueprint('tracking', __name__)

@tracking_bp.route('/hydrogen')
def hydrogen():
    return render_template('hydrogen.html')

# Convert dispatch time string to window
def convert_time_to_window(time_str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    if 4 <= hours < 12:
        return "morning"
    elif 12 <= hours < 20:
        return "noon"
    else:
        return "night"

@tracking_bp.route('/diesel', methods=['GET', 'POST'])
def main():
    if request.method == 'POST':
        pallets = float(request.form['pallets'])
        vehicle_type = request.form['vehicle_type']
        start_place = request.form['start_place'] + ", UK"
        destination_place = request.form['destination_place'] + ", UK"
        vehicle_age = float(request.form['vehicle_age'])
        time_str = request.form['dispatch_time']
        dispatch_time = convert_time_to_window(time_str)
        target_date = request.form['journey_date']
        total_payload = pallets * 0.88
        goods_weight = total_payload
        
        try:
            start_coords = get_coordinates(start_place)
            destination_coords = get_coordinates(destination_place)
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return render_template("error.html", message="Error getting coordinates.")
        
        try:
            city_distance, highway_distance = calculate_distances(start_coords, destination_coords)
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return render_template("error.html", message="Error calculating distances.")
        
        try:
            route_coordinates, traffic_delay = get_route_traffic_data(start_coords, destination_coords)
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return render_template("error.html", message="Error getting route traffic data.")
        
        api_key = Config.WEATHER_API_KEY
        try:
            average_temperature, snow_classification, rain_classification = get_weather_data(api_key, route_coordinates, target_date)
        except requests.exceptions.RequestException as e:
            print("Error:", e)
            return render_template("error.html", message="Error getting weather data.")
        
        traffic_severity = "high" if traffic_delay > 30 else "medium" if traffic_delay > 7 else "low"

        def get_raw_input(start_place, destination_place, highway_distance, city_distance, traffic_severity,
                          average_temperature, rain_classification, snow_classification, vehicle_type):
            
            origin_depot = start_place.split(',')[0].strip()
            destination_depot = destination_place.split(',')[0].strip()
            avg_speed_mph = 65

            # Encode categorical variables
            encoded_origin = origin_encoded.get(origin_depot, -1)
            encoded_destination = origin_encoded.get(destination_depot, -1)
            encoded_dispatch_time = dispatch_encoded.get(dispatch_time, -1)
            encoded_avg_traffic_congestion = traffic_congestion_encoded.get(traffic_severity, -1)
            encoded_avg_temp = temp_encoded.get("medium", -1)  # Default to medium
            encoded_avg_precipitation = precipitation_encoded.get(rain_classification.lower(), -1)
            encoded_avg_snow = snow_encoded.get(snow_classification.lower(), -1)
            dummy_variables = {vehicle: (1 if vehicle == vehicle_type else 0) for vehicle in vehicle_type_encoded}
            
            input_data = {
                "Vehicle_age": [vehicle_age],
                "Goods_weight": [goods_weight],
                "Total_distance_miles": [city_distance + highway_distance],
                "Avg_traffic_congestion": [encoded_avg_traffic_congestion],
                "Avg_temp": [encoded_avg_temp],
                "Avg_Precipitation": [encoded_avg_precipitation],
                "Avg_snow": [encoded_avg_snow],
                "Origin_depot": [encoded_origin],
                "Destination_depot": [encoded_destination],
                "Avg_Speed_mph": [avg_speed_mph],
                "Distance_highway": [highway_distance],
                "Distance_city": [city_distance],
                "dispatch_time": [encoded_dispatch_time],
                "total_payload": [total_payload]
            }

            input_data.update(dummy_variables)

            return pd.DataFrame(input_data)

        
        raw_input_df = get_raw_input(start_place, destination_place, highway_distance, city_distance, traffic_severity,
                                     average_temperature, rain_classification, snow_classification, vehicle_type)
        
        prediction = model.predict(raw_input_df)
        efficiency_prediction = prediction[0]
        
        total_dist = city_distance + highway_distance
        total_required_fuel = total_dist / efficiency_prediction
        
        city = start_place.split(',')[0].strip()
        fuel_price = get_average_diesel_price_by_city(data, city)
        fuel_price_per_liter = fuel_price / 100
        fuel_price_per_gallon = fuel_price_per_liter * 4.54
        
        total_fuel_cost = total_required_fuel * fuel_price_per_gallon
        cost_per_mile = total_fuel_cost / total_dist
        total_cost = total_fuel_cost + (total_fuel_cost * 0.1)

        # Feature importance
        feature_importance = model.feature_importances_
        sorted_idx = np.argsort(feature_importance)[::-1]  # Sort in descending order

        # Get the indices of the top 8 features
        top_8_idx = sorted_idx[:8]

        # Generate random values 
        good_value_fuel = random.uniform(1.0, fuel_price)
        insurance_fuel_cost = random.uniform(1.0, good_value_fuel) 
        goods_loading_time = random.randint(10, 60)
        is_goods_secured = random.choice(['✔️', '❌'])
        check_safety = random.choice(['✔️', '❌'])

        # Create visualization
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
        plt.savefig('static/feature_importance_d.png')

        model_data = {
            'total_dist': [total_dist],
            'vehicle_age': [vehicle_age],
            'goods_weight': [goods_weight],
            'city_distance': [city_distance],
            'highway_distance': [highway_distance],
            'average_temperature': [average_temperature],
            'avg_speed_mph': [65],
            'rain_classification': [rain_classification],
            'snow_classification': [snow_classification],
            'traffic_severity': [traffic_severity],
            'start_place': [start_place],
            'destination_place': [destination_place],
            'vehicle_type': [vehicle_type],
            'fuel_price_per_gallon': [fuel_price_per_gallon],
            'total_fuel_cost': [total_fuel_cost],
            'total_required_fuel':[total_required_fuel],
            'efficiency_prediction': [efficiency_prediction],
            'total_cost':[total_cost],
            'cost_per_mile':[cost_per_mile],
            'fuel_price':[fuel_price],
            'good_value_fuel':[good_value_fuel],
            'insurance_fuel_cost':[insurance_fuel_cost],
            'goods_loading_time':[goods_loading_time],
            'is_goods_secured':[is_goods_secured],
            'check_safety':[check_safety]
        }
        
        # Create a DataFrame with the specified column names
        csv_columns = ['total_dist', 'vehicle_age', 'goods_weight', 'city_distance', 'highway_distance','average_temperature',
                      'avg_speed_mph', 'rain_classification', 'snow_classification', 'traffic_severity',
                      'start_place', 'destination_place', 'vehicle_type', 'fuel_price_per_gallon','total_required_fuel',
                      'total_fuel_cost', 'efficiency_prediction','total_cost','cost_per_mile','fuel_price','good_value_fuel','insurance_fuel_cost',
                      'goods_loading_time','is_goods_secured','check_safety']
        df = pd.DataFrame(model_data, columns=csv_columns)
        
        # Save the DataFrame to a CSV file
        csv_filename = 'Diesel_Model_Data.csv'
        df.to_csv(csv_filename)
        
        diesel_data = {
            "average_temperature": f"{average_temperature:.2f}",
            "rain_classification": rain_classification,
            "snow_classification": snow_classification,
            "highway_distance": f"{highway_distance:.2f}",
            "city_distance": f"{city_distance:.2f}",
            "efficiency_prediction": f"{efficiency_prediction:.2f}",
            "total_required_fuel": f"{total_required_fuel:.2f}",
            "total_fuel_cost": f"{total_fuel_cost:.2f}",
            "total_cost": f"{total_cost:.2f}",
            "cost_per_mile": f"{cost_per_mile:.2f}",
            "overhead_cost": f"{total_cost * 0.1:.2f}",
            "total_final_cost": f"{total_cost + (total_cost * 0.1):.2f}",
            "feature_importance": 'static/feature_importance_d.png',
            "fuel_price": f"{fuel_price:.2f}",
            "good_value_fuel": f"{good_value_fuel:.2f}",
            "insurance_fuel_cost": f"{insurance_fuel_cost:.2f}",
            "goods_loading_time": goods_loading_time,
            "is_goods_secured": is_goods_secured,
            "check_safety": check_safety
        }
        
        # Pass data to diesel map
        getdata(start_place, destination_place)

        return render_template("dieselanalytics.html", **diesel_data)
    
    return render_template("diesel.html")