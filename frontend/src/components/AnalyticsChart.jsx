import React, { useState, useEffect, useContext } from 'react';
import { AppContext } from '../AppContext';

// Label mapping specifically for feature importance chart
const featureImportanceLabelMap = {
  'Distance_highway': 'Distance Highway',
  'Distance_city': 'Distance City',
  'Avg_temp': 'Temperature',
  'dispatch_time': 'Dispatch Time',
  'Avg_traffic_congestion': 'Traffic Congestion',
  'Vehicle_age': 'Vehicle Age',
  'Avg_Speed_mph': 'Average Speed',
  'Goods_weight': 'Goods Weight',
  'Avg_Precipitation': 'Precipitation',
  'Avg_snow': 'Snow Level',
  'total_payload': 'Total Payload',
  'range': 'Range'
}

export default function AnalyticsChart() {
  const { analyticsData } = useContext(AppContext);
  const [featureData, setFeatureData] = useState([]);
  const [animate, setAnimate] = useState(false);

  // Function to get display label
  const getDisplayLabel = (backendLabel) => {
    return featureImportanceLabelMap[backendLabel] || backendLabel;
  };

  useEffect(() => {
    if (analyticsData && analyticsData.featureImportance) {
      const maxValue = Math.max(...analyticsData.featureImportance.map(item => item.value));
      
      const formattedData = analyticsData.featureImportance.map((item, i) => ({
        id: i + 1,
        label: getDisplayLabel(item.name),
        value: Math.round(item.value),
        scaledValue: Math.round((item.value / maxValue) * 100),
        colorClass: `bar-color-${i + 1}`
      }));
      
      setFeatureData(formattedData);
    } else {
      setFeatureData([]);
    }
    
    const timer = setTimeout(() => {
      setAnimate(true);
    }, 100);
    
    return () => clearTimeout(timer);
  }, [analyticsData]);

  if (featureData.length === 0) {
    return <div className="analytics-chart">Loading feature importance data...</div>;
  }

  return (
    <div className="analytics-chart">      
      {featureData.map((item, index) => (
        <div key={item.id} className="bar-row">
          <div className="bar-label">{item.label}</div>
          <div className="bar-container">
            <div 
              className={`bar-fill ${item.colorClass}`} 
              style={{ 
                width: animate ? `${item.scaledValue}%` : '0%',
                transitionDelay: `${index * 0.1}s`
              }}
            ></div>
          </div>
          <div className="bar-value">{item.value}</div>
        </div>
      ))}
    </div>
  );
}