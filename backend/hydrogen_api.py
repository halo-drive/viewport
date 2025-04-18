# hydrogen_api.py

from flask import Blueprint, request, jsonify
# Assuming these functions now come from hydrogen.py as discussed
from hydrogen import get_coordinates, find_nearest_station, calculate_distances, get_traffic_data, get_route_coordinates, get_weather_data, get_raw_input # Added get_raw_input
from hydrogen_here_map import get_here_directions, get_coordinates as here_get_coordinates, find_nearest_stations
import joblib
import pandas as pd
import numpy as np
import random
import time  # <--- IMPORT TIME
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
    overall_start_time = time.perf_counter() # Start overall timer
    print("\n--- [HYDROGEN API START] ---")

    try:
        # --- 1. Get Form Data & Initial Setup ---
        t_start = time.perf_counter()
        station_postal_codes = ['AB12 3SH', 'S60 5WG', 'B25 8DW', 'SN3 4QS', 'TW6 2GE']
        pallets = float(request.form['pallets'])
        vehicle_type = request.form['vehicleModel']
        origin_depot = request.form['originDepot']
        destination_depot = request.form['destinationDepot']
        vehicle_age = float(request.form['vehicleAge'])
        dispatch_time_str = request.form['dispatchTime']
        dispatch_time = convert_time_to_window(dispatch_time_str)
        target_date = request.form['journeyDate']
        fuel_origin = float(request.form.get('fuelAtOrigin', 0))
        fuel_range1 = float(request.form.get('fuelStation1', 30))
        fuel_range2 = float(request.form.get('fuelStation2', 80))

        total_payload = pallets * 0.88
        goods_weight = total_payload

        # Determine vehicle range/capacity (duplicate logic from hydrogen.py - needs refactor later)
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
            vehicle_range = 300 # Default
            Tank_capacity = 51 # Default

        # NOTE: Avg_Speed_mph = 80 defined here but overridden in get_raw_input later
        Avg_Speed_mph = 80

        origin_uk = f"{origin_depot}, UK"
        destination_uk = f"{destination_depot}, UK"
        print(f"[TIMER] Setup & Form Data: {time.perf_counter() - t_start:.4f}s")

        # --- 2. Analytics Data Fetching (from hydrogen.py / Mapbox/Weather) ---
        t_start = time.perf_counter()
        origin_coordinates = get_coordinates(origin_uk)
        destination_coordinates = get_coordinates(destination_uk)
        t_coords = time.perf_counter()
        print(f"[TIMER] -> get_coordinates (Origin/Dest): {t_coords - t_start:.4f}s")

        mapbox_token = Config.MAPBOX_TOKEN
        nearest_fuel_station = find_nearest_station(origin_uk, station_postal_codes, mapbox_token)
        t_find_station = time.perf_counter()
        print(f"[TIMER] -> find_nearest_station (Mapbox): {t_find_station - t_coords:.4f}s")

        fuel_station_coordinates = get_coordinates(nearest_fuel_station) if nearest_fuel_station else None
        t_station_coords = time.perf_counter()
        print(f"[TIMER] -> get_coordinates (Station): {t_station_coords - t_find_station:.4f}s")

        # Ensure coordinates are valid before calculating distances
        total_city_distance = 0.0
        total_highway_distance = 0.0
        if origin_coordinates and fuel_station_coordinates and destination_coordinates:
            origin_to_fuel_station = calculate_distances(origin_coordinates, fuel_station_coordinates)
            fuel_station_to_destination = calculate_distances(fuel_station_coordinates, destination_coordinates)
            total_city_distance = origin_to_fuel_station[0] + fuel_station_to_destination[0]
            total_highway_distance = origin_to_fuel_station[1] + fuel_station_to_destination[1]
        else:
             print("Warning: Skipping distance calculation due to missing coordinates.")
        t_distances = time.perf_counter()
        print(f"[TIMER] -> calculate_distances (Mapbox): {t_distances - t_station_coords:.4f}s")

        traffic_congestion_level = "Low" # Default
        if origin_coordinates and fuel_station_coordinates and destination_coordinates:
             traffic_congestion_level = get_traffic_data(origin_coordinates, destination_coordinates, fuel_station_coordinates, mapbox_token)
        else:
             print("Warning: Skipping traffic data fetch due to missing coordinates.")
        t_traffic = time.perf_counter()
        print(f"[TIMER] -> get_traffic_data (Mapbox): {t_traffic - t_distances:.4f}s")

        coordinates = []
        if origin_coordinates and destination_coordinates:
            coordinates = get_route_coordinates(origin_coordinates, destination_coordinates)
        else:
             print("Warning: Skipping route coordinate fetch due to missing coordinates.")
        t_route_coords = time.perf_counter()
        print(f"[TIMER] -> get_route_coordinates (Mapbox): {t_route_coords - t_traffic:.4f}s")

        weather_api_key = Config.WEATHER_API_KEY
        average_temperature, snow_classification, rain_classification = 0.0, "Low", "Low" # Defaults
        if coordinates: # Only call weather if we have coordinates
             average_temperature, snow_classification, rain_classification = get_weather_data(weather_api_key, coordinates, target_date)
        else:
             print("Warning: Skipping weather data fetch due to missing route coordinates.")
        t_weather = time.perf_counter()
        print(f"[TIMER] -> get_weather_data (WeatherAPI Loop): {t_weather - t_route_coords:.4f}s <-- MAJOR SUSPECT")

        print(f"[TIMER] TOTAL Analytics Data Fetching: {t_weather - t_start:.4f}s")

        # --- 3. Prediction ---
        t_start = time.perf_counter()
        raw_input_df = get_raw_input(origin_depot, destination_depot, nearest_fuel_station, total_highway_distance,
                                   total_city_distance, traffic_congestion_level, average_temperature,
                                   rain_classification, snow_classification, pallets, vehicle_age, goods_weight, # Corrected: goods_weight
                                   Avg_Speed_mph, dispatch_time, vehicle_type, vehicle_range, Tank_capacity, total_payload)
        t_prep = time.perf_counter()
        print(f"[TIMER] -> get_raw_input (Prep): {t_prep - t_start:.4f}s")

        try:
            prediction = model.predict(raw_input_df)
        except AttributeError as e:
            if "'super' object has no attribute 'get_params'" in str(e):
                prediction = model._Booster.predict(raw_input_df)
            else: raise
        efficiency_prediction = prediction[0]
        t_predict = time.perf_counter()
        print(f"[TIMER] -> model.predict: {t_predict - t_prep:.4f}s")
        print(f"[TIMER] TOTAL Prediction: {t_predict - t_start:.4f}s")

        # --- 4. Cost Calculation ---
        t_start = time.perf_counter()
        Total_dist = total_city_distance + total_highway_distance
        if efficiency_prediction == 0: # Avoid division by zero
             Total_Required_Fuel = float('inf')
             print("Warning: Efficiency prediction is zero, required fuel is infinite.")
        else:
            Total_Required_Fuel = Total_dist / efficiency_prediction

        Total_cost_hydrogen = Total_Required_Fuel * 12 # Hardcoded price
        Cost_per_mile = Total_cost_hydrogen / Total_dist if Total_dist > 0 else 0
        overhead_cost = Total_cost_hydrogen * 0.1
        total_cost = Total_cost_hydrogen + overhead_cost # This is final cost including overhead
        # total_final_cost below seems redundant with total_cost now?
        total_final_cost = total_cost # Assigning for clarity based on response structure
        print(f"[TIMER] Cost Calculation: {time.perf_counter() - t_start:.4f}s")

        # --- 5. Map Route Generation (from hydrogen_here_map / HERE/Nominatim) ---
        t_start = time.perf_counter()
        here_api_key = Config.HERE_API_KEY
        origin_coords_here = here_get_coordinates(origin_depot) # Nominatim call 1
        dest_coords_here = here_get_coordinates(destination_depot) # Nominatim call 2
        route_points = []
        station_points = []
        t_here_coords = time.perf_counter()
        print(f"[TIMER] -> here_get_coordinates (Nominatim): {t_here_coords - t_start:.4f}s")

        t_here_routing_total = 0
        t_here_station_find_total = 0

        if origin_coords_here and dest_coords_here: # Check if geocoding succeeded
            if fuel_origin > Total_Required_Fuel:
                t_route_start = time.perf_counter()
                direct_route = get_here_directions(origin_coords_here, dest_coords_here, here_api_key)
                t_here_routing_total += (time.perf_counter() - t_route_start)
                if direct_route:
                    route_points = direct_route
                    station_points = []
                print("[TIMER] --> Direct HERE Route needed.")
            else:
                print("[TIMER] --> HERE Route with Stations needed.")
                station_cities = ['Aberdeen', 'Birmingham', 'Cardiff', 'Glasgow', 'Leeds', 'Manchester', 'Liverpool', 'London']
                t_station_find_start = time.perf_counter()
                nearest_stations = find_nearest_stations(origin_depot, station_cities, destination_depot) # Multiple Nominatim calls inside
                t_here_station_find_total += (time.perf_counter() - t_station_find_start)
                print(f"[TIMER] ---> find_nearest_stations (Nominatim Loop): {t_here_station_find_total:.4f}s <-- MAJOR SUSPECT")

                if nearest_stations:
                    if len(nearest_stations) == 1:
                        station_name = nearest_stations[0][0]
                        t_stn_coord_start = time.perf_counter()
                        station_coords = here_get_coordinates(station_name) # Nominatim call
                        t_here_station_find_total += (time.perf_counter() - t_stn_coord_start)
                        if station_coords:
                            t_route_start = time.perf_counter()
                            origin_to_station = get_here_directions(origin_coords_here, station_coords, here_api_key)
                            station_to_dest = get_here_directions(station_coords, dest_coords_here, here_api_key)
                            t_here_routing_total += (time.perf_counter() - t_route_start)
                            if origin_to_station and station_to_dest:
                                route_points = origin_to_station + station_to_dest
                                station_points = [{"name": station_name, "coordinates": station_coords}]
                    elif len(nearest_stations) > 1:
                        station1_name = nearest_stations[0][0]
                        station2_name = nearest_stations[1][0]
                        t_stn_coord_start = time.perf_counter()
                        station1_coords = here_get_coordinates(station1_name) # Nominatim call
                        station2_coords = here_get_coordinates(station2_name) # Nominatim call
                        t_here_station_find_total += (time.perf_counter() - t_stn_coord_start)
                        if station1_coords and station2_coords:
                            t_route_start = time.perf_counter()
                            origin_to_station1 = get_here_directions(origin_coords_here, station1_coords, here_api_key)
                            station1_to_station2 = get_here_directions(station1_coords, station2_coords, here_api_key)
                            station2_to_dest = get_here_directions(station2_coords, dest_coords_here, here_api_key)
                            t_here_routing_total += (time.perf_counter() - t_route_start)
                            if origin_to_station1 and station1_to_station2 and station2_to_dest:
                                route_points = origin_to_station1 + station1_to_station2 + station2_to_dest
                                station_points = [
                                    {"name": station1_name, "coordinates": station1_coords},
                                    {"name": station2_name, "coordinates": station2_coords}
                                ]

            # Fallback: If no route with stations was generated, get direct route
            if not route_points:
                print("[TIMER] --> Fallback to direct HERE Route.")
                t_route_start = time.perf_counter()
                direct_route = get_here_directions(origin_coords_here, dest_coords_here, here_api_key)
                t_here_routing_total += (time.perf_counter() - t_route_start)
                if direct_route:
                    route_points = direct_route
        else:
            print("Warning: Skipping HERE routing due to missing Nominatim coordinates.")

        print(f"[TIMER] -> HERE Station Finding (Nominatim): {t_here_station_find_total:.4f}s")
        print(f"[TIMER] -> HERE Routing API Calls: {t_here_routing_total:.4f}s")
        print(f"[TIMER] TOTAL Map Route Generation: {time.perf_counter() - t_start:.4f}s")


        # --- 6. Feature Importance & Final Prep ---
        t_start = time.perf_counter()
        feature_importance = model.feature_importances_
        sorted_idx = np.argsort(feature_importance)[::-1]
        top_8_idx = sorted_idx[:8]
        feature_names = list(raw_input_df.columns)
        top_feature_names = [feature_names[i] for i in top_8_idx]
        top_feature_values = [float(feature_importance[i]) for i in top_8_idx]

        # Log for debugging
        # print("\n\n===== HYDROGEN MODEL PREDICTION =====") ... (kept from original)
        # print("\n===== HYDROGEN TOP 8 FEATURES =====") ... (kept from original)

        feature_importance_data = []
        for name, value in zip(top_feature_names, top_feature_values):
            feature_importance_data.append({"name": name, "value": value})

        # Random values
        good_value_fuel = random.uniform(1.0, Total_cost_hydrogen if Total_cost_hydrogen > 1 else 10) # Use H2 cost
        insurance_fuel_cost = random.uniform(1.0, good_value_fuel)
        goods_loading_time = random.randint(10, 60)
        is_goods_secured = random.choice(['✔️', '❌'])
        check_safety = random.choice(['✔️', '❌'])

        print(f"[TIMER] Feature Imp & Final Prep: {time.perf_counter() - t_start:.4f}s")

        # --- 7. Prepare Response ---
        t_start = time.perf_counter()
        response = {
            "success": True,
            "route": {
                "origin": origin_depot,
                "destination": destination_depot,
                "coordinates": route_points, # From HERE routing
                "stations": station_points, # From HERE routing station logic
                "total_distance": Total_dist # From analytics distance calc
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
                "total_cost": round(total_cost, 2), # Includes overhead
                "cost_per_mile": round(Cost_per_mile, 2),
                "overhead_cost": round(overhead_cost, 2),
                "total_final_cost": round(total_final_cost, 2), # Same as total_cost now
                "fuel_price": 12, # Hardcoded H2 price per kg
                "good_value_fuel": round(good_value_fuel, 2),
                "insurance_fuel_cost": round(insurance_fuel_cost, 2),
                "goods_loading_time": goods_loading_time,
                "is_goods_secured": is_goods_secured,
                "check_safety": check_safety,
                "featureImportance": feature_importance_data
            }
        }
        print(f"[TIMER] Response Construction: {time.perf_counter() - t_start:.4f}s")

        print(f"--- [HYDROGEN API END] TOTAL TIME: {time.perf_counter() - overall_start_time:.4f}s ---")
        return jsonify(response)

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in hydrogen route API: {str(e)}")
        print(f"Traceback: {error_traceback}")
        # Log total time even on error
        print(f"--- [HYDROGEN API END - ERROR] TOTAL TIME: {time.perf_counter() - overall_start_time:.4f}s ---")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_traceback # Maybe remove traceback in production
        }), 500