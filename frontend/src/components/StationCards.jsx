import React, { useEffect, useContext } from 'react';
import { AppContext } from '../AppContext';
import green from '../assets/green.png';
import red from '../assets/red.png';
import hydrogenPump from '../assets/hydrogen-pump.png';
import dieselPump from '../assets/diesel-pump.png';
import chargingStationIcon from '../assets/charging-station.png'; // You'll need to add this image asset
import FuelGauge from './FuelGauge';
import './StationCards.css';

const StationCards = ({ onClose }) => {
  const { 
    routeData, 
    journeyProcessed, 
    stationDataList, 
    setStationDataList,
    energyData,
    setEnergyData
  } = useContext(AppContext);
  
  // Set up click away listener to close cards
  useEffect(() => {
    const handleClickOutside = (event) => {
      // Check if click is outside of station cards and fuel card
      const stationCards = document.querySelector('.station-cards-container');
      const fuelCard = document.querySelector('.fuel-card-container');
      
      if (
        (stationCards && !stationCards.contains(event.target)) && 
        (fuelCard && !fuelCard.contains(event.target))
      ) {
        // If click is outside both cards, call the onClose function
        onClose();
      }
    };
    
    // Add the event listener
    document.addEventListener('mousedown', handleClickOutside);
    
    // Clean up
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);
  
  // Get the current fuel type from sessionStorage
  const getCurrentFuelType = () => {
    try {
      return sessionStorage.getItem('currentFuelType') || 'Diesel';
    } catch (e) {
      console.error("Error accessing sessionStorage:", e);
      return 'Diesel'; // Default to Diesel if error
    }
  };
  
  const fuelType = getCurrentFuelType();
  
  // Generate energy data if it doesn't exist yet
  useEffect(() => {
    if (journeyProcessed && !energyData) {
      // Generate new random energy data
      // Random diesel level (100-1500 L)
      const randomDiesel = Math.floor(Math.random() * (1500 - 100 + 1)) + 100;
      
      // Random hydrogen level (10-80 kg)
      const randomHydrogen = Math.floor(Math.random() * (80 - 10 + 1)) + 10;
      
      // Random battery charge level (10-95%)
      const randomBatteryCharge = Math.floor(Math.random() * (95 - 10 + 1)) + 10;
      
      // Create the energy data
      const newEnergyData = {
        dieselLevel: randomDiesel,
        hydrogenLevel: randomHydrogen,
        batteryCharge: randomBatteryCharge
      };
      
      // Store in context for persistence
      setEnergyData(newEnergyData);
    }
  }, [journeyProcessed, energyData, setEnergyData]);
  
  // Generate station data when route data changes
  useEffect(() => {
    // Check if we have a new journey with stations
    if (
      journeyProcessed && 
      routeData && 
      routeData.stations && 
      routeData.stations.length > 0
    ) {
      // Try to get station names from session storage
      let stationNames = [];
      try {
        const storedNames = sessionStorage.getItem('stationNames');
        if (storedNames) {
          stationNames = JSON.parse(storedNames);
        }
      } catch (e) {
        console.error("Error reading station names:", e);
      }
      
      // Generate data for each station
      const newStationDataList = routeData.stations.map((station, index) => {
        // Get station name or use default
        const stationName = stationNames[index] || `${fuelType} Station ${index + 1}`;
        
        if (fuelType === 'Diesel') {
          // Random available filling points (2-6)
          const availablePoints = Math.floor(Math.random() * (6 - 2 + 1)) + 2;
          // Random total fuel amount (10000-24000 L)
          const totalFuel = Math.floor(Math.random() * (24000 - 10000 + 1)) + 10000;
          
          return {
            name: stationName,
            availablePoints: availablePoints,
            totalPoints: 8,
            totalFuel: totalFuel
          };
        } else if (fuelType === 'Hydrogen') {
          // Random hydrogen station data
          const compressionOptions = [14, 40, 80];
          const randomCompression = compressionOptions[Math.floor(Math.random() * compressionOptions.length)];
          const randomCapacity = Math.floor(Math.random() * (1000 - 500 + 1)) + 500;
          
          // Random time for scheduled start
          const hours = Math.floor(Math.random() * 24);
          const minutes = Math.floor(Math.random() * 60);
          const scheduledStart = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
          
          // Estimated finish (2-4 hours later)
          const finishHours = hours + Math.floor(Math.random() * (4 - 2 + 1)) + 2;
          const adjustedFinishHours = finishHours >= 24 ? finishHours - 24 : finishHours;
          const estimatedFinish = `${adjustedFinishHours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
          
          return {
            name: stationName,
            compressionCapacity: randomCompression,
            capacity: randomCapacity,
            scheduledStart: scheduledStart,
            estimatedFinish: estimatedFinish
          };
        } else {
          // Electric charging station data
          const chargingPowerOptions = [50, 100, 150, 350];
          const randomChargingPower = chargingPowerOptions[Math.floor(Math.random() * chargingPowerOptions.length)];
          
          // Random available chargers (1-6 out of 8 total)
          const availableChargers = Math.floor(Math.random() * (6 - 1 + 1)) + 1;
          
          // Random charging time
          const estimatedChargingTime = `${Math.floor(Math.random() * (120 - 30 + 1)) + 30} mins`;
          
          // Random charging cost
          const chargingCost = (Math.random() * (35 - 15) + 15).toFixed(2);
          
          return {
            name: stationName,
            chargingPower: randomChargingPower,
            availableChargers: availableChargers,
            totalChargers: 8,
            estimatedChargingTime: estimatedChargingTime,
            chargingCost: chargingCost
          };
        }
      });
      
      // Save the generated data to context to persist it
      setStationDataList(newStationDataList);
    }
  }, [routeData, journeyProcessed, fuelType, setStationDataList]);
  
  // Return early if no data
  if (stationDataList.length === 0 || !energyData) {
    return null;
  }
  
  return (
    <>
      <div className="station-cards-container">
        {stationDataList.map((stationData, index) => (
          <div key={index} className="station-card">
            <div className="station-card-header">
              <img 
                src={fuelType === 'Hydrogen' ? hydrogenPump : fuelType === 'Electric' ? chargingStationIcon : dieselPump} 
                alt={fuelType} 
                className="station-card-icon" 
              />
              <h3 className="station-card-title">{stationData.name}</h3>
            </div>
            
            {fuelType === 'Diesel' ? (
              <div className="station-display">
                <div className="detail-item total-fuel">
                  <span className="detail-label">Total Fuel:</span>
                  <span className="detail-value">{stationData.totalFuel} Litres</span>
                </div>
                <div className="filling-points">
                  <div className="filling-points-row">
                    {[...Array(4)].map((_, i) => (
                      <img 
                        key={`row1-${i}`}
                        src={i < Math.min(stationData.availablePoints, 4) ? green : red} 
                        alt={i < stationData.availablePoints ? "Available" : "Occupied"} 
                        className="filling-point-icon"
                      />
                    ))}
                  </div>
                  <div className="filling-points-row">
                    {[...Array(4)].map((_, i) => (
                      <img 
                        key={`row2-${i}`}
                        src={i + 4 < stationData.availablePoints ? green : red} 
                        alt={i + 4 < stationData.availablePoints ? "Available" : "Occupied"} 
                        className="filling-point-icon"
                      />
                    ))}
                  </div>
                  <div className="filling-status">
                    <span className="available-count">{stationData.availablePoints} Free</span>
                    <span className="occupied-count">{stationData.totalPoints - stationData.availablePoints} Used</span>
                  </div>
                </div>
              </div>
            ) : fuelType === 'Hydrogen' ? (
              <div className="station-display">
                <div className="hydrogen-station-details">
                  <div className="detail-item">
                    <span className="detail-label">Compression Capacity:</span>
                    <span className="detail-value">{stationData.compressionCapacity} kg/hr</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Capacity:</span>
                    <span className="detail-value">{stationData.capacity} kg</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Scheduled Start:</span>
                    <span className="detail-value">{stationData.scheduledStart}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Estimated Finish:</span>
                    <span className="detail-value">{stationData.estimatedFinish}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="station-display">
                <div className="electric-station-details">
                  <div className="detail-item">
                    <span className="detail-label">Charging Power:</span>
                    <span className="detail-value">{stationData.chargingPower} kW</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Est. Charging Time:</span>
                    <span className="detail-value">{stationData.estimatedChargingTime}</span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">Est. Cost:</span>
                    <span className="detail-value">£{stationData.chargingCost}</span>
                  </div>
                  <div className="charging-status">
                    <div className="charging-points-visual" style={{ display: 'flex', justifyContent: 'center', margin: '10px 0' }}>
                      {[...Array(stationData.totalChargers)].map((_, i) => (
                        <span 
                          key={i} 
                          className={`charging-point ${i < stationData.availableChargers ? 'available' : 'occupied'}`}
                          title={i < stationData.availableChargers ? 'Available' : 'Occupied'}
                          style={{
                            display: 'inline-block',
                            width: '15px',
                            height: '15px',
                            borderRadius: '50%',
                            margin: '0 5px',
                            backgroundColor: i < stationData.availableChargers ? '#2ecc71' : '#e74c3c'
                          }}
                        />
                      ))}
                    </div>
                    <div className="filling-status">
                      <span className="available-count">{stationData.availableChargers} Free</span>
                      <span className="occupied-count">{stationData.totalChargers - stationData.availableChargers} Used</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Fuel Card at the bottom of the screen */}
      <div className="fuel-card-container">
        <div className="fuel-card">
          {/* Fuel Gauge */}
          <FuelGauge 
            value={fuelType === 'Electric' ? energyData.batteryCharge : fuelType === 'Hydrogen' ? energyData.hydrogenLevel : energyData.dieselLevel}
            maxValue={fuelType === 'Electric' ? 100 : fuelType === 'Hydrogen' ? 80 : 1500}
            type={fuelType}
          />
          
          {/* Value display with icon to the left */}
          <div className="fuel-value-container">
            <img 
              src={fuelType === 'Electric' ? chargingStationIcon : fuelType === 'Hydrogen' ? hydrogenPump : dieselPump} 
              alt={fuelType} 
              className="fuel-value-icon" 
            />
            <div className="fuel-value-text">
              {fuelType === 'Electric' 
                ? `${energyData.batteryCharge}% Charged` 
                : fuelType === 'Hydrogen'
                  ? `${energyData.hydrogenLevel} Kg`
                  : `${energyData.dieselLevel} Litres`}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default StationCards;