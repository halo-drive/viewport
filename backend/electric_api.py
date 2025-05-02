# electric_api.py
from flask import Blueprint, request, jsonify
import random
import pandas as pd
import numpy as np
import traceback
# Assuming tracking.py provides geocode_maps_co for non-GPS cases
from tracking import get_coordinates as geocode_maps_co, calculate_distances, get_route_traffic_data, get_weather_data
# Import the modified function from electric_routing_here
from electric_routing_here import get_here_directions, get_coordinates as here_get_coordinates, get_charging_station_coordinates, get_route_with_charging_stations
from config import Config

# (Keep blueprint init, encodings, vehicle specs, helpers as before)
# ...
electric_api_bp = Blueprint('electric_api', __name__)
vehicle_type_encoded = ['Volvo FE Electric', 'DAF CF Electric', 'Mercedes eActros', 'MAN eTGM', 'Renault E-Tech D', 'Scania BEV', 'Volvo FL Electric', 'FUSO eCanter', 'Freightliner eCascadia', 'BYD ETM6']
origin_encoded = {'Aberdeen': 0, 'Birmingham': 1, 'Cardiff': 2, 'Glasgow': 3, 'Leeds': 4, 'Liverpool': 5, 'London': 6, 'Manchester': 7}
dispatch_encoded = {'morning': 0, 'night': 1, 'noon': 2}
traffic_congestion_encoded = {'low': 0, 'medium': 1, 'high': 2}
temp_encoded = {'low': 0, 'medium': 1, 'high': 2}
precipitation_encoded = {'low': 0, 'medium': 1, 'high': 2}
snow_encoded = {'low': 0, 'medium': 1, 'high': 2}
battery_capacity = { 'Volvo FE Electric': 200, 'DAF CF Electric': 222, 'Mercedes eActros': 240, 'MAN eTGM': 185, 'Renault E-Tech D': 200, 'Scania BEV': 230, 'Volvo FL Electric': 165, 'FUSO eCanter': 120, 'Freightliner eCascadia': 475, 'BYD ETM6': 210 }
vehicle_range = { 'Volvo FE Electric': 120, 'DAF CF Electric': 140, 'Mercedes eActros': 160, 'MAN eTGM': 120, 'Renault E-Tech D': 125, 'Scania BEV': 155, 'Volvo FL Electric': 110, 'FUSO eCanter': 90, 'Freightliner eCascadia': 230, 'BYD ETM6': 135 }
base_efficiency = { 'Volvo FE Electric': 1800, 'DAF CF Electric': 1750, 'Mercedes eActros': 1650, 'MAN eTGM': 1700, 'Renault E-Tech D': 1750, 'Scania BEV': 1650, 'Volvo FL Electric': 1650, 'FUSO eCanter': 1400, 'Freightliner eCascadia': 2100, 'BYD ETM6': 1700 } # Wh/mile
def convert_time_to_window(time_str):
    # (code unchanged)
    try:
        hours = int(time_str.split(':')[0])
        if 4 <= hours < 12: return "morning"
        elif 12 <= hours < 20: return "noon"
        else: return "night"
    except: return "noon" # Default
#...

@electric_api_bp.route('/api/electric/route', methods=['POST'])
def electric_route_api():
    try:
        # --- Get Form Data (Unchanged) ---
        pallets = request.form.get('pallets', type=float, default=20.0)
        vehicle_model = request.form.get('vehicleModel', 'Volvo FE Electric')
        destination_depot = request.form.get('destinationDepot')
        vehicle_age = request.form.get('vehicleAge', type=float, default=3.0)
        dispatch_time_str = request.form.get('dispatchTime', '12:00:00')
        target_date = request.form.get('journeyDate')

        # --- Handle Origin (GPS or Depot Name) (Same logic as diesel_api) ---
        origin_lat = request.form.get('originLat', type=float)
        origin_lon = request.form.get('originLon', type=float)
        origin_depot_name = request.form.get('originDepot')

        start_coords = None # (lat, lon)
        origin_display_name = None # For response/log

        if origin_lat is not None and origin_lon is not None:
            start_coords = (origin_lat, origin_lon)
            origin_display_name = "Current Location (GPS)"
            print(f"Using GPS origin: {start_coords}")
        elif origin_depot_name:
            origin_display_name = origin_depot_name
            coords_result = here_get_coordinates(f"{origin_depot_name}, UK", Config.HERE_API_KEY)
            if coords_result and coords_result[0] is not None:
                 start_coords = coords_result
                 print(f"Using Depot origin: {origin_depot_name}, Coords: {start_coords}")
            else:
                 # Fallback geocode?
                 print(f"Warning: HERE geocode failed for {origin_depot_name}, trying fallback.")
                 start_coords = geocode_maps_co(f"{origin_depot_name}, UK")
                 if not (start_coords and start_coords[0] is not None):
                      return jsonify({"success": False, "error": f"Could not geocode origin depot: {origin_depot_name}"}), 400
                 print(f"Using Depot origin (fallback geocode): {origin_depot_name}, Coords: {start_coords}")
        else:
            return jsonify({"success": False, "error": "Missing origin information"}), 400

        # Geocode destination (Unchanged)
        if not destination_depot: return jsonify({"success": False, "error": "Missing destination depot"}), 400
        if not target_date: return jsonify({"success": False, "error": "Missing journey date"}), 400
        dest_coords = here_get_coordinates(f"{destination_depot}, UK", Config.HERE_API_KEY)
        if not dest_coords or dest_coords[0] is None: return jsonify({"success": False, "error": f"Could not geocode destination depot: {destination_depot}"}), 400
        print(f"Destination: {destination_depot}, Coords: {dest_coords}")
        # --- End Coordinate Handling ---

        dispatch_time = convert_time_to_window(dispatch_time_str)
        total_payload = pallets * 0.88
        goods_weight = total_payload
        api_key = Config.HERE_API_KEY


        # --- Get Route & Stations (MODIFIED CALL) ---
        try:
            # Call the modified function with coordinate tuples directly
            # Returns: original_route_list, direct_polyline_points, charging_station_coords
            _, direct_polyline_points, charging_station_coords = get_route_with_charging_stations(
                 api_key,
                 origin_coords=start_coords, # Pass tuple (lat, lon)
                 destination_coords=dest_coords # Pass tuple (lat, lon)
            )
        except ValueError as ve:
             print(f"Error getting EV route/stations from HERE: {ve}")
             return jsonify({"success": False, "error": f"Failed to calculate EV route: {ve}"}), 500

        # Use the direct polyline points initially
        route_points_for_response = direct_polyline_points if direct_polyline_points else []

        print(f"Found {len(charging_station_coords)} charging stations along the route")
        station_points = [{"name": f"Charging Station {i+1}", "coordinates": coord} for i, coord in enumerate(charging_station_coords)]

        # --- Rebuild combined route polyline if stations found (MODIFIED to use coords) ---
        # Convert coord tuples to 'lat,lon' strings for get_here_directions
        origin_coords_str = f"{start_coords[0]},{start_coords[1]}"
        dest_coords_str = f"{dest_coords[0]},{dest_coords[1]}"

        combined_route_points = []
        if charging_station_coords:
            # Origin to first station
            first_station_str = f"{charging_station_coords[0][0]},{charging_station_coords[0][1]}"
            origin_to_first = get_here_directions(origin_coords_str, first_station_str, api_key)
            if origin_to_first: combined_route_points.extend(origin_to_first)

            # Between stations
            for i in range(len(charging_station_coords) - 1):
                 current_str = f"{charging_station_coords[i][0]},{charging_station_coords[i][1]}"
                 next_s_str = f"{charging_station_coords[i+1][0]},{charging_station_coords[i+1][1]}"
                 station_to_station = get_here_directions(current_str, next_s_str, api_key)
                 if station_to_station: combined_route_points.extend(station_to_station)

            # Last station to destination
            last_station_str = f"{charging_station_coords[-1][0]},{charging_station_coords[-1][1]}"
            last_to_dest = get_here_directions(last_station_str, dest_coords_str, api_key)
            if last_to_dest: combined_route_points.extend(last_to_dest)

             # Use combined path if successfully generated
            if combined_route_points:
                route_points_for_response = combined_route_points
            else:
                print("Warning: Failed to generate combined EV route through stations, using direct route.")
                # Keep route_points_for_response as direct_polyline_points

        # --- Analytics Calculations (Unchanged) ---
        city_distance, highway_distance = calculate_distances(start_coords, dest_coords)
        route_coordinates_for_weather, traffic_delay = get_route_traffic_data(start_coords, dest_coords)
        traffic_severity = "high" if traffic_delay > 30 else "medium" if traffic_delay > 7 else "low"
        weather_api_key = Config.WEATHER_API_KEY
        average_temperature, snow_classification, rain_classification = get_weather_data(weather_api_key, route_coordinates_for_weather, target_date)

        # --- Calculate Efficiency (Rule-based) (Unchanged) ---
        total_dist = city_distance + highway_distance
        efficiency_wh_per_mile = base_efficiency.get(vehicle_model, 1700)
        if average_temperature < 5: efficiency_wh_per_mile *= 1.30
        elif average_temperature < 10: efficiency_wh_per_mile *= 1.15
        if traffic_severity == "high": efficiency_wh_per_mile *= 1.20
        elif traffic_severity == "medium": efficiency_wh_per_mile *= 1.10
        if rain_classification.lower() == "heavy" or snow_classification.lower() == "heavy": efficiency_wh_per_mile *= 1.15
        elif rain_classification.lower() == "medium" or snow_classification.lower() == "medium": efficiency_wh_per_mile *= 1.05
        if pallets > 15: efficiency_wh_per_mile *= 1.10
        if vehicle_age > 2: efficiency_wh_per_mile *= (1 + (vehicle_age * 0.02))
        efficiency_prediction = 1000 / efficiency_wh_per_mile if efficiency_wh_per_mile else 0
        total_required_energy = total_dist / efficiency_prediction if efficiency_prediction else float('inf')

        # --- Cost Calculation (Unchanged) ---
        energy_price_per_kwh = 0.70
        total_energy_cost = total_required_energy * energy_price_per_kwh
        cost_per_mile = total_energy_cost / total_dist if total_dist else 0
        overhead_cost = total_energy_cost * 0.1
        total_final_cost = total_energy_cost + overhead_cost

        # --- Feature Importance (Hardcoded Example) (Unchanged) ---
        feature_importance_data = [
            {"name": "Distance_highway", "value": 25}, {"name": "Avg_temp", "value": 21},
            {"name": "Vehicle_age", "value": 15}, {"name": "Avg_traffic_congestion", "value": 12},
            {"name": "Avg_Speed_mph", "value": 10}, {"name": "Distance_city", "value": 8},
            {"name": "Goods_weight", "value": 5}, {"name": "Avg_Precipitation", "value": 4}
        ]
        feature_importance_data.sort(key=lambda x: x['value'], reverse=True)

        # --- Random Values (Unchanged) ---
        good_value_energy = random.uniform(total_energy_cost * 0.4, total_energy_cost * 0.8) if total_energy_cost > 0 else 0
        insurance_energy_cost = random.uniform(good_value_energy * 0.5, good_value_energy) if good_value_energy > 0 else 0
        goods_loading_time = random.randint(10, 60)
        is_goods_secured = random.choice(['✔️', '❌'])
        check_safety = random.choice(['✔️', '❌'])

        # --- Prepare Response (Use route_points_for_response) ---
        response = {
            "success": True,
            "route": {
                "origin": origin_display_name, # GPS or Name
                "destination": destination_depot,
                "coordinates": route_points_for_response, # Final polyline points
                "stations": station_points,
                "total_distance": round(total_dist, 2)
            },
            "analytics": {
                # (analytics fields unchanged)
                 "average_temperature": round(average_temperature, 2),
                 "rain_classification": rain_classification,
                 "snow_classification": snow_classification,
                 "highway_distance": round(highway_distance, 2),
                 "city_distance": round(city_distance, 2),
                 "efficiency_prediction": round(efficiency_prediction, 2),
                 "total_required_fuel": round(total_required_energy, 2),
                 "total_fuel_cost": round(total_energy_cost, 2),
                 "cost_per_mile": round(cost_per_mile, 2),
                 "overhead_cost": round(overhead_cost, 2),
                 "total_final_cost": round(total_final_cost, 2),
                 "fuel_price": energy_price_per_kwh,
                 "good_value_fuel": round(good_value_energy, 2),
                 "insurance_fuel_cost": round(insurance_energy_cost, 2),
                 "goods_loading_time": goods_loading_time,
                 "is_goods_secured": is_goods_secured,
                 "check_safety": check_safety,
                 "featureImportance": feature_importance_data
            }
        }

        return jsonify(response)

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"Error in electric route API: {str(e)}")
        print(f"Traceback: {error_traceback}")
        return jsonify({"success": False, "error": str(e), "traceback": error_traceback}), 500