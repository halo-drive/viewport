from flask import Flask, render_template, request, Response, Blueprint
import os, json
from anlys import launch_not_all
import pandas as pd
from tracking import main


csv_1 = 'Diesel_Model_Data.csv'

csv_2 = 'Hydrogen_Model_Data.csv'

df = pd.read_csv(csv_1)

df1 = pd.read_csv(csv_2)

row = df.iloc[0]

row1 = df1.iloc[0]

diesel_data = {
    "average_temperature": f"{row['average_temperature']:.2f}",
    "rain_classification": row['rain_classification'],
    "snow_classification": row['snow_classification'],
    "highway_distance": f"{row['highway_distance']:.2f}",
    "city_distance": f"{row['city_distance']:.2f}",
    "efficiency_prediction": f"{row['efficiency_prediction']:.2f}",
    "total_required_fuel": f"{row['total_required_fuel']:.2f}",
    "total_fuel_cost": f"{row['total_fuel_cost']:.2f}",
    "total_cost": f"{row['total_cost']:.2f}",
    "cost_per_mile": f"{row['cost_per_mile']:.2f}",
    "overhead_cost": f"{row['total_cost'] * 0.1:.2f}",
    "total_final_cost": f"{row['total_cost'] + (row['total_cost'] * 0.1):.2f}",# Assuming this is a static value
    "feature_importance": 'static/feature_importance_d.png',  
    "fuel_price": f"{row['fuel_price']:.2f}",
    "good_value_fuel": f"{row['good_value_fuel']:.2f}",
    "insurance_fuel_cost": f"{row['insurance_fuel_cost']:.2f}",
    "goods_loading_time": row['goods_loading_time'],
    "is_goods_secured": row['is_goods_secured'],
    "check_safety": row['check_safety']
}

hydrogen_data = {
    "average_temperature": f"{row1['average_temperature']:.2f}",
    "rain_classification": row1['rain_classification'],
    "snow_classification": row1['snow_classification'],
    "highway_distance": f"{row1['highway_distance']:.2f}",
    "city_distance": f"{row['city_distance']:.2f}",
    "efficiency_prediction": f"{row1['efficiency_prediction']:.2f}",
    "total_required_fuel": f"{row1['total_required_fuel']:.2f}",
    "total_fuel_cost": f"{row1['total_fuel_cost']:.2f}",
    "total_cost": f"{row1['total_cost']:.2f}",
    "cost_per_mile": f"{row1['cost_per_mile']:.2f}",
    "overhead_cost": f"{row1['total_cost'] * 0.1:.2f}",
    "total_final_cost": f"{row1['total_cost'] + (row1['total_cost'] * 0.1):.2f}",
    "feature_importance": 'static/feature_importance_h.png',
    "fuel_price": f"{row1['total_cost']:.2f}",
    "good_value_fuel": f"{row1['good_value_fuel']:.2f}",
    "insurance_fuel_cost": f"{row1['insurance_fuel_cost']:.2f}",
    "goods_loading_time": row1['goods_loading_time'],
    "is_goods_secured": row1['is_goods_secured'],
    "check_safety": row1['check_safety']
}


routemap_bp = Blueprint('routemap', __name__)

@routemap_bp.route('/droute')
def droute():
    return render_template('droute.html')

@routemap_bp.route('/hroute')
def hroute():
    return render_template('hroute.html')

@routemap_bp.route('/routemap')
def routemap():
    return render_template('routemap.html')

@routemap_bp.route('/dieselanalytics')
def dieseanalytics():
    return render_template("dieselanalytics.html", **diesel_data)


@routemap_bp.route('/hydrogenanalytic')
def hydrogenanalytic():
    return render_template("hydrogenanalytics.html", **hydrogen_data)

@routemap_bp.route('/routemaph')
def routemah():
    return render_template('routemaph.html')
