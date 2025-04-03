import React, { useEffect } from 'react';
import green from '../assets/green.png';
import red from '../assets/red.png';
import hydrogenPump from '../assets/hydrogen-pump.png';
import dieselPump from '../assets/diesel-pump.png';
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
  
  return (
    <div className="single-station-card-container">
      <div className="single-station-card station-card">
        <div className="station-card-header">
          <img 
            src={fuelType === 'Hydrogen' ? hydrogenPump : dieselPump} 
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
        ) : (
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
        )}
      </div>
    </div>
  );
};

export default StationCard;