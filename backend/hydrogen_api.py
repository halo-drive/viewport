# hydrogen_api.py
# V5: Fix traffic warning and reduce weather API calls

from flask import Blueprint, request, jsonify
# <<< MODIFIED IMPORTS >>>
# Get analytics functions primarily from tracking.py for consistency
# Keep hydrogen.py imports for model input prep and specific H2 functions if any remain
from tracking import get_route_traffic_data, get_weather_data, calculate_distances as calculate_distances_tracking, get_coordinates as get_coordinates_tracking
from hydrogen import find_nearest_station, get_raw_input # Keep find_nearest_station for postal codes, get_raw_input
# Keep get_coordinates from hydrogen.py if needed elsewhere, or alias tracking one
# from hydrogen import get_coordinates
# <<< END MODIFIED IMPORTS >>>

# Import HERE map functions
from hydrogen_here_map import get_here_directions, get_coordinates as here_get_coordinates_nominatim
# Import geodesic for distance calculation
from geopy.distance import geodesic
from typing import Dict, Any, List, Tuple, Optional # Added Optional
import joblib
import pandas as pd
import numpy as np
import random
import time
import traceback
from config import Config

# Definitive H2 stations list
DEFINITIVE_H2_STATIONS: List[Dict[str, Any]] = [
    # ... (list remains the same) ...
    {'postal_code': 'AB12 3FU', 'name': 'Aberdeen H2 Station', 'coords': (57.10741937854072, -2.0904684228947445)},
    {'postal_code': 'S60 5WG', 'name': 'Rotherham H2 Station', 'coords': (53.38600389416075, -1.3788029534943287)},
    {'postal_code': 'B25 8HU', 'name': 'Birmingham H2 Station', 'coords': (52.46120169452769, -1.8398180963237745)},
    {'postal_code': 'SN5 8AT', 'name': 'Swindon H2 Station', 'coords': (51.547694679567684, -1.8557626651533776)},
    {'postal_code': 'TW6 2SQ', 'name': 'Heathrow H2 Station', 'coords': (51.46877479486763, -0.42002441117222283)},
]

# Known depot coordinates for model input mapping
KNOWN_DEPOT_COORDS = {
    # ... (dictionary remains the same) ...
    'London': (51.5074, -0.1278), 'Liverpool': (53.4084, -2.9916),
    'Manchester': (53.4808, -2.2426), 'Leeds': (53.8008, -1.5491),
    'Birmingham': (52.4862, -1.8904), 'Glasgow': (55.8642, -4.2518),
    'Cardiff': (51.4816, -3.1791), 'Aberdeen': (57.1497, -2.0943)
}

# Load the model
model = joblib.load('Hydrogen_model.pkl')

# Initialize the blueprint
hydrogen_api_bp = Blueprint('hydrogen_api', __name__)

# Encodings for the model
# ... (encodings remain the same) ...
vehicle_type_encoded = ['HVS HGV', 'HVS MCV', 'Hymax Series']
origin_encoded = {'Aberdeen': 0, 'Birmingham': 1, 'Cardiff': 2, 'Glasgow': 3, 'Leeds': 4, 'Liverpool': 5, 'London': 6, 'Manchester': 7}
nearest_station_encoded = {'AB12 3SH': 0, 'B25 8DW': 1, 'S60 5WG': 2, 'SN3 4QS': 3, 'TW6 2GE': 4}
dispatch_encoded = {'morning': 0, 'night': 1, 'noon': 2}
traffic_congestion_encoded = {'low': 0, 'medium': 1, 'high': 2}
rain_encoded = {'low': 0, 'medium': 1, 'high': 2}
snow_encoded = {'low': 0, 'medium': 1, 'high': 2}


def convert_time_to_window(time_str):
    # ... (function remains the same) ...
    try: hours, minutes, seconds = map(int, time_str.split(':'))
    except ValueError: return "noon" # Default on error
    if 4 <= hours < 12: return "morning"
    elif 12 <= hours < 20: return "noon"
    else: return "night"


@hydrogen_api_bp.route('/api/hydrogen/route', methods=['POST'])
def hydrogen_route_api():
    overall_start_time = time.perf_counter()
    print("\n--- [HYDROGEN API START] ---")

    try:
        # --- 1. Get Form Data & Initial Setup ---
        # ... (form data retrieval largely the same) ...
        t_start = time.perf_counter()
        # station_postal_codes list is used by find_nearest_station, keep it for now
        station_postal_codes = ['AB12 3SH', 'S60 5WG', 'B25 8DW', 'SN3 4QS', 'TW6 2GE']

        try:
            # ... (get required fields) ...
            pallets = float(request.form['pallets'])
            vehicle_type = request.form['vehicleModel']
            destination_depot = request.form['destinationDepot']
            vehicle_age = float(request.form['vehicleAge'])
            dispatch_time_str = request.form['dispatchTime']
            target_date = request.form['journeyDate']
        except KeyError as e: return jsonify({"success": False, "error": f"Missing field: {e}"}), 400
        except ValueError as e: return jsonify({"success": False, "error": f"Invalid value: {e}"}), 400

        fuel_origin = float(request.form.get('fuelAtOrigin', 0))
        dispatch_time = convert_time_to_window(dispatch_time_str)
        total_payload = pallets * 0.88; goods_weight = total_payload
        # ... (vehicle range/capacity logic) ...
        if vehicle_type == 'HVS HGV': vehicle_range = 300; Tank_capacity = 51
        elif vehicle_type == 'HVS MCV': vehicle_range = 370; Tank_capacity = 51
        elif vehicle_type == 'Hymax Series': vehicle_range = 422; Tank_capacity = 60
        else: vehicle_range = 300; Tank_capacity = 51; print(f"Warn: Unknown vehicle {vehicle_type}")

        # --- Handle Origin (GPS or Depot Name) ---
        # ... (logic using KNOWN_DEPOT_COORDS remains the same) ...
        origin_lat = request.form.get('originLat', type=float)
        origin_lon = request.form.get('originLon', type=float)
        origin_depot_name = request.form.get('originDepot')
        origin_coordinates: Optional[Tuple[float, float]] = None
        origin_for_model: Optional[str] = None
        origin_display_name: Optional[str] = None

        if origin_lat is not None and origin_lon is not None:
            origin_coordinates = (origin_lat, origin_lon); origin_display_name = "Current Location (GPS)"
            print(f"Using GPS origin: {origin_coordinates}")
            min_distance = float('inf'); nearest_depot_name = None
            input_gps_coords = origin_coordinates; print("Calculating nearest known depot for model input...")
            if KNOWN_DEPOT_COORDS:
                for name, coords in KNOWN_DEPOT_COORDS.items():
                    try:
                         if isinstance(coords, (list, tuple)) and len(coords) == 2:
                              dist = geodesic(input_gps_coords, coords).miles
                              if dist < min_distance: min_distance = dist; nearest_depot_name = name
                         else: print(f"Warn: Invalid depot coords {name}")
                    except Exception as e: print(f"Warn: Dist calc error {name}: {e}")
            origin_for_model = nearest_depot_name if nearest_depot_name else 'London'
            if nearest_depot_name: print(f"GPS mapped to model origin: '{origin_for_model}'")
            else: print(f"Defaulting model origin to '{origin_for_model}'.")
        elif origin_depot_name:
            origin_for_model = origin_depot_name; origin_display_name = origin_depot_name
            print(f"Using Depot origin: {origin_depot_name}. Geocoding...")
            # Use the geocoder from tracking.py for consistency now
            origin_coordinates = get_coordinates_tracking(f"{origin_depot_name}, UK")
            if not (origin_coordinates and origin_coordinates[0] is not None):
                  return jsonify({"success": False, "error": f"Could not geocode origin depot: {origin_depot_name}"}), 400
            print(f"Geocoded Depot origin: {origin_coordinates}")
        else: return jsonify({"success": False, "error": "Missing origin info"}), 400

        # --- Geocode Destination ---
        print(f"Geocoding destination: {destination_depot}...")
        # Use the geocoder from tracking.py for consistency
        destination_coordinates = get_coordinates_tracking(f"{destination_depot}, UK")
        if not (destination_coordinates and destination_coordinates[0] is not None):
            return jsonify({"success": False, "error": f"Could not geocode dest depot: {destination_depot}"}), 400
        print(f"Geocoded Destination: {destination_coordinates}")

        print(f"[TIMER] Setup & Geocoding: {time.perf_counter() - t_start:.4f}s")

        # --- 2. Analytics Data Fetching ---
        # <<< MODIFIED SECTION >>>
        t_start = time.perf_counter()
        mapbox_token = Config.MAPBOX_TOKEN # Needed for find_nearest_station postal code lookup

        # Find nearest station *postal code* (for model input feature 'Closest_station')
        origin_name_for_station_find = f"{origin_for_model}, UK"
        nearest_station_postal_code = find_nearest_station(origin_name_for_station_find, station_postal_codes, mapbox_token)
        t_find_station = time.perf_counter()
        print(f"[TIMER] -> find_nearest_station (Mapbox): {t_find_station - t_start:.4f}s")

        # Calculate distances (using tracking.py function)
        total_city_distance, total_highway_distance = 0.0, 0.0
        if origin_coordinates and destination_coordinates:
             total_city_distance, total_highway_distance = calculate_distances_tracking(origin_coordinates, destination_coordinates)
        else: return jsonify({"success": False, "error": "Internal error: Missing coords for dist calc."}), 500
        t_distances = time.perf_counter()
        print(f"[TIMER] -> calculate_distances (Mapbox O->D): {t_distances - t_find_station:.4f}s")

        # Get Route Coords (for weather) AND Traffic delay using the tracking.py function
        route_coords_for_weather = []
        traffic_delay = 0.0
        if origin_coordinates and destination_coordinates:
            # This function samples points (default ~15 in tracking.py) and gets delay
            route_coords_for_weather, traffic_delay = get_route_traffic_data(origin_coordinates, destination_coordinates)
        else: print("Error: Missing coordinates for traffic/weather route fetch.")
        t_traffic_weather_coords = time.perf_counter()
        # This timer now includes both route sampling AND traffic delay fetch
        print(f"[TIMER] -> get_route_traffic_data (Coords+Delay): {t_traffic_weather_coords - t_distances:.4f}s")

        # Determine traffic severity from delay
        traffic_severity = "high" if traffic_delay > 30 else "medium" if traffic_delay > 7 else "low"
        print(f"Traffic Severity: {traffic_severity} (Delay: {traffic_delay:.2f} mins)")

        # Get weather data (using tracking.py function)
        weather_api_key = Config.WEATHER_API_KEY
        average_temperature, snow_classification, rain_classification = 0.0, "Low", "Low"
        if route_coords_for_weather: # Check if we got coordinates
             # This call now uses fewer points (~15) provided by get_route_traffic_data
             average_temperature, snow_classification, rain_classification = get_weather_data(weather_api_key, route_coords_for_weather, target_date)
        else: print("Warning: Skipping weather data fetch.")
        t_weather = time.perf_counter()
        # This timer should be much shorter now
        print(f"[TIMER] -> get_weather_data (WeatherAPI Loop): {t_weather - t_traffic_weather_coords:.4f}s")
        # <<< END MODIFIED SECTION >>>

        print(f"[TIMER] TOTAL Analytics Data Fetching: {t_weather - t_start:.4f}s")


        # --- 3. Prediction ---
        t_start = time.perf_counter()
        raw_input_df = get_raw_input(
            Origin_depot=origin_for_model, Destination_depot=destination_depot,
            nearest_fuel_station=nearest_station_postal_code, # Use postal code from find_nearest_station
            total_highway_distance=total_highway_distance, total_city_distance=total_city_distance,
            traffic_congestion_level=traffic_severity, # Use severity derived from delay
            average_temperature=average_temperature,
            rain_classification=rain_classification, snow_classification=snow_classification,
            pallets=pallets, Vehicle_age=vehicle_age, Goods_weight=goods_weight,
            Avg_Speed_mph=65, dispatch_time=dispatch_time, vehicle_type=vehicle_type,
            vehicle_range=vehicle_range, Tank_capacity=Tank_capacity, total_payload=total_payload
        )
        # ... (rest of prediction logic) ...
        t_prep = time.perf_counter()
        print(f"[TIMER] -> get_raw_input (Prep): {t_prep - t_start:.4f}s")
        try: prediction = model.predict(raw_input_df)
        except AttributeError: prediction = model._Booster.predict(raw_input_df)
        efficiency_prediction = prediction[0] if prediction else 0
        t_predict = time.perf_counter(); print(f"[TIMER] -> model.predict: {t_predict - t_prep:.4f}s")
        print(f"[TIMER] TOTAL Prediction: {t_predict - t_start:.4f}s")


        # --- 4. Cost Calculation ---
        # ... (cost calculation remains the same) ...
        t_start = time.perf_counter()
        Total_dist_analytics = total_city_distance + total_highway_distance
        if efficiency_prediction == 0: Total_Required_Fuel = float('inf')
        else: Total_Required_Fuel = Total_dist_analytics / efficiency_prediction
        Total_cost_hydrogen = Total_Required_Fuel * 12
        Cost_per_mile = Total_cost_hydrogen / Total_dist_analytics if Total_dist_analytics > 0 else 0
        overhead_cost = Total_cost_hydrogen * 0.1
        total_cost = Total_cost_hydrogen + overhead_cost; total_final_cost = total_cost
        print(f"[TIMER] Cost Calculation: {time.perf_counter() - t_start:.4f}s")


        # --- 5. Map Route Generation (Using HERE & Definitive Stations) ---
        # ... (logic using DEFINITIVE_H2_STATIONS remains the same) ...
        t_start = time.perf_counter()
        here_api_key = Config.HERE_API_KEY
        route_points = []; station_points = []
        actual_route_distance = Total_dist_analytics # Default

        if origin_coordinates and destination_coordinates:
            origin_coords_tuple_for_here = origin_coordinates
            # Geocode destination using Nominatim via hydrogen_here_map for HERE routing part
            dest_coords_here_tuple = here_get_coordinates_nominatim(destination_depot)

            if dest_coords_here_tuple and dest_coords_here_tuple[0] is not None:
                dest_coords_tuple_for_here = dest_coords_here_tuple
                t_here_dest_coords = time.perf_counter()
                print(f"[TIMER] -> here_get_coordinates_nominatim (Dest): {t_here_dest_coords - t_start:.4f}s")

                if fuel_origin > Total_Required_Fuel:
                    # Direct route needed
                    print("[MAP ROUTE] Fuel sufficient. Calculating direct HERE Route.")
                    t_route_start = time.perf_counter()
                    direct_route = get_here_directions(origin_coords_tuple_for_here, dest_coords_tuple_for_here, here_api_key)
                    print(f"[TIMER] -> HERE Direct Route API Call: {time.perf_counter() - t_route_start:.4f}s")
                    if direct_route: route_points = direct_route
                    else: print("Warning: Failed to get direct route polyline from HERE.")
                    station_points = []
                else:
                    # Station stop needed
                    print("[MAP ROUTE] Fuel needed. Finding best station from definitive list...")
                    min_total_deviation_distance = float('inf'); best_station = None
                    if DEFINITIVE_H2_STATIONS:
                        for station in DEFINITIVE_H2_STATIONS:
                            station_coords = station.get('coords')
                            if not (isinstance(station_coords, tuple) and len(station_coords) == 2): continue
                            try:
                                deviation_dist = (geodesic(origin_coords_tuple_for_here, station_coords).miles +
                                                  geodesic(station_coords, dest_coords_tuple_for_here).miles)
                                if deviation_dist < min_total_deviation_distance:
                                    min_total_deviation_distance = deviation_dist; best_station = station
                            except Exception as e: print(f"Warn: Dist calc error station {station.get('name')}: {e}")
                    else: print("Warn: Definitive station list empty.")

                    if best_station:
                        # Route via best station
                        best_station_name = best_station.get('name', 'H2 Station')
                        best_station_coords = best_station.get('coords')
                        print(f"[MAP ROUTE] Best station: '{best_station_name}'")
                        t_route_start = time.perf_counter()
                        origin_to_station_route = get_here_directions(origin_coords_tuple_for_here, best_station_coords, here_api_key)
                        station_to_dest_route = get_here_directions(best_station_coords, dest_coords_tuple_for_here, here_api_key)
                        print(f"[TIMER] -> HERE Route API Calls (O->S, S->D): {time.perf_counter() - t_route_start:.4f}s")
                        if origin_to_station_route and station_to_dest_route:
                            route_points = origin_to_station_route + station_to_dest_route
                            station_points = [{"name": best_station_name, "coordinates": best_station_coords}]
                        else: # Fallback
                            print("Warn: Failed route via station. Falling back direct.")
                            t_route_start = time.perf_counter()
                            direct_route = get_here_directions(origin_coords_tuple_for_here, dest_coords_tuple_for_here, here_api_key)
                            print(f"[TIMER] -> HERE Direct Route (Fallback): {time.perf_counter() - t_route_start:.4f}s")
                            if direct_route: route_points = direct_route
                            station_points = []
                    else:
                        # Fallback if no best station found
                        print("[MAP ROUTE] No suitable station found. Calculating direct route.")
                        t_route_start = time.perf_counter()
                        direct_route = get_here_directions(origin_coords_tuple_for_here, dest_coords_tuple_for_here, here_api_key)
                        print(f"[TIMER] -> HERE Direct Route (No Station): {time.perf_counter() - t_route_start:.4f}s")
                        if direct_route: route_points = direct_route
                        station_points = []
            else:
                print("Warning: Skipping HERE routing, failed to geocode destination with Nominatim.")
        else:
            print("Warning: Skipping HERE routing due to missing origin/destination coordinates.")

        print(f"[TIMER] TOTAL Map Route Generation: {time.perf_counter() - t_start:.4f}s")

        # --- 6. Feature Importance & Final Prep ---
        # ... (Remains the same) ...
        t_start = time.perf_counter(); feature_importance_data = []
        # ... (feature importance logic) ...
        if hasattr(model, 'feature_importances_'):
             feature_importance = model.feature_importances_
             if raw_input_df is not None and not raw_input_df.empty:
                  sorted_idx = np.argsort(feature_importance)[::-1]; top_8_idx = sorted_idx[:8]
                  feature_names = list(raw_input_df.columns); top_8_idx = [i for i in top_8_idx if i < len(feature_names)]
                  top_feature_names = [feature_names[i] for i in top_8_idx]; top_feature_values = [float(feature_importance[i]) for i in top_8_idx]
                  feature_importance_data = [{"name": name, "value": value} for name, value in zip(top_feature_names, top_feature_values)]
             else: print("Warn: Cannot calc FI, input df empty.")
        elif hasattr(model, '_Booster') and hasattr(model._Booster, 'get_score'):
             try:
                  fscore = model._Booster.get_score(importance_type='weight')
                  if fscore:
                       sorted_features = sorted(fscore.items(), key=lambda item: item[1], reverse=True); top_features = sorted_features[:8]
                       feature_importance_data = [{"name": name, "value": float(score)} for name, score in top_features]
                  else: print("Warn: Booster get_score empty.")
             except Exception as fi_err: print(f"Warn: FI error: {fi_err}")
        else: print("Warn: Model has no FI attribute.")
        # ... (random values logic) ...
        good_value_fuel = random.uniform(1.0, Total_cost_hydrogen if Total_cost_hydrogen > 1 else 10)
        insurance_fuel_cost = random.uniform(1.0, good_value_fuel)
        goods_loading_time = random.randint(10, 60)
        is_goods_secured = random.choice(['✔️', '❌'])
        check_safety = random.choice(['✔️', '❌'])
        print(f"[TIMER] Feature Imp & Final Prep: {time.perf_counter() - t_start:.4f}s")

        # --- 7. Prepare Response ---
        # ... (Remains the same) ...
        t_start = time.perf_counter()
        response = {
            "success": True,
            "route": { "origin": origin_display_name, "destination": destination_depot, "coordinates": route_points, "stations": station_points, "total_distance": round(Total_dist_analytics, 2)},
            "analytics": {
                 "average_temperature": round(average_temperature, 2),"rain_classification": rain_classification,"snow_classification": snow_classification,
                 "highway_distance": round(total_highway_distance, 2),"city_distance": round(total_city_distance, 2), "efficiency_prediction": round(efficiency_prediction, 2),
                 "total_required_fuel": round(Total_Required_Fuel, 2) if Total_Required_Fuel != float('inf') else "Infinity",
                 "total_fuel_cost": round(Total_cost_hydrogen, 2) if Total_Required_Fuel != float('inf') else "Infinity",
                 "total_cost": round(total_cost, 2) if Total_Required_Fuel != float('inf') else "Infinity",
                 "cost_per_mile": round(Cost_per_mile, 2) if Total_dist_analytics > 0 else 0,
                 "overhead_cost": round(overhead_cost, 2) if Total_Required_Fuel != float('inf') else "Infinity",
                 "total_final_cost": round(total_final_cost, 2) if Total_Required_Fuel != float('inf') else "Infinity",
                 "fuel_price": 12, "good_value_fuel": round(good_value_fuel, 2), "insurance_fuel_cost": round(insurance_fuel_cost, 2),
                 "goods_loading_time": goods_loading_time, "is_goods_secured": is_goods_secured, "check_safety": check_safety,
                 "featureImportance": feature_importance_data
            }
        }
        print(f"[TIMER] Response Construction: {time.perf_counter() - t_start:.4f}s")
        print(f"--- [HYDROGEN API END] TOTAL TIME: {time.perf_counter() - overall_start_time:.4f}s ---")
        return jsonify(response)

    # --- Exception Handling ---
    except Exception as e:
        # ... (Remains the same) ...
        error_traceback = traceback.format_exc(); print(f"Error in hydrogen route API: {str(e)}\n{error_traceback}")
        print(f"--- [HYDROGEN API END - ERROR] TOTAL TIME: {time.perf_counter() - overall_start_time:.4f}s ---")
        return jsonify({"success": False,"error": f"An unexpected error occurred: {str(e)}",}), 500