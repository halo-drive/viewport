from flask import Blueprint, request, jsonify
import random
import pandas as pd
import numpy as np
from tracking import get_coordinates, calculate_distances, get_route_traffic_data, get_weather_data
from electric_routing_here import get_here_directions, get_coordinates as here_get_coordinates, get_charging_station_coordinates, get_route_with_charging_stations
from config import Config

# Initialize the blueprint
electric_api_bp = Blueprint('electric_api', __name__)

# Encodings for the data processing (similar to diesel but adapted for electric)
vehicle_type_encoded = ['Volvo FE Electric', 'DAF CF Electric', 'Mercedes eActros', 
                        'MAN eTGM', 'Renault E-Tech D', 'Scania BEV',
                        'Volvo FL Electric', 'FUSO eCanter', 'Freightliner eCascadia', 'BYD ETM6']
                        
origin_encoded = {'Aberdeen': 0, 'Birmingham': 1, 'Cardiff': 2, 'Glasgow': 3,
                  'Leeds': 4, 'Liverpool': 5, 'London': 6, 'Manchester': 7}
                  
dispatch_encoded = {'morning': 0, 'night': 1, 'noon': 2}
traffic_congestion_encoded = {'low': 0, 'medium': 1, 'high': 2}
temp_encoded = {'low': 0, 'medium': 1, 'high': 2}
precipitation_encoded = {'low': 0, 'medium': 1, 'high': 2}
snow_encoded = {'low': 0, 'medium': 1, 'high': 2}

# Vehicle battery capacity in kWh
battery_capacity = {
    'Volvo FE Electric': 200,
    'DAF CF Electric': 222,
    'Mercedes eActros': 240,
    'MAN eTGM': 185,
    'Renault E-Tech D': 200,
    'Scania BEV': 230,
    'Volvo FL Electric': 165,
    'FUSO eCanter': 120,
    'Freightliner eCascadia': 475,
    'BYD ETM6': 210
}

# Average range in miles
vehicle_range = {
    'Volvo FE Electric': 120,
    'DAF CF Electric': 140,
    'Mercedes eActros': 160,
    'MAN eTGM': 120,
    'Renault E-Tech D': 125,
    'Scania BEV': 155,
    'Volvo FL Electric': 110,
    'FUSO eCanter': 90,
    'Freightliner eCascadia': 230,
    'BYD ETM6': 135
}

def convert_time_to_window(time_str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    if 4 <= hours < 12:
        return "morning"
    elif 12 <= hours < 20:
        return "noon"
    else:
        return "night"

@electric_api_bp.route('/api/electric/route', methods=['POST'])
def electric_route_api():
    try:
        # Get form data
        pallets = float(request.form['pallets'])
        vehicle_model = request.form['vehicleModel']
        origin_depot = request.form['originDepot']
        destination_depot = request.form['destinationDepot']
        vehicle_age = float(request.form['vehicleAge'])
        dispatch_time = convert_time_to_window(request.form['dispatchTime'])
        target_date = request.form['journeyDate']
        
        print(f"\n\n===== ELECTRIC ROUTE REQUEST =====")
        print(f"From: {origin_depot} to {destination_depot}")
        print(f"Vehicle: {vehicle_model}, Age: {vehicle_age}, Pallets: {pallets}")
        print(f"Dispatch time: {request.form['dispatchTime']} ({dispatch_time})")
        
        start_place = f"{origin_depot}, UK"
        destination_place = f"{destination_depot}, UK"
        total_payload = pallets * 0.88
        goods_weight = total_payload
        
        # Get coordinates and route with charging stations
        api_key = Config.HERE_API_KEY
        
        route_coords, route_points, charging_station_coords = get_route_with_charging_stations(
            api_key, origin_city=start_place, destination_city=destination_place
        )
        
        print(f"Found {len(charging_station_coords)} charging stations along the route")
        
        # Format stations for response
        station_points = []
        for i, charge_coord in enumerate(charging_station_coords):
            station_points.append({
                "name": f"Charging Station {i+1}",
                "coordinates": charge_coord
            })

        # Create combined route that passes through stations
        combined_route_points = []
        if len(charging_station_coords) > 0:
            # Get origin and destination coordinates
            start_coords_here = here_get_coordinates(start_place, api_key)
            dest_coords_here = here_get_coordinates(destination_place, api_key)
            
            # Start with origin to first station
            first_station = charging_station_coords[0]
            
            origin_to_first = get_here_directions(
                f"{start_coords_here[0]},{start_coords_here[1]}", 
                f"{first_station[0]},{first_station[1]}", 
                api_key
            )
            
            if origin_to_first:
                combined_route_points.extend(origin_to_first)
            
            # Add routes between stations
            for i in range(len(charging_station_coords) - 1):
                current = charging_station_coords[i]
                next_station = charging_station_coords[i+1]
                
                station_to_station = get_here_directions(
                    f"{current[0]},{current[1]}",
                    f"{next_station[0]},{next_station[1]}",
                    api_key
                )
                
                if station_to_station:
                    combined_route_points.extend(station_to_station)
            
            # Add last station to destination
            last_station = charging_station_coords[-1]
            
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
        print(f"City distance: {city_distance} miles, Highway distance: {highway_distance} miles")
        
        # Get route traffic data
        route_coordinates, traffic_delay = get_route_traffic_data(start_coords, destination_coords)
        
        # Define traffic severity
        traffic_severity = "high" if traffic_delay > 30 else "medium" if traffic_delay > 7 else "low"
        print(f"Traffic severity: {traffic_severity}")
        
        # Get weather data
        weather_api_key = Config.WEATHER_API_KEY
        average_temperature, snow_classification, rain_classification = get_weather_data(weather_api_key, route_coordinates, target_date)
        print(f"Weather: Temp: {average_temperature}°C, Rain: {rain_classification}, Snow: {snow_classification}")
        
        # Calculate efficiency - Instead of ML model, we use fixed values and adjustments based on conditions
        total_dist = city_distance + highway_distance
        
        # Base efficiency in Wh/mile (lower is better)
        base_efficiency = {
            'Volvo FE Electric': 1800,
            'DAF CF Electric': 1750,
            'Mercedes eActros': 1650,
            'MAN eTGM': 1700,
            'Renault E-Tech D': 1750,
            'Scania BEV': 1650,
            'Volvo FL Electric': 1650,
            'FUSO eCanter': 1400,
            'Freightliner eCascadia': 2100,
            'BYD ETM6': 1700
        }
        
        # Get base efficiency for the selected vehicle
        efficiency_wh_per_mile = base_efficiency.get(vehicle_model, 1700)  # Default to 1700 Wh/mile
        
        # Adjust for temperature (cold weather reduces efficiency)
        if average_temperature < 5:
            efficiency_wh_per_mile *= 1.3  # 30% worse efficiency in very cold weather
        elif average_temperature < 10:
            efficiency_wh_per_mile *= 1.15  # 15% worse efficiency in cold weather
        
        # Adjust for traffic (stop and go traffic reduces efficiency)
        if traffic_severity == "high":
            efficiency_wh_per_mile *= 1.2  # 20% worse in heavy traffic
        elif traffic_severity == "medium":
            efficiency_wh_per_mile *= 1.1  # 10% worse in medium traffic
        
        # Adjust for weather conditions (rain and snow affect efficiency)
        if rain_classification.lower() == "heavy" or snow_classification.lower() == "heavy":
            efficiency_wh_per_mile *= 1.15  # 15% worse in heavy rain/snow
        elif rain_classification.lower() == "medium" or snow_classification.lower() == "medium":
            efficiency_wh_per_mile *= 1.05  # 5% worse in medium rain/snow
        
        # Adjust for payload weight
        if pallets > 15:
            efficiency_wh_per_mile *= 1.1  # 10% worse with heavy load
        
        # Adjust for vehicle age (battery degradation)
        if vehicle_age > 2:
            efficiency_wh_per_mile *= (1 + (vehicle_age * 0.02))  # 2% worse per year of age
        
        # Efficiency in miles per kWh
        efficiency_prediction = 1000 / efficiency_wh_per_mile  # Convert from Wh/mile to miles/kWh
        
        # Total energy required in kWh
        total_required_energy = total_dist / efficiency_prediction
        
        # Cost calculation (70p per kWh)
        total_energy_cost = total_required_energy * 0.70  # £0.70 per kWh
        cost_per_mile = total_energy_cost / total_dist
        overhead_cost = total_energy_cost * 0.1  # 10% overhead
        total_cost = total_energy_cost + overhead_cost
        
        # Log efficiency calculation
        print("\n\n===== ELECTRIC MODEL CALCULATION =====")
        print(f"Total distance: {total_dist:.2f} miles")
        print(f"Base efficiency: {base_efficiency.get(vehicle_model, 1700)} Wh/mile")
        print(f"Adjusted efficiency: {efficiency_wh_per_mile:.2f} Wh/mile ({efficiency_prediction:.2f} miles/kWh)")
        print(f"Total energy required: {total_required_energy:.2f} kWh")
        print(f"Energy cost: £{total_energy_cost:.2f} (at £0.70 per kWh)")
        print(f"Cost per mile: £{cost_per_mile:.2f}")
        print("======================================\n")
        
        # Generate feature importance data
        feature_importance_data = [
            {"name": "Distance_highway", "value": 25},
            {"name": "Avg_temp", "value": 21},
            {"name": "Vehicle_age", "value": 15},
            {"name": "Avg_traffic_congestion", "value": 12},
            {"name": "Avg_Speed_mph", "value": 10},
            {"name": "Distance_city", "value": 8},
            {"name": "Goods_weight", "value": 5},
            {"name": "Avg_Precipitation", "value": 4}
        ]
        
        # Random values for other metrics
        good_value_energy = random.uniform(total_energy_cost * 0.4, total_energy_cost * 0.8)
        insurance_energy_cost = random.uniform(good_value_energy * 0.5, good_value_energy) 
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
                "total_required_fuel": round(total_required_energy, 2),  # kWh instead of fuel
                "total_fuel_cost": round(total_energy_cost, 2),
                "total_cost": round(total_cost, 2),
                "cost_per_mile": round(cost_per_mile, 2),
                "overhead_cost": round(overhead_cost, 2),
                "total_final_cost": round(total_cost, 2),
                "fuel_price": 0.70,  # £0.70 per kWh
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
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in electric route API: {str(e)}")
        print(f"Traceback: {error_traceback}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": error_traceback
        }), 500