import React, { useEffect } from 'react';
import green from '../assets/green.png';
import red from '../assets/red.png';
import hydrogenPump from '../assets/hydrogen-pump.png';
import dieselPump from '../assets/diesel-pump.png';
import chargingStationIcon from '../assets/charging-station.png'; // Add this image asset
import './StationCards.css';

// Single station card component to display when a station marker is clicked
const StationCard = ({ stationData, onClose }) => {
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
  
  // Set up click away listener to close card
  useEffect(() => {
    const handleClickOutside = (event) => {
      // Check if click is outside of station card
      const stationCard = document.querySelector('.single-station-card');
      if (stationCard && !stationCard.contains(event.target)) {
        // If click is outside, call the onClose function
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
  
  if (!stationData) return null;
  
  // Get the appropriate icon based on fuel type
  const getStationIcon = () => {
    if (fuelType === 'Electric') {
      return chargingStationIcon;
    } else if (fuelType === 'Hydrogen') {
      return hydrogenPump;
    } else {
      return dieselPump;
    }
  };
  
  return (
    <div className="single-station-card-container">
      <div className="single-station-card station-card">
        <div className="station-card-header">
          <img 
            src={getStationIcon()} 
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
    </div>
  );
};

export default StationCard;