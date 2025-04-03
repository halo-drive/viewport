from flask import Blueprint, request, jsonify
from tracking import get_coordinates, calculate_distances, get_route_traffic_data, get_weather_data
from diesel_routing_here import get_here_directions, get_coordinates as here_get_coordinates, get_fuel_station_coordinates, get_route_with_fuel_stations
import joblib
import pandas as pd
import numpy as np
import random
import requests
from config import Config

# Load the model
model = joblib.load('Fossil_model.pkl')

# URL of the fuel prices API
url = "https://fuel.motorfuelgroup.com/fuel_prices_data.json"
try:
    response = requests.get(url)
    if response.status_code == 200:
        fuel_data = response.json()
except:
    fuel_data = None

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

# Initialize the blueprint
diesel_api_bp = Blueprint('diesel_api', __name__)

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

def convert_time_to_window(time_str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    if 4 <= hours < 12:
        return "morning"
    elif 12 <= hours < 20:
        return "noon"
    else:
        return "night"

@diesel_api_bp.route('/api/diesel/route', methods=['POST'])
def diesel_route_api():
    try:
        # Get form data
        pallets = float(request.form['pallets'])
        vehicle_type = request.form['vehicleModel']
        origin_depot = request.form['originDepot']
        destination_depot = request.form['destinationDepot']
        vehicle_age = float(request.form['vehicleAge'])
        dispatch_time = convert_time_to_window(request.form['dispatchTime'])
        target_date = request.form['journeyDate']
        
        start_place = f"{origin_depot}, UK"
        destination_place = f"{destination_depot}, UK"
        total_payload = pallets * 0.88
        goods_weight = total_payload
        
        # Get coordinates and route with fuel stations
        api_key = Config.HERE_API_KEY
        route_coords, route_points, fuel_station_coords = get_route_with_fuel_stations(
            api_key, origin_city=start_place, destination_city=destination_place
        )
        
        # Format stations for response
        station_points = []
        for i, fuel_coord in enumerate(fuel_station_coords):
            station_points.append({
                "name": f"Fuel Station {i+1}",
                "coordinates": fuel_coord
            })

        # Create combined route that passes through stations
        combined_route_points = []
        if len(fuel_station_coords) > 0:
            # Get origin and destination coordinates
            start_coords_here = here_get_coordinates(start_place, api_key)
            dest_coords_here = here_get_coordinates(destination_place, api_key)
            
            # Start with origin to first station
            first_station = fuel_station_coords[0]
            origin_to_first = get_here_directions(
                f"{start_coords_here[0]},{start_coords_here[1]}", 
                f"{first_station[0]},{first_station[1]}", 
                api_key
            )
            if origin_to_first:
                combined_route_points.extend(origin_to_first)
            
            # Add routes between stations
            for i in range(len(fuel_station_coords) - 1):
                current = fuel_station_coords[i]
                next_station = fuel_station_coords[i+1]
                station_to_station = get_here_directions(
                    f"{current[0]},{current[1]}",
                    f"{next_station[0]},{next_station[1]}",
                    api_key
                )
                if station_to_station:
                    combined_route_points.extend(station_to_station)
            
            # Add last station to destination
            last_station = fuel_station_coords[-1]
            last_to_dest = get_here_directions(
                f"{last_station[0]},{last_station[1]}",
                f"{dest_coords_here[0]},{dest_coords_here[1]}",
                api_key
            )
            if last_to_dest:
                combined_route_points.extend(last_to_dest)
            
            # Use the combined route if we have one
            if combined_route_points:
                route_points = combined_route_points
        
        # Get coordinates for other calculations
        start_coords = get_coordinates(start_place)
        destination_coords = get_coordinates(destination_place)
        
        # Calculate distances
        city_distance, highway_distance = calculate_distances(start_coords, destination_coords)
        
        # Get route traffic data
        route_coordinates, traffic_delay = get_route_traffic_data(start_coords, destination_coords)
        
        # Define traffic severity
        traffic_severity = "high" if traffic_delay > 30 else "medium" if traffic_delay > 7 else "low"
        
        # Get weather data
        weather_api_key = Config.WEATHER_API_KEY
        average_temperature, snow_classification, rain_classification = get_weather_data(weather_api_key, route_coordinates, target_date)
        
        # Prepare data for prediction
        def get_raw_input(start_place, destination_place, highway_distance, city_distance, traffic_severity,
                          average_temperature, rain_classification, snow_classification, vehicle_type):
            
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
                "Avg_Speed_mph": [65],
                "Distance_highway": [highway_distance],
                "Distance_city": [city_distance],
                "dispatch_time": [encoded_dispatch_time],
                "total_payload": [total_payload]
            }

            input_data.update(dummy_variables)
            return pd.DataFrame(input_data)
        
        # Get prediction
        raw_input_df = get_raw_input(start_place, destination_place, highway_distance, city_distance, traffic_severity,
                                     average_temperature, rain_classification, snow_classification, vehicle_type)
        
        try:
            prediction = model.predict(raw_input_df)
        except AttributeError as e:
            if "'super' object has no attribute 'get_params'" in str(e):
                # Workaround for the get_params error
                prediction = model._Booster.predict(raw_input_df)
            else:
                raise
                
        efficiency_prediction = prediction[0]
        
        # Calculate fuel metrics
        total_dist = city_distance + highway_distance
        total_required_fuel = total_dist / efficiency_prediction
        
        city = origin_depot
        fuel_price = get_average_diesel_price_by_city(fuel_data, city)
        fuel_price_per_liter = fuel_price / 100
        fuel_price_per_gallon = fuel_price_per_liter * 4.54
        
        total_fuel_cost = total_required_fuel * fuel_price_per_gallon
        cost_per_mile = total_fuel_cost / total_dist
        total_cost = total_fuel_cost + (total_fuel_cost * 0.1)
        
        # Feature importance (we're not sending the image)
        feature_importance = model.feature_importances_
        sorted_idx = np.argsort(feature_importance)[::-1]
        top_8_idx = sorted_idx[:8]
        
        # Format the feature importance data
        feature_names = list(raw_input_df.columns)
        top_feature_names = [feature_names[i] for i in top_8_idx]
        top_feature_values = [float(feature_importance[i]) for i in top_8_idx]

        # Log model inputs and prediction to terminal
        print("\n\n===== DIESEL MODEL PREDICTION =====")
        print("INPUT DATA:")
        for key in raw_input_df.columns:
            print(f"  {key}: {raw_input_df[key].values[0]}")
        print(f"\nEFFICIENCY PREDICTION: {efficiency_prediction:.4f} mpg")
        print("====================================\n")

        # Log feature importance for debugging
        print("\n===== DIESEL TOP 8 FEATURES =====")
        for i, (name, value) in enumerate(zip(top_feature_names, top_feature_values)):
            print(f"{i+1}. {name}: {value:.4f}")
        print("=================================\n")

        feature_importance_data = []
        for name, value in zip(top_feature_names, top_feature_values):
            feature_importance_data.append({
                "name": name,
                "value": value  # No scaling
            })

        # Random values for other metrics
        good_value_fuel = random.uniform(1.0, fuel_price)
        insurance_fuel_cost = random.uniform(1.0, good_value_fuel) 
        goods_loading_time = random.randint(10, 60)
        is_goods_secured = random.choice(['✔️', '❌'])
        check_safety = random.choice(['✔️', '❌'])
        
        # Prepare response
        response = {
            "success": True,
            "route": {
                "origin": origin_depot,
                "destination": destination_depot,
                "coordinates": route_points,
                "stations": station_points,
                "total_distance": total_dist
            },
            "analytics": {
                "average_temperature": round(average_temperature, 2),
                "rain_classification": rain_classification,
                "snow_classification": snow_classification,
                "highway_distance": round(highway_distance, 2),
                "city_distance": round(city_distance, 2),
                "efficiency_prediction": round(efficiency_prediction, 2),
                "total_required_fuel": round(total_required_fuel, 2),
                "total_fuel_cost": round(total_fuel_cost, 2),
                "total_cost": round(total_cost, 2),
                "cost_per_mile": round(cost_per_mile, 2),
                "overhead_cost": round(total_cost * 0.1, 2),
                "total_final_cost": round(total_cost + (total_cost * 0.1), 2),
                "fuel_price": round(fuel_price, 2),
                "good_value_fuel": round(good_value_fuel, 2),
                "insurance_fuel_cost": round(insurance_fuel_cost, 2),
                "goods_loading_time": goods_loading_time,
                "is_goods_secured": is_goods_secured,
                "check_safety": check_safety,
                "featureImportance": feature_importance_data
            }
        }
        
        return jsonify(response)
    
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in diesel route API: {str(e)}")
        print(f"Traceback: {error_traceback}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_traceback
        }), 500