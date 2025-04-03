import { useContext } from 'react';
import { AppContext } from '../AppContext';
import AnalyticsChart from './AnalyticsChart';

// Import icons
import goods from "../assets/goods.png";
import insurance from "../assets/insurance.png";
import fuel from "../assets/fuel.png";
import overhead from "../assets/overhead.png";
import temperature from "../assets/temperature.png";
import precipitation from "../assets/precipitation.png";
import snow from "../assets/snow.png";
import highway from "../assets/highway.png";
import city from "../assets/city.png";
import cross from "../assets/cross.png";
import check from "../assets/check.png";
import time from "../assets/time.png";
import StartForm from './StartForm';

export default function SlidingPanel() {
  const { activePane, analyticsData } = useContext(AppContext);

  if (!activePane) return null;
  
  // Don't render energy pane from here, it's now handled separately
  if (activePane === "energy") return null;
  
  return (
    <div className={`sliding-pane ${activePane === "analytics" ? "analytics-pane" : ""} ${activePane === "start" ? "start-pane" : ""}`}>
      <div className="pane-header">
        <h1>{activePane}</h1>
      </div>
      <div className="pane-content">
        {activePane === "start" && (
          <div className="start-container">
            <StartForm />
          </div>
        )}
        
        {activePane === "cost" && (
          <div className="cost-container">
              <div className="cost-item">
                  <span className="cost-label">Goods Value:</span>
                  <img src={goods} alt="Goods" className="cost-icon" />
                  <span className="cost-value">£{analyticsData ? analyticsData.good_value_fuel.toFixed(2) : "--"}</span>
              </div>
              <div className="cost-item">
                   <span className="cost-label">Insurance Cost:</span>
                   <img src={insurance} alt="Insurance" className="cost-icon" />
                  <span className="cost-value">£{analyticsData ? analyticsData.insurance_fuel_cost.toFixed(2) : "--"}</span>
              </div>
              <div className="cost-item">
                  <span className="cost-label">Fuel Cost:</span>
                  <img src={fuel} alt="Fuel" className="cost-icon" />
                  <span className="cost-value">£{analyticsData ? analyticsData.total_fuel_cost.toFixed(2) : "--"}</span>
              </div>
              <div className="cost-item">
                  <span className="cost-label">Overhead Cost:</span>
                  <img src={overhead} alt="Overhead" className="cost-icon" />
                  <span className="cost-value">£{analyticsData ? analyticsData.overhead_cost.toFixed(2) : "--"}</span>
              </div>
          </div>
        )}
        
        {activePane === "journey" && (
          <div className="journey-container">
              <div className="journey-item">
                  <span className="journey-label">Avg. Temp.:</span>
                  <img src={temperature} alt="Temperature" className="journey-icon" />
                  <span className="journey-value">{analyticsData ? `${analyticsData.average_temperature}°C` : "--"}</span>
              </div>
              <div className="journey-item">
                  <span className="journey-label">Avg. Precipitation:</span>
                  <img src={precipitation} alt="Precipitation" className="journey-icon" />
                  <span className="journey-value">{analyticsData ? analyticsData.rain_classification : "--"}</span>
              </div>
              <div className="journey-item">
                  <span className="journey-label">Avg. Snow:</span>
                  <img src={snow} alt="Snow" className="journey-icon" />
                  <span className="journey-value">{analyticsData ? analyticsData.snow_classification : "--"}</span>
              </div>
              <div className="journey-item">
                  <span className="journey-label">Highway:</span>
                  <img src={highway} alt="Highway" className="journey-icon" />
                  <span className="journey-value">{analyticsData ? `${analyticsData.highway_distance} miles` : "--"}</span>
              </div>
              <div className="journey-item">
                  <span className="journey-label">City:</span>
                  <img src={city} alt="City" className="journey-icon" />
                  <span className="journey-value">{analyticsData ? `${analyticsData.city_distance} miles` : "--"}</span>
              </div>
        </div>
        )}
        
        {activePane === "fleet" && (
          <div className="fleet-container">
          <div className="fleet-item">
            <span className="fleet-label">Goods Secured:</span>
            <span className="fleet-value">
              <img src={analyticsData && analyticsData.is_goods_secured === '✔️' ? check : cross} alt="Status" className="status-icon" />
            </span>
          </div>
          <div className="fleet-item">
            <span className="fleet-label">Safety Check:</span>
            <span className="fleet-value">
              <img src={analyticsData && analyticsData.check_safety === '✔️' ? check : cross} alt="Status" className="status-icon" />
            </span>
          </div>
          <div className="fleet-item">
            <span className="fleet-label">Loading Time:</span>
            <img src={time} alt="time" className="fleet-icon" />
            <span className="fleet-value">{analyticsData ? `${analyticsData.goods_loading_time} mins` : "--"}</span>
          </div>
        </div>
        )}
        
        {activePane === "analytics" && (
          <div>
            <p className="analytics-header">Top 8 Features by Importance</p>
            <AnalyticsChart />
          </div>
        )}
      </div>
    </div>
  );
}