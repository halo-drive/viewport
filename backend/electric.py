from flask import Blueprint, render_template, request, Response, jsonify
import random
import os
import pandas as pd
import matplotlib.pyplot as plt
from electric_routing_here import getdata
from config import Config

# Create Blueprint
electric_bp = Blueprint('electric', __name__)

# Vehicle range in miles (based on battery capacity)
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

# Battery capacity in kWh
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

def convert_time_to_window(time_str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    if 4 <= hours < 12:
        return "morning"
    elif 12 <= hours < 20:
        return "noon"
    else:
        return "night"

@electric_bp.route('/electricanalytics', methods=['GET', 'POST'])
def electricanalytics():
    try:
        # Get form data
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
        initial_charge = float(request.form.get('initial_charge', 80))  # Default to 80% if not provided
        
        # Get vehicle range and battery capacity
        vehicle_max_range = vehicle_range.get(vehicle_type, 130)  # Default to 130 miles
        battery_cap = battery_capacity.get(vehicle_type, 200)  # Default to 200 kWh
        
        # Calculate how much charge is available (as a percentage of maximum range)
        available_range = vehicle_max_range * (initial_charge / 100)
        
        # Calculate total payload
        total_payload = pallets * 0.88
        
        # Base efficiency calculation (miles per kWh)
        base_efficiency = {
            'Volvo FE Electric': 0.60,
            'DAF CF Electric': 0.65,
            'Mercedes eActros': 0.67,
            'MAN eTGM': 0.60,
            'Renault E-Tech D': 0.63,
            'Scania BEV': 0.67,
            'Volvo FL Electric': 0.65,
            'FUSO eCanter': 0.75,
            'Freightliner eCascadia': 0.48,
            'BYD ETM6': 0.64
        }
        
        # Get base efficiency and apply adjustment factors
        efficiency_mi_per_kwh = base_efficiency.get(vehicle_type, 0.6)  # Default to 0.6 mi/kWh for trucks
        
        # Simple factors for efficiency adjustment
        if pallets > 15:
            efficiency_mi_per_kwh *= 0.85  # 15% less efficient with heavier load
        
        if Vehicle_age > 2:
            efficiency_mi_per_kwh *= (1 - (Vehicle_age * 0.02))  # 2% degradation per year
        
        # Create route map
        getdata(Origin_depot_uk, Destination_depot_uk)
        
        # For simplicity, we'll use estimated distances instead of actually calculating
        # In a real implementation, these would come from the routing module
        highway_distance = random.uniform(50, 150)
        city_distance = random.uniform(10, 50)
        total_dist = highway_distance + city_distance
        
        # Calculate energy usage
        total_required_energy = total_dist / efficiency_mi_per_kwh
        
        # Calculate costs (70p per kWh)
        energy_cost_per_kwh = 0.70  # £0.70 per kWh
        total_energy_cost = total_required_energy * energy_cost_per_kwh
        cost_per_mile = total_energy_cost / total_dist
        overhead_cost = total_energy_cost * 0.1  # 10% overhead
        total_cost = total_energy_cost + overhead_cost
        
        # Random values for other metrics 
        temperature = random.uniform(2, 25)
        rain_options = ["Low", "Medium", "Heavy"]
        snow_options = ["Low", "Medium", "Heavy"]
        rain_classification = random.choice(rain_options)
        snow_classification = random.choice(snow_options)
        
        # Random operational metrics
        good_value_energy = random.uniform(total_energy_cost * 0.4, total_energy_cost * 0.8)
        insurance_energy_cost = random.uniform(good_value_energy * 0.5, good_value_energy) 
        goods_loading_time = random.randint(10, 60)
        is_goods_secured = random.choice(['✔️', '❌'])
        check_safety = random.choice(['✔️', '❌'])
        
        # Create feature importance chart for visualization
        fig = plt.figure(figsize=(12, 6))
        ax = fig.add_subplot()

        # Set a dark navy blue background for the figure and plot area
        fig.patch.set_facecolor('#000128')  # Dark navy color
        ax.set_facecolor('#000128')         # Dark navy color

        # Define importance values for key features
        feature_names = [
            'Distance_highway', 'Avg_temp', 'Vehicle_age', 
            'Avg_traffic_congestion', 'Avg_Speed_mph', 
            'Distance_city', 'Goods_weight', 'Avg_Precipitation'
        ]
        
        feature_values = [0.25, 0.21, 0.15, 0.12, 0.10, 0.08, 0.05, 0.04]
        
        # Sort by importance (descending)
        sorted_indices = sorted(range(len(feature_values)), key=lambda i: feature_values[i], reverse=True)
        sorted_names = [feature_names[i] for i in sorted_indices]
        sorted_values = [feature_values[i] for i in sorted_indices]

        # Create the horizontal bar plot with white bars
        ax.barh(range(len(sorted_names)), sorted_values, align='center', color='white')
        ax.set_yticks(range(len(sorted_names)))
        ax.set_yticklabels(sorted_names, color='white')
        ax.set_title('Top Features by Importance', color='white')
        ax.set_xlabel('Feature Importance', color='white')

        # Change tick label colors to white for visibility
        ax.tick_params(axis='y', colors='white')
        ax.tick_params(axis='x', colors='white')

        plt.tight_layout()
        plt.savefig('static/feature_importance_e.png')

        # Create a DataFrame for this analysis
        model_data = {
            'total_dist': [total_dist],
            'vehicle_age': [Vehicle_age],
            'goods_weight': [total_payload],
            'city_distance': [city_distance],
            'highway_distance': [highway_distance],
            'avg_speed_mph': [65],  # Default average speed
            'average_temperature': [temperature],
            'rain_classification': [rain_classification],
            'snow_classification': [snow_classification],
            'traffic_severity': ['medium'],  # Default medium traffic
            'start_place': [Origin_depot],
            'destination_place': [Destination_depot],
            'vehicle_type': [vehicle_type],
            'energy_price_per_kwh': [energy_cost_per_kwh],
            'total_energy_cost': [total_energy_cost],
            'efficiency_prediction': [efficiency_mi_per_kwh],
            'total_required_energy': [total_required_energy],
            'total_cost': [total_cost],
            'cost_per_mile': [cost_per_mile],
            'good_value_energy': [good_value_energy],
            'insurance_energy_cost': [insurance_energy_cost],
            'goods_loading_time': [goods_loading_time],
            'is_goods_secured': [is_goods_secured],
            'check_safety': [check_safety]
        }
        
        # Create a DataFrame with the specified column names
        csv_columns = [
            'total_dist', 'vehicle_age', 'goods_weight', 'city_distance', 'highway_distance',
            'avg_speed_mph', 'rain_classification', 'snow_classification', 'traffic_severity',
            'start_place', 'destination_place', 'vehicle_type', 'energy_price_per_kwh', 'average_temperature',
            'total_energy_cost', 'efficiency_prediction', 'insurance_energy_cost', 'good_value_energy', 
            'cost_per_mile', 'total_cost', 'total_required_energy', 'goods_loading_time', 'is_goods_secured', 
            'check_safety'
        ]
        
        df = pd.DataFrame(model_data, columns=csv_columns)
        
        # Save the DataFrame to a CSV file
        csv_filename = 'Electric_Model_Data.csv'
        df.to_csv(csv_filename)
        
        # Prepare data for the template
        electric_data = {
            "average_temperature": f"{temperature:.2f}",
            "rain_classification": rain_classification,
            "snow_classification": snow_classification,
            "highway_distance": f"{highway_distance:.2f}",
            "city_distance": f"{city_distance:.2f}",
            "efficiency_prediction": f"{efficiency_mi_per_kwh:.2f}",
            "total_required_fuel": f"{total_required_energy:.2f}",  # kWh instead of fuel
            "total_fuel_cost": f"{total_energy_cost:.2f}",
            "total_cost": f"{total_cost:.2f}",
            "cost_per_mile": f"{cost_per_mile:.2f}",
            "overhead_cost": f"{overhead_cost:.2f}",
            "total_final_cost": f"{total_cost:.2f}",
            "feature_importance": 'static/feature_importance_e.png',
            "fuel_price": f"{energy_cost_per_kwh:.2f}",
            "good_value_fuel": f"{good_value_energy:.2f}",
            "insurance_fuel_cost": f"{insurance_energy_cost:.2f}",
            "goods_loading_time": goods_loading_time,
            "is_goods_secured": is_goods_secured,
            "check_safety": check_safety
        }

        return render_template("electricanalytics.html", **electric_data)

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in electric analytics: {str(e)}")
        print(f"Traceback: {error_traceback}")
        return f"Error in processing the request: {str(e)}"

@electric_bp.route('/electric')
def electric():
    return render_template("electric.html")