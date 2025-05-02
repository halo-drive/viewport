# diesel_api.py
# Modified to handle GPS coordinates for origin
# V2: Implements nearest known depot calculation for GPS origin model input

from flask import Blueprint, request, jsonify
# Import geodesic for distance calculation
from geopy.distance import geodesic
# Assuming tracking.py provides geocode_maps_co for non-GPS cases
from tracking import get_coordinates as geocode_maps_co, calculate_distances, get_route_traffic_data, get_weather_data
# Import the modified function from diesel_routing_here
from diesel_routing_here import get_here_directions, get_coordinates as here_get_coordinates, get_fuel_station_coordinates, get_route_with_fuel_stations
import joblib
import pandas as pd
import numpy as np
import random
import requests
import traceback
from config import Config

# <<< NEW: Store known depot coordinates (same as used in hydrogen_api) >>>
# Format: { 'DepotName': (latitude, longitude) }
KNOWN_DEPOT_COORDS = {
    'London': (51.5074, -0.1278),
    'Liverpool': (53.4084, -2.9916),
    'Manchester': (53.4808, -2.2426),
    'Leeds': (53.8008, -1.5491),
    'Birmingham': (52.4862, -1.8904),
    'Glasgow': (55.8642, -4.2518),
    'Cardiff': (51.4816, -3.1791),
    'Aberdeen': (57.1497, -2.0943)
}
# <<< END NEW >>>

# (Keep model loading, fuel price logic, blueprint init as before)
model = joblib.load('Fossil_model.pkl')
url = "https://fuel.motorfuelgroup.com/fuel_prices_data.json"
try:
    response = requests.get(url)
    fuel_data = response.json() if response.status_code == 200 else None
except Exception as e:
    print(f"Warning: Failed to fetch fuel price data: {e}")
    fuel_data = None
def get_average_diesel_price_by_city(data, city):
    # (code unchanged)
    if not data or not city: return 175.9 # Default
    city_upper = city.upper()
    prices = [
        station["prices"].get("B7") for station in data.get("stations", [])
        if city_upper in station.get("address", "").upper() and station.get("prices", {}).get("B7")
    ]
    return sum(prices) / len(prices) if prices else 175.9

diesel_api_bp = Blueprint('diesel_api', __name__)

# Encodings (ensure keys match KNOWN_DEPOT_COORDS)
vehicle_type_encoded = ['DAF XF 105.510', 'DAF XG 530', 'IVECO EuroCargo ml180e28', 'IVECO NP 460', 'MAN TGM 18.250', 'MAN TGX 18.400', 'SCANIA G 460', 'SCANIA R 450', 'VOLVO FH 520', 'VOLVO FL 420']
origin_encoded = {'Aberdeen': 0, 'Birmingham': 1, 'Cardiff': 2, 'Glasgow': 3, 'Leeds': 4, 'Liverpool': 5, 'London': 6, 'Manchester': 7}
dispatch_encoded = {'morning': 0, 'night': 1, 'noon': 2}
traffic_congestion_encoded = {'low': 0, 'medium': 1, 'high': 2}
temp_encoded = {'low': 0, 'medium': 1, 'high': 2}
precipitation_encoded = {'low': 0, 'medium': 1, 'high': 2}
snow_encoded = {'low': 0, 'medium': 1, 'high': 2}

def convert_time_to_window(time_str):
    # (code unchanged, but consider adding error handling like in hydrogen)
    try:
        hours = int(time_str.split(':')[0])
        if 4 <= hours < 12: return "morning"
        elif 12 <= hours < 20: return "noon"
        else: return "night"
    except ValueError:
        print(f"Warning: Invalid dispatchTime format '{time_str}'. Defaulting to 'noon'.")
        return "noon" # Default on error

@diesel_api_bp.route('/api/diesel/route', methods=['POST'])
def diesel_route_api():
    try:
        # --- Get Form Data ---
        # (Error handling for missing/invalid fields added for robustness)
        try:
            pallets = request.form.get('pallets', type=float, default=20.0)
            vehicle_type = request.form.get('vehicleModel', 'VOLVO FH 520')
            destination_depot = request.form['destinationDepot'] # Required
            vehicle_age = request.form.get('vehicleAge', type=float, default=3.0)
            dispatch_time_str = request.form.get('dispatchTime', '12:00:00')
            target_date = request.form['journeyDate'] # Required
        except KeyError as e:
            return jsonify({"success": False, "error": f"Missing required form field: {e}"}), 400
        except ValueError as e:
             # This might catch errors if default types fail, though less likely with .get defaults
            return jsonify({"success": False, "error": f"Invalid numeric value in form field: {e}"}), 400

        # --- Handle Origin (GPS or Depot Name) ---
        origin_lat = request.form.get('originLat', type=float)
        origin_lon = request.form.get('originLon', type=float)
        origin_depot_name = request.form.get('originDepot') # Still check for depot name

        start_coords = None # Tuple (lat, lon) for geographic calculations
        origin_for_model = None # Name for model encoding ('London', 'Birmingham', etc.)
        origin_display_name = None # Name for response ('Current Location (GPS)' or actual depot)

        if origin_lat is not None and origin_lon is not None:
            # <<< MODIFIED SECTION for GPS Origin >>>
            start_coords = (origin_lat, origin_lon) # Use actual GPS coords for geo calculations
            origin_display_name = "Current Location (GPS)"
            print(f"Using GPS origin: {start_coords}")

            # Find nearest known depot for model input
            min_distance = float('inf')
            nearest_depot_name = None
            input_gps_coords = start_coords # Use the tuple

            print("Calculating nearest known depot for model input...")
            if not KNOWN_DEPOT_COORDS:
                 print("Warning: KNOWN_DEPOT_COORDS is empty. Cannot find nearest depot.")
            else:
                for depot_name, depot_coords in KNOWN_DEPOT_COORDS.items():
                    try:
                        if isinstance(depot_coords, (list, tuple)) and len(depot_coords) == 2:
                             distance = geodesic(input_gps_coords, depot_coords).miles
                             # print(f"  Distance to {depot_name}: {distance:.2f} miles") # Debug log
                             if distance < min_distance:
                                 min_distance = distance
                                 nearest_depot_name = depot_name
                        else:
                             print(f"Warning: Invalid coordinate format for depot '{depot_name}': {depot_coords}")
                    except ValueError as e:
                         print(f"Warning: Could not calculate distance to depot '{depot_name}' (coords: {depot_coords}): {e}")
                    except Exception as e:
                         print(f"Warning: Unexpected error calculating distance to depot '{depot_name}': {e}")

            # Set origin_for_model to the nearest found, or default to London if none found
            origin_for_model = nearest_depot_name if nearest_depot_name else 'London'
            if nearest_depot_name:
                print(f"GPS Coordinates {input_gps_coords} mapped to nearest depot for model: '{origin_for_model}' (Distance: {min_distance:.2f} miles)")
            else:
                print(f"Could not determine nearest depot. Defaulting model origin to '{origin_for_model}'.")
            # <<< END MODIFIED SECTION >>>

        elif origin_depot_name:
            # Handle depot name input (uses HERE for geocoding first)
            origin_for_model = origin_depot_name
            origin_display_name = origin_depot_name
            coords_result = here_get_coordinates(f"{origin_depot_name}, UK", Config.HERE_API_KEY)
            if coords_result and coords_result[0] is not None:
                 start_coords = coords_result
                 print(f"Using Depot origin: {origin_depot_name}, Coords (HERE): {start_coords}")
            else:
                 # Fallback geocode using tracking.py's method
                 print(f"Warning: HERE geocode failed for {origin_depot_name}, trying fallback (Geocode.maps.co).")
                 start_coords = geocode_maps_co(f"{origin_depot_name}, UK")
                 if not (start_coords and start_coords[0] is not None):
                      return jsonify({"success": False, "error": f"Could not geocode origin depot: {origin_depot_name}"}), 400
                 print(f"Using Depot origin (fallback geocode): {origin_depot_name}, Coords: {start_coords}")
        else:
            return jsonify({"success": False, "error": "Missing origin information (GPS coordinates or originDepot name)"}), 400

        # Geocode destination (Using HERE)
        if not destination_depot: return jsonify({"success": False, "error": "Missing destination depot"}), 400
        if not target_date: return jsonify({"success": False, "error": "Missing journey date"}), 400 # Check target date earlier
        dest_coords = here_get_coordinates(f"{destination_depot}, UK", Config.HERE_API_KEY)
        if not dest_coords or dest_coords[0] is None:
            # Add fallback for destination geocoding?
            print(f"Warning: HERE geocode failed for destination {destination_depot}, trying fallback.")
            dest_coords = geocode_maps_co(f"{destination_depot}, UK")
            if not (dest_coords and dest_coords[0] is not None):
                return jsonify({"success": False, "error": f"Could not geocode destination depot: {destination_depot}"}), 400
            print(f"Destination (fallback geocode): {destination_depot}, Coords: {dest_coords}")
        else:
             print(f"Destination: {destination_depot}, Coords (HERE): {dest_coords}")

        # --- End Coordinate Handling ---

        dispatch_time = convert_time_to_window(dispatch_time_str)
        total_payload = pallets * 0.88
        goods_weight = total_payload
        api_key = Config.HERE_API_KEY # HERE API Key

        # --- Get Route & Stations (using start_coords tuple) ---
        try:
            # Call the modified function with coordinate tuples directly
            _, direct_polyline_points, fuel_station_coords = get_route_with_fuel_stations(
                 api_key,
                 origin_coords=start_coords, # Pass tuple (lat, lon)
                 destination_coords=dest_coords # Pass tuple (lat, lon)
            )
        except ValueError as ve:
             print(f"Error getting route/stations from HERE: {ve}")
             return jsonify({"success": False, "error": f"Failed to calculate route: {ve}"}), 500
        except Exception as e_route: # Catch other potential errors
             print(f"Unexpected error in get_route_with_fuel_stations: {e_route}")
             return jsonify({"success": False, "error": f"Failed to calculate route: {str(e_route)}"}), 500


        route_points_for_response = direct_polyline_points if direct_polyline_points else []
        station_points = [{"name": f"Fuel Station {i+1}", "coordinates": coord} for i, coord in enumerate(fuel_station_coords)]

        # --- Rebuild combined route polyline if stations found (uses coordinate tuples) ---
        combined_route_points = []
        if fuel_station_coords:
             origin_coords_str = f"{start_coords[0]},{start_coords[1]}"
             dest_coords_str = f"{dest_coords[0]},{dest_coords[1]}"
             # (Route rebuilding logic remains the same)
             first_station_str = f"{fuel_station_coords[0][0]},{fuel_station_coords[0][1]}"
             origin_to_first = get_here_directions(origin_coords_str, first_station_str, api_key)
             if origin_to_first: combined_route_points.extend(origin_to_first)

             for i in range(len(fuel_station_coords) - 1):
                 current_str = f"{fuel_station_coords[i][0]},{fuel_station_coords[i][1]}"
                 next_s_str = f"{fuel_station_coords[i+1][0]},{fuel_station_coords[i+1][1]}"
                 station_to_station = get_here_directions(current_str, next_s_str, api_key)
                 if station_to_station: combined_route_points.extend(station_to_station)

             last_station_str = f"{fuel_station_coords[-1][0]},{fuel_station_coords[-1][1]}"
             last_to_dest = get_here_directions(last_station_str, dest_coords_str, api_key)
             if last_to_dest: combined_route_points.extend(last_to_dest)

             if combined_route_points:
                  route_points_for_response = combined_route_points
             else:
                  print("Warning: Failed to generate combined route through stations, using direct route.")


        # --- Analytics Calculations (using start_coords tuple) ---
        # Calculate distances (using Mapbox via tracking.py)
        city_distance, highway_distance = calculate_distances(start_coords, dest_coords)

        # Get traffic and weather route coords (using Mapbox via tracking.py)
        route_coordinates_for_weather, traffic_delay = get_route_traffic_data(start_coords, dest_coords)
        traffic_severity = "high" if traffic_delay > 30 else "medium" if traffic_delay > 7 else "low"

        # Get weather data (using WeatherAPI via tracking.py)
        weather_api_key = Config.WEATHER_API_KEY
        average_temperature, snow_classification, rain_classification = get_weather_data(weather_api_key, route_coordinates_for_weather, target_date)


        # --- Prepare Data for Prediction ---
        # Uses origin_for_model (nearest depot name or actual) for encoding
        encoded_origin = origin_encoded.get(origin_for_model, origin_encoded['London']) # Default to London if lookup fails
        encoded_destination = origin_encoded.get(destination_depot, -1) # Use -1 for unknown destination? Check model training
        encoded_dispatch_time = dispatch_encoded.get(dispatch_time, -1)
        encoded_avg_traffic_congestion = traffic_congestion_encoded.get(traffic_severity.lower(), -1)
        temp_cat = "high" if average_temperature > 15 else "low" if average_temperature < 5 else "medium"
        encoded_avg_temp = temp_encoded.get(temp_cat, 1) # Default to medium
        encoded_avg_precipitation = precipitation_encoded.get(rain_classification.lower(), -1)
        encoded_avg_snow = snow_encoded.get(snow_classification.lower(), -1)
        dummy_variables = {vehicle: (1 if vehicle == vehicle_type else 0) for vehicle in vehicle_type_encoded}

        input_data = {
            "Vehicle_age": [vehicle_age], "Goods_weight": [goods_weight],
            "Total_distance_miles": [city_distance + highway_distance],
            "Avg_traffic_congestion": [encoded_avg_traffic_congestion],
            "Avg_temp": [encoded_avg_temp], "Avg_Precipitation": [encoded_avg_precipitation],
            "Avg_snow": [encoded_avg_snow],
            "Origin_depot": [encoded_origin], # <<< USES NEAREST/ACTUAL DEPOT NAME (ENCODED)
            "Destination_depot": [encoded_destination], "Avg_Speed_mph": [65], # Assuming 65 is standard/expected
            "Distance_highway": [highway_distance], "Distance_city": [city_distance],
            "dispatch_time": [encoded_dispatch_time], "total_payload": [total_payload]
        }
        input_data.update(dummy_variables)
        raw_input_df = pd.DataFrame(input_data)

        # --- Prediction ---
        try:
             prediction = model.predict(raw_input_df)
        except AttributeError as e:
             if hasattr(model, '_Booster'):
                  prediction = model._Booster.predict(raw_input_df)
             else:
                  print(f"Error during prediction: Model object type is {type(model)}")
                  raise
        efficiency_prediction = prediction[0] if prediction else 0


        # --- Cost & Metric Calculation ---
        total_dist = city_distance + highway_distance
        total_required_fuel = total_dist / efficiency_prediction if efficiency_prediction else float('inf')
        # Use origin_for_model name for fuel price lookup
        fuel_price = get_average_diesel_price_by_city(fuel_data, origin_for_model)
        fuel_price_per_gallon = (fuel_price / 100) * 4.54 # Convert pence/litre to £/gallon
        total_fuel_cost = total_required_fuel * fuel_price_per_gallon
        cost_per_mile = total_fuel_cost / total_dist if total_dist > 0 else 0
        overhead_cost = total_fuel_cost * 0.1
        total_final_cost = total_fuel_cost + overhead_cost


        # --- Feature Importance ---
        feature_importance_data = []
        if hasattr(model, 'feature_importances_'):
            # ... (feature importance logic remains the same) ...
            importances = model.feature_importances_
            feature_names = list(raw_input_df.columns)
            sorted_idx = np.argsort(importances)[::-1][:8]
            top_8_idx = [i for i in sorted_idx if i < len(feature_names)] # Bounds check
            feature_importance_data = [{"name": feature_names[i], "value": float(importances[i])} for i in top_8_idx]
        elif hasattr(model, '_Booster') and hasattr(model._Booster, 'get_score'):
             # Handle feature importance for XGBoost model loaded differently
            try:
                fscore = model._Booster.get_score(importance_type='weight')
                if fscore:
                    sorted_features = sorted(fscore.items(), key=lambda item: item[1], reverse=True)
                    top_features = sorted_features[:8]
                    feature_importance_data = [{"name": name, "value": float(score)} for name, score in top_features]
                else: print("Warning: Model booster get_score returned empty.")
            except Exception as fi_err: print(f"Warning: Could not get feature importance from model booster: {fi_err}")
        else: print("Warning: Model does not have 'feature_importances_' or recognized booster method for importance.")


        # --- Random Values ---
        # (Remains the same)
        good_value_fuel = random.uniform(1.0, total_fuel_cost if total_fuel_cost > 1 else 10)
        insurance_fuel_cost = random.uniform(1.0, good_value_fuel)
        goods_loading_time = random.randint(10, 60)
        is_goods_secured = random.choice(['✔️', '❌'])
        check_safety = random.choice(['✔️', '❌'])

        # --- Prepare Response ---
        response = {
            "success": True,
            "route": {
                "origin": origin_display_name, # Use the display name (GPS or Depot)
                "destination": destination_depot,
                "coordinates": route_points_for_response, # Final polyline points
                "stations": station_points,
                "total_distance": round(total_dist, 2)
            },
            "analytics": {
                # (analytics fields structure remains the same)
                 "average_temperature": round(average_temperature, 2),
                 "rain_classification": rain_classification,
                 "snow_classification": snow_classification,
                 "highway_distance": round(highway_distance, 2),
                 "city_distance": round(city_distance, 2),
                 "efficiency_prediction": round(efficiency_prediction, 2),
                 "total_required_fuel": round(total_required_fuel, 2) if total_required_fuel != float('inf') else "Infinity",
                 "total_fuel_cost": round(total_fuel_cost, 2) if total_required_fuel != float('inf') else "Infinity",
                 "cost_per_mile": round(cost_per_mile, 2) if total_dist > 0 else 0,
                 "overhead_cost": round(overhead_cost, 2) if total_required_fuel != float('inf') else "Infinity",
                 "total_final_cost": round(total_final_cost, 2) if total_required_fuel != float('inf') else "Infinity",
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

    # --- Exception Handling ---
    # (Remains the same)
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error in diesel route API: {str(e)}")
        print(f"Traceback: {error_traceback}")
        return jsonify({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}",
            # "traceback": error_traceback # Avoid in production
        }), 500