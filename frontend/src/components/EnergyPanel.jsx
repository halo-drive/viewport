import React, { useState, useEffect, useContext } from 'react';
import { AppContext } from '../AppContext';
import dieselPump from '../assets/diesel-pump.png';
import hydrogenPump from '../assets/hydrogen-pump.png';
import chargingStationIcon from '../assets/charging-station.png'; // You'll need to add this image asset
import green from '../assets/green.png';
import red from '../assets/red.png';

export default function EnergyPanel() {
  // Get AppContext for storing persistent data
  const { routeData, journeyProcessed, energyData, setEnergyData } = useContext(AppContext);
  
  // Get fuel type from session storage
  const getCurrentFuelType = () => {
    try {
      return sessionStorage.getItem('currentFuelType') || 'Diesel';
    } catch (e) {
      console.error("Error accessing sessionStorage:", e);
      return 'Diesel'; // Default to Diesel if error
    }
  };
  
  const journeyFuelType = getCurrentFuelType();
  
  // Generate or retrieve energy data
  useEffect(() => {
    // Check if we already have energy data
    if (!energyData || !Object.keys(energyData).length) {
      // Try to get station names from session storage
      let stationNames = [];
      try {
        const storedNames = sessionStorage.getItem('stationNames');
        if (storedNames) {
          stationNames = JSON.parse(storedNames);
          console.log("Retrieved station names:", stationNames);
        }
      } catch (e) {
        console.error("Error reading station names:", e);
      }
      
      // Default station names if none found
      const dieselStationName = stationNames.length > 0 ? stationNames[0] : 'Central Depot Station';
      const hydrogenStationName = stationNames.length > 0 ? stationNames[0] : 'Hydrogen Hub Station';
      const electricStationName = stationNames.length > 0 ? stationNames[0] : 'EV Charging Hub';
      
      // No data exists yet - generate new random data
      // Random diesel level (100-1500 L)
      const randomDiesel = Math.floor(Math.random() * (1500 - 100 + 1)) + 100;
      
      // Random hydrogen level (10-80 kg)
      const randomHydrogen = Math.floor(Math.random() * (80 - 10 + 1)) + 10;
      
      // Random electric battery charge (10-95%)
      const randomBatteryCharge = Math.floor(Math.random() * (95 - 10 + 1)) + 10;
      
      // Random available filling points (2-6)
      const availablePoints = Math.floor(Math.random() * (6 - 2 + 1)) + 2;
      
      // Random hydrogen station data
      const compressionOptions = [14, 40, 80];
      const randomCompression = compressionOptions[Math.floor(Math.random() * compressionOptions.length)];
      const randomCapacity = Math.floor(Math.random() * (1000 - 500 + 1)) + 500;
      
      // Random electric charging station data
      const chargingPowerOptions = [150, 250, 350, 500];
      const randomChargingPower = chargingPowerOptions[Math.floor(Math.random() * chargingPowerOptions.length)];
      const randomAvailableChargers = Math.floor(Math.random() * (8 - 1 + 1)) + 1;
      
      // Random time for scheduled start
      const hours = Math.floor(Math.random() * 24);
      const minutes = Math.floor(Math.random() * 60);
      const scheduledStart = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
      
      // Estimated finish (2-4 hours later)
      const finishHours = hours + Math.floor(Math.random() * (4 - 2 + 1)) + 2;
      const adjustedFinishHours = finishHours >= 24 ? finishHours - 24 : finishHours;
      const estimatedFinish = `${adjustedFinishHours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
      
      // Create and store the energy data
      const newEnergyData = {
        dieselLevel: randomDiesel,
        hydrogenLevel: randomHydrogen,
        batteryCharge: randomBatteryCharge,
        dieselStation: {
          name: dieselStationName,
          availablePoints: availablePoints,
          totalPoints: 8
        },
        hydrogenStation: {
          name: hydrogenStationName,
          compressionCapacity: randomCompression,
          capacity: randomCapacity,
          scheduledStart: scheduledStart,
          estimatedFinish: estimatedFinish
        },
        electricStation: {
          name: electricStationName,
          chargingPower: randomChargingPower,
          availableChargers: randomAvailableChargers,
          totalChargers: 8,
          estimatedTime: `${Math.floor(Math.random() * (180 - 60 + 1)) + 60} mins`
        }
      };
      
      // Store in context for persistence
      setEnergyData(newEnergyData);
    }
  }, [energyData, setEnergyData]);

  // Helper function to get color for fuel level bar
  const getFuelBarColor = (level, max) => {
    const percentage = level / max;
    
    if (percentage < 0.3) return '#e74c3c'; // Red for low
    if (percentage < 0.6) return '#f39c12'; // Orange for medium
    return '#2ecc71'; // Green for high
  };
  
  // If we don't have energy data yet, show loading
  if (!energyData) {
    return <div>Loading energy data...</div>;
  }

  return (
    <div className="energy-panel">
      {/* Fuel Section */}
      <div className="energy-section">
        <h3 className="section-title">Fuel</h3>
        
        {journeyFuelType === 'Diesel' ? (
          <div className="fuel-display">
            <div className="fuel-icon-container">
              <img src={dieselPump} alt="Diesel" className="fuel-icon" />
            </div>
            <div className="fuel-bar-container">
              <div 
                className="fuel-bar-fill" 
                style={{ 
                  width: `${(energyData.dieselLevel / 1500) * 100}%`,
                  backgroundColor: getFuelBarColor(energyData.dieselLevel, 1500)
                }}
              ></div>
            </div>
            <div className="fuel-value">{energyData.dieselLevel} Litres</div>
          </div>
        ) : journeyFuelType === 'Hydrogen' ? (
          <div className="fuel-display">
            <div className="fuel-icon-container">
              <img src={hydrogenPump} alt="Hydrogen" className="fuel-icon" />
            </div>
            <div className="fuel-bar-container">
              <div 
                className="fuel-bar-fill" 
                style={{ 
                  width: `${(energyData.hydrogenLevel / 80) * 100}%`,
                  backgroundColor: getFuelBarColor(energyData.hydrogenLevel, 80)
                }}
              ></div>
            </div>
            <div className="fuel-value">{energyData.hydrogenLevel} Kg</div>
          </div>
        ) : (
          <div className="fuel-display">
            <div className="fuel-icon-container">
              <img src={chargingStationIcon} alt="Battery" className="fuel-icon" />
            </div>
            <div className="fuel-bar-container">
              <div 
                className="fuel-bar-fill" 
                style={{ 
                  width: `${energyData.batteryCharge}%`,
                  backgroundColor: getFuelBarColor(energyData.batteryCharge, 100)
                }}
              ></div>
            </div>
            <div className="fuel-value">{energyData.batteryCharge}% Charged</div>
          </div>
        )}
      </div>
      
      {/* Stations Section */}
      <div className="energy-section">
        <h3 className="section-title">Station</h3>
        
        {journeyFuelType === 'Diesel' ? (
          <div className="station-display">
            <h4 className="station-name">{energyData.dieselStation.name}</h4>
            <div className="filling-points">
              <div className="filling-points-row">
                {[...Array(4)].map((_, index) => (
                  <img 
                    key={`row1-${index}`}
                    src={index < Math.min(energyData.dieselStation.availablePoints, 4) ? green : red} 
                    alt={index < energyData.dieselStation.availablePoints ? "Available" : "Occupied"} 
                    className="filling-point-icon"
                  />
                ))}
              </div>
              <div className="filling-points-row">
                {[...Array(4)].map((_, index) => (
                  <img 
                    key={`row2-${index}`}
                    src={index + 4 < energyData.dieselStation.availablePoints ? green : red} 
                    alt={index + 4 < energyData.dieselStation.availablePoints ? "Available" : "Occupied"} 
                    className="filling-point-icon"
                  />
                ))}
              </div>
              <div className="filling-status">
                <span className="available-count">{energyData.dieselStation.availablePoints} Available</span>
                <span className="occupied-count">{energyData.dieselStation.totalPoints - energyData.dieselStation.availablePoints} Occupied</span>
              </div>
            </div>
          </div>
        ) : journeyFuelType === 'Hydrogen' ? (
          <div className="station-display">
            <h4 className="station-name">{energyData.hydrogenStation.name}</h4>
            <div className="hydrogen-station-details">
              <div className="detail-item">
                <span className="detail-label">Compression Capacity:</span>
                <span className="detail-value">{energyData.hydrogenStation.compressionCapacity} kg/hr</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Capacity:</span>
                <span className="detail-value">{energyData.hydrogenStation.capacity} kg</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Scheduled Start:</span>
                <span className="detail-value">{energyData.hydrogenStation.scheduledStart}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Estimated Finish:</span>
                <span className="detail-value">{energyData.hydrogenStation.estimatedFinish}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="station-display">
            <h4 className="station-name">{energyData.electricStation.name}</h4>
            <div className="electric-station-details">
              <div className="detail-item">
                <span className="detail-label">Charging Power:</span>
                <span className="detail-value">{energyData.electricStation.chargingPower} kW</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Available Chargers:</span>
                <span className="detail-value">{energyData.electricStation.availableChargers} / {energyData.electricStation.totalChargers}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Est. Charging Time:</span>
                <span className="detail-value">{energyData.electricStation.estimatedTime}</span>
              </div>
              <div className="charging-status">
                <div className="charging-points-row">
                  {[...Array(energyData.electricStation.totalChargers)].map((_, index) => (
                    <span 
                      key={index}
                      className={`charging-point ${index < energyData.electricStation.availableChargers ? 'available' : 'occupied'}`}
                      style={{
                        display: 'inline-block',
                        width: '15px',
                        height: '15px',
                        borderRadius: '50%',
                        margin: '0 5px',
                        backgroundColor: index < energyData.electricStation.availableChargers ? '#2ecc71' : '#e74c3c'
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}