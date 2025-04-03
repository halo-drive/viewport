import React, { useState, useContext } from 'react';
import { AppContext } from '../AppContext';
import api from '../services/api';
import { AuthContext } from '../AuthContext';

export default function StartForm() {
  const { 
    journeyProcessed, 
    setJourneyProcessed, 
    setSelectedOrigin, 
    setSelectedDestination,
    setActivePane,
    setIsLoading,
    setRouteData,
    setAnalyticsData,
    setEnergyData, // Added this to reset energy data
    resetJourneyData // Use the new reset function
  } = useContext(AppContext);

  const { logout } = useContext(AuthContext);

  // Initialize form with defaults or saved values
  const [formData, setFormData] = useState(() => {
    // Try to get saved form data from sessionStorage
    try {
      const savedData = sessionStorage.getItem('lastFormData');
      if (savedData) {
        return JSON.parse(savedData);
      }
    } catch (e) {
      console.error("Error reading saved form data:", e);
    }
    
    // Fall back to defaults if no saved data
    return {
      fuelType: 'Diesel',
      pallets: 20,
      vehicleModel: 'VOLVO FH 520',
      originDepot: 'London',
      destinationDepot: 'Manchester',
      vehicleAge: 3,
      fuelAtOrigin: 20,
      fuelStation1: 30,
      fuelStation2: 80,
      dispatchTime: '12:00:00',
      journeyDate: getTomorrowDate()
    };
  });

  const [error, setError] = useState('');

  // Get upcoming dates for the journey date dropdown
  function getTomorrowDate() {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return formatDate(tomorrow);
  }

  function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function getUpcomingDates() {
    const dates = [];
    for (let i = 1; i <= 4; i++) {
      const date = new Date();
      date.setDate(date.getDate() + i);
      dates.push({
        value: formatDate(date),
        label: formatDate(date)
      });
    }
    return dates;
  }

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  // When fuel type changes, update vehicle model options
  const handleFuelTypeChange = (fuelType) => {
    let updatedFormData = {
      ...formData,
      fuelType: fuelType
    };
    
    // Reset vehicle model to appropriate default based on fuel type
    if (fuelType === 'Diesel') {
      updatedFormData.vehicleModel = 'VOLVO FH 520';
    } else {
      updatedFormData.vehicleModel = 'HVS HGV';
    }
    
    setFormData(updatedFormData);
  };

  const handleReset = () => {
    // Use the centralized reset function
    resetJourneyData();
    
    // Clear saved form data
    try {
      sessionStorage.removeItem('lastFormData');
    } catch (e) {
      console.error("Error clearing saved form data:", e);
    }
    
    // Reset the form data to defaults
    setFormData({
      fuelType: 'Diesel',
      pallets: 20,
      vehicleModel: 'VOLVO FH 520',
      originDepot: 'London',
      destinationDepot: 'Manchester',
      vehicleAge: 3,
      fuelAtOrigin: 20,
      fuelStation1: 30,
      fuelStation2: 80,
      dispatchTime: '12:00:00',
      journeyDate: getTomorrowDate()
    });
    
    setError('');
    
    // Force the map to clear by triggering a refresh on the map component
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 100);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Reset energy data for new journey
    setEnergyData(null);
    
    // Show loading state
    setIsLoading(true);
    
    // Close the form panel
    setActivePane(null);
    
    // Store the current form data in sessionStorage to persist it
    try {
      sessionStorage.setItem('lastFormData', JSON.stringify(formData));
      // Store the current fuel type in sessionStorage
      sessionStorage.setItem('currentFuelType', formData.fuelType);
    } catch (e) {
      console.error("Error storing form data:", e);
    }
    
    try {
      // Create FormData object to send to the backend
      const apiFormData = new FormData();
      
      // Add common fields
      apiFormData.append('pallets', formData.pallets);
      apiFormData.append('vehicleModel', formData.vehicleModel);
      apiFormData.append('originDepot', formData.originDepot);
      apiFormData.append('destinationDepot', formData.destinationDepot);
      apiFormData.append('vehicleAge', formData.vehicleAge);
      apiFormData.append('dispatchTime', formData.dispatchTime);
      apiFormData.append('journeyDate', formData.journeyDate);
      
      // Add fuel type specific fields
      if (formData.fuelType === 'Hydrogen') {
        apiFormData.append('fuelAtOrigin', formData.fuelAtOrigin);
        apiFormData.append('fuelStation1', formData.fuelStation1);
        apiFormData.append('fuelStation2', formData.fuelStation2);
      }
      
      // Call the appropriate API based on fuel type
      const result = await (formData.fuelType === 'Diesel' 
        ? api.calculateDieselRoute(apiFormData)
        : api.calculateHydrogenRoute(apiFormData));
      
      if (result.success) {
        // Store route and analytics data
        setRouteData(result.route);
        setAnalyticsData(result.analytics);
        
        // Set journey parameters for display
        setSelectedOrigin(formData.originDepot);
        setSelectedDestination(formData.destinationDepot);
        
        // Mark journey as processed
        setJourneyProcessed(true);
      } else {
        setError(result.error || 'An error occurred processing your request');
      }
    } catch (error) {
      console.error('Error submitting form:', error);
      setError('Failed to connect to the server. Please try again.');
    } finally {
      // Hide loading state
      setIsLoading(false);
    }
  };

  const depots = [
    'London', 'Liverpool', 'Manchester', 'Leeds', 
    'Birmingham', 'Glasgow', 'Cardiff', 'Aberdeen'
  ];

  return (
    <form className="start-form" onSubmit={handleSubmit}>
      {error && <div className="form-error">{error}</div>}
      
      <div className="form-group">
        <label>Fuel Type:</label>
        <div className="fuel-type-buttons">
          <button 
            type="button"
            className={`fuel-btn ${formData.fuelType === 'Diesel' ? 'active' : ''}`}
            onClick={() => handleFuelTypeChange('Diesel')}
          >
            Diesel
          </button>
          <button 
            type="button"
            className={`fuel-btn ${formData.fuelType === 'Hydrogen' ? 'active' : ''}`}
            onClick={() => handleFuelTypeChange('Hydrogen')}
          >
            Hydrogen
          </button>
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="pallets">Number of Pallets:</label>
        <input
          type="number"
          id="pallets"
          name="pallets"
          value={formData.pallets}
          onChange={handleChange}
        />
      </div>

      <div className="form-group">
        <label htmlFor="vehicleModel">Vehicle Model:</label>
        <select
          id="vehicleModel"
          name="vehicleModel"
          value={formData.vehicleModel}
          onChange={handleChange}
        >
          {formData.fuelType === 'Diesel' ? (
            <>
              <option value="VOLVO FH 520">VOLVO FH 520</option>
              <option value="VOLVO FL 420">VOLVO FL 420</option>
              <option value="DAF XF 105.510">DAF XF 105.510</option>
              <option value="DAF XG 530">DAF XG 530</option>
              <option value="SCANIA R 450">SCANIA R 450</option>
            </>
          ) : (
            <>
              <option value="HVS HGV">HVS HGV</option>
              <option value="HVS MCV">HVS MCV</option>
              <option value="Hymax Series">Hymax Series</option>
            </>
          )}
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="originDepot">Origin Depot:</label>
        <select
          id="originDepot"
          name="originDepot"
          value={formData.originDepot}
          onChange={handleChange}
        >
          {depots.map(depot => (
            <option key={depot} value={depot}>{depot}</option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="destinationDepot">Destination Depot:</label>
        <select
          id="destinationDepot"
          name="destinationDepot"
          value={formData.destinationDepot}
          onChange={handleChange}
        >
          {depots.map(depot => (
            <option key={depot} value={depot}>{depot}</option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="vehicleAge">Vehicle Age:</label>
        <input
          type="number"
          id="vehicleAge"
          name="vehicleAge"
          value={formData.vehicleAge}
          onChange={handleChange}
        />
      </div>

      <div className="form-group">
        <label htmlFor="fuelAtOrigin">Fuel at Origin:</label>
        <input
          type="number"
          id="fuelAtOrigin"
          name="fuelAtOrigin"
          value={formData.fuelAtOrigin}
          onChange={handleChange}
        />
      </div>

      {formData.fuelType === 'Hydrogen' && (
        <>
          <div className="form-group">
            <label htmlFor="fuelStation1">Fuel Range at Station 1:</label>
            <input
              type="number"
              id="fuelStation1"
              name="fuelStation1"
              value={formData.fuelStation1}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label htmlFor="fuelStation2">Fuel Range at Station 2:</label>
            <input
              type="number"
              id="fuelStation2"
              name="fuelStation2"
              value={formData.fuelStation2}
              onChange={handleChange}
            />
          </div>
        </>
      )}

      <div className="form-group">
        <label htmlFor="dispatchTime">Dispatch Time Window:</label>
        <input
          type="time"
          id="dispatchTime"
          name="dispatchTime"
          step="1"
          value={formData.dispatchTime}
          onChange={handleChange}
        />
      </div>

      <div className="form-group">
        <label htmlFor="journeyDate">Journey Date:</label>
        <select
          id="journeyDate"
          name="journeyDate"
          value={formData.journeyDate}
          onChange={handleChange}
        >
          {getUpcomingDates().map(date => (
            <option key={date.value} value={date.value}>{date.label}</option>
          ))}
        </select>
      </div>

      <div className="form-buttons">
        <button type="submit" className="submit-btn">Process</button>
        <button type="button" className="reset-btn" onClick={handleReset}>New Query</button>
        <button type="button" className="logout-btn" onClick={logout}>Logout</button>
      </div>
    </form>
  );
}