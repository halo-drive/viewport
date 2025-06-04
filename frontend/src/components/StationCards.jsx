import React, { useEffect, useContext } from 'react';
import { AppContext } from '../AppContext';
import green from '../assets/green.png';
import red from '../assets/red.png';
import hydrogenPump from '../assets/hydrogen-pump.png';
import dieselPump from '../assets/diesel-pump.png';
import chargingStationIcon from '../assets/charging-station.png'; 
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
  
  useEffect(() => {
    const handleClickOutside = (event) => {
      const stationCards = document.querySelector('.station-cards-container');
      const fuelCard = document.querySelector('.fuel-card-container');
      
      if (
        (stationCards && !stationCards.contains(event.target)) && 
        (fuelCard && !fuelCard.contains(event.target))
      ) {
        onClose();
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);
  
  const getCurrentFuelType = () => {
    try {
      return sessionStorage.getItem('currentFuelType') || 'Diesel';
    } catch (e) {
      console.error("Error accessing sessionStorage:", e);
      return 'Diesel'; 
    }
  };
  
  const fuelType = getCurrentFuelType();
  
  useEffect(() => {
    if (journeyProcessed && !energyData) {
      const randomDiesel = Math.floor(Math.random() * (1500 - 100 + 1)) + 100;
      
      const randomHydrogen = Math.floor(Math.random() * (80 - 10 + 1)) + 10;
      
      const randomBatteryCharge = Math.floor(Math.random() * (95 - 10 + 1)) + 10;
      
      const newEnergyData = {
        dieselLevel: randomDiesel,
        hydrogenLevel: randomHydrogen,
        batteryCharge: randomBatteryCharge
      };
      
      setEnergyData(newEnergyData);
    }
  }, [journeyProcessed, energyData, setEnergyData]);
  
  useEffect(() => {
    if (
      journeyProcessed && 
      routeData && 
      routeData.stations && 
      routeData.stations.length > 0
    ) {
      let stationNames = [];
      try {
        const storedNames = sessionStorage.getItem('stationNames');
        if (storedNames) {
          stationNames = JSON.parse(storedNames);
        }
      } catch (e) {
        console.error("Error reading station names:", e);
      }
      
      const newStationDataList = routeData.stations.map((station, index) => {
        const stationName = stationNames[index] || `${fuelType} Station ${index + 1}`;
        
        if (fuelType === 'Diesel') {
          const availablePoints = Math.floor(Math.random() * (6 - 2 + 1)) + 2;
          const totalFuel = Math.floor(Math.random() * (24000 - 10000 + 1)) + 10000;
          
          return {
            name: stationName,
            availablePoints: availablePoints,
            totalPoints: 8,
            totalFuel: totalFuel
          };
        } else if (fuelType === 'Hydrogen') {
          const compressionOptions = [14, 40, 80];
          const randomCompression = compressionOptions[Math.floor(Math.random() * compressionOptions.length)];
          const randomCapacity = Math.floor(Math.random() * (1000 - 500 + 1)) + 500;
          
          const hours = Math.floor(Math.random() * 24);
          const minutes = Math.floor(Math.random() * 60);
          const scheduledStart = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
          
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
          const chargingPowerOptions = [50, 100, 150, 350];
          const randomChargingPower = chargingPowerOptions[Math.floor(Math.random() * chargingPowerOptions.length)];
          
          const availableChargers = Math.floor(Math.random() * (6 - 1 + 1)) + 1;
          
          const estimatedChargingTime = `${Math.floor(Math.random() * (120 - 30 + 1)) + 30} mins`;
          
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
      
      setStationDataList(newStationDataList);
    }
  }, [routeData, journeyProcessed, fuelType, setStationDataList]);
  
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

      <div className="fuel-card-container">
        <div className="fuel-card">
          <FuelGauge 
            value={fuelType === 'Electric' ? energyData.batteryCharge : fuelType === 'Hydrogen' ? energyData.hydrogenLevel : energyData.dieselLevel}
            maxValue={fuelType === 'Electric' ? 100 : fuelType === 'Hydrogen' ? 80 : 1500}
            type={fuelType}
          />
          
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