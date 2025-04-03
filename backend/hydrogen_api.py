from flask import Blueprint, request, jsonify
from hydrogen import get_coordinates, find_nearest_station, calculate_distances, get_traffic_data, get_route_coordinates, get_weather_data
from hydrogen_here_map import get_here_directions, get_coordinates as here_get_coordinates, find_nearest_stations
import joblib
import pandas as pd
import numpy as np
import random
from config import Config

# Load the model
model = joblib.load('Hydrogen_model.pkl')

# Initialize the blueprint
hydrogen_api_bp = Blueprint('hydrogen_api', __name__)

# Encodings for the model
vehicle_type_encoded = ['HVS HGV', 'HVS MCV', 'Hymax Series']
origin_encoded = {'Aberdeen': 0, 'Birmingham': 1, 'Cardiff': 2, 'Glasgow': 3,
                  'Leeds': 4, 'Liverpool': 5, 'London': 6, 'Manchester': 7}
nearest_station_encoded = {'AB12 3SH': 0, 'B25 8DW': 1, 'S60 5WG': 2, 'SN3 4QS': 3, 'TW6 2GE': 4}
dispatch_encoded = {'morning': 0, 'night': 1, 'noon': 2}
traffic_congestion_encoded = {'low': 0, 'medium': 1, 'high': 2}
rain_encoded = {'low': 0, 'medium': 1, 'high': 2}
snow_encoded = {'low': 0, 'medium': 1, 'high': 2}

def convert_time_to_window(time_str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    if 4 <= hours < 12:
        return "morning"
    elif 12 <= hours < 20:
        return "noon"
    else:
        return "night"

@hydrogen_api_bp.route('/api/hydrogen/route', methods=['POST'])
def hydrogen_route_api():
    try:
        # Get form data
        station_postal_codes = ['AB12 3SH', 'S60 5WG', 'B25 8DW', 'SN3 4QS', 'TW6 2GE']
        pallets = float(request.form['pallets'])
        vehicle_type = request.form['vehicleModel']
        origin_depot = request.form['originDepot']
        destination_depot = request.form['destinationDepot']
        vehicle_age = float(request.form['vehicleAge'])
        dispatch_time = convert_time_to_window(request.form['dispatchTime'])
        target_date = request.form['journeyDate']
        fuel_origin = float(request.form.get('fuelAtOrigin', 0))
        fuel_range1 = float(request.form.get('fuelStation1', 30))  # Default to 30 if not provided
        fuel_range2 = float(request.form.get('fuelStation2', 80))  # Default to 80 if not provided
        
        total_payload = pallets * 0.88
        
        if vehicle_type == 'HVS HGV':
            vehicle_range = 300
            Tank_capacity = 51
        elif vehicle_type == 'HVS MCV':
            vehicle_range = 370
            Tank_capacity = 51
        elif vehicle_type == 'Hymax Series':
            vehicle_range = 422
            Tank_capacity = 60
        else:
            vehicle_range = 300
            Tank_capacity = 51
            
        Avg_Speed_mph = 80
        Goods_weight = total_payload
        
        # Get coordinates for UK cities
        origin_uk = f"{origin_depot}, UK"
        destination_uk = f"{destination_depot}, UK"
        
        # Get coordinates for start and destination places
        origin_coordinates = get_coordinates(origin_uk)
        destination_coordinates = get_coordinates(destination_uk)
        
        # Find nearest fuel station
        mapbox_token = Config.MAPBOX_TOKEN
        nearest_fuel_station = find_nearest_station(origin_uk, station_postal_codes, mapbox_token)
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
        
        # Get weather data
        weather_api_key = Config.WEATHER_API_KEY
        average_temperature, snow_classification, rain_classification = get_weather_data(weather_api_key, coordinates, target_date)
        
        # Prepare input data for prediction
        def get_raw_input(Origin_depot, Destination_depot, nearest_fuel_station, total_highway_distance,
                      total_city_distance, traffic_congestion_level, average_temperature,
                      rain_classification, snow_classification, pallets, Vehicle_age, Goods_weight,
                      Avg_Speed_mph, dispatch_time, vehicle_type, vehicle_range, Tank_capacity, total_payload):
            
            # Encode categorical variables
            encoded_origin = origin_encoded.get(Origin_depot, -1)
            encoded_destination = origin_encoded.get(Destination_depot, -1)
            encoded_dispatch_time = dispatch_encoded.get(dispatch_time, -1)
            encoded_nearest_station = nearest_station_encoded.get(nearest_fuel_station, -1)
            # Encode traffic congestion, temperature, precipitation, and snow
            encoded_avg_traffic_congestion = traffic_congestion_encoded.get(traffic_congestion_level.lower(), -1)
            encoded_avg_rain = rain_encoded.get(rain_classification.lower(), -1)
            encoded_avg_snow = snow_encoded.get(snow_classification.lower(), -1)
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
            return pd.DataFrame(input_data)
        
        # Get prediction
        raw_input_df = get_raw_input(origin_depot, destination_depot, nearest_fuel_station, total_highway_distance,
                                 total_city_distance, traffic_congestion_level, average_temperature,
                                 rain_classification, snow_classification, pallets, vehicle_age, Goods_weight,
                                 Avg_Speed_mph, dispatch_time, vehicle_type, vehicle_range, Tank_capacity, total_payload)
        
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
        Total_dist = total_city_distance + total_highway_distance
        Total_Required_Fuel = Total_dist / efficiency_prediction
        Total_cost_hydrogen = Total_Required_Fuel * 12
        Cost_per_mile = Total_cost_hydrogen / Total_dist
        overhead_cost = Total_cost_hydrogen * 0.1
        total_cost = Total_cost_hydrogen + overhead_cost
        
        # Get coordinates for HERE Maps API
        here_api_key = Config.HERE_API_KEY
        origin_coords_here = here_get_coordinates(origin_depot)
        dest_coords_here = here_get_coordinates(destination_depot)
        
        route_points = []
        station_points = []
        
        # Check if vehicle has enough range to complete journey without refueling
        # Use the exact same condition as the original backend
        if fuel_origin > Total_Required_Fuel:
            # Vehicle has enough fuel to complete journey without stopping
            # Get direct route without stations
            direct_route = get_here_directions(origin_coords_here, dest_coords_here, here_api_key)
            if direct_route:
                route_points = direct_route
                # Important: Set station_points to empty list to ensure no stations are displayed
                station_points = []
        else:
            # Need fuel stations - proceed with station search logic
            station_cities = ['Aberdeen', 'Birmingham', 'Cardiff', 'Glasgow', 'Leeds', 'Manchester', 'Liverpool', 'London']
            nearest_stations = find_nearest_stations(origin_depot, station_cities, destination_depot)
            
            if nearest_stations and len(nearest_stations) > 0:
                # Get route with fuel stations
                if len(nearest_stations) == 1:
                    station_name = nearest_stations[0][0]
                    station_coords = here_get_coordinates(station_name)
                    
                    # Calculate route segments through the station
                    origin_to_station = get_here_directions(origin_coords_here, station_coords, here_api_key)
                    station_to_dest = get_here_directions(station_coords, dest_coords_here, here_api_key)
                    
                    if origin_to_station and station_to_dest:
                        # Combine routes to create a path that goes through the station
                        route_points = origin_to_station + station_to_dest
                        station_points = [{"name": station_name, "coordinates": station_coords}]
                elif len(nearest_stations) > 1:
                    station1_name = nearest_stations[0][0]
                    station2_name = nearest_stations[1][0]
                    
                    station1_coords = here_get_coordinates(station1_name)
                    station2_coords = here_get_coordinates(station2_name)
                    
                    # Calculate route segments through both stations
                    origin_to_station1 = get_here_directions(origin_coords_here, station1_coords, here_api_key)
                    station1_to_station2 = get_here_directions(station1_coords, station2_coords, here_api_key)
                    station2_to_dest = get_here_directions(station2_coords, dest_coords_here, here_api_key)
                    
                    if origin_to_station1 and station1_to_station2 and station2_to_dest:
                        # Combine routes to create a path that goes through both stations
                        route_points = origin_to_station1 + station1_to_station2 + station2_to_dest
                        station_points = [
                            {"name": station1_name, "coordinates": station1_coords},
                            {"name": station2_name, "coordinates": station2_coords}
                        ]
            
            # If no stations found or routes with stations failed, get direct route
            if not route_points:
                direct_route = get_here_directions(origin_coords_here, dest_coords_here, here_api_key)
                if direct_route:
                    route_points = direct_route
        
        # Feature importance (we're not sending the image)
        feature_importance = model.feature_importances_
        sorted_idx = np.argsort(feature_importance)[::-1]
        top_8_idx = sorted_idx[:8]
        
        # Format the feature importance data
        feature_names = list(raw_input_df.columns)
        top_feature_names = [feature_names[i] for i in top_8_idx]
        top_feature_values = [float(feature_importance[i]) for i in top_8_idx]

        # Log model inputs and prediction to terminal
        print("\n\n===== HYDROGEN MODEL PREDICTION =====")
        print("INPUT DATA:")
        for key in raw_input_df.columns:
            print(f"  {key}: {raw_input_df[key].values[0]}")
        print(f"\nEFFICIENCY PREDICTION: {efficiency_prediction:.4f} miles/kg")
        print("========================================\n")

        # Log feature importance for debugging
        print("\n===== HYDROGEN TOP 8 FEATURES =====")
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
        good_value_fuel = random.uniform(1.0, total_cost)
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
                "total_distance": Total_dist
            },
            "analytics": {
                "average_temperature": round(average_temperature, 2),
                "rain_classification": rain_classification,
                "snow_classification": snow_classification,
                "highway_distance": round(total_highway_distance, 2),
                "city_distance": round(total_city_distance, 2),
                "efficiency_prediction": round(efficiency_prediction, 2),
                "total_required_fuel": round(Total_Required_Fuel, 2),
                "total_fuel_cost": round(Total_cost_hydrogen, 2),
                "total_cost": round(total_cost, 2),
                "cost_per_mile": round(Cost_per_mile, 2),
                "overhead_cost": round(overhead_cost, 2),
                "total_final_cost": round(total_cost, 2),
                "fuel_price": round(total_cost, 2),
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
        print(f"Error in hydrogen route API: {str(e)}")
        print(f"Traceback: {error_traceback}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_traceback
        }), 500