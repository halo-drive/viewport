import React, { useState, useContext, useCallback, useRef, useEffect } from 'react';
import { AppContext } from '../AppContext';
import { AuthContext } from '../AuthContext';
import api from '../services/api'; // Assuming you have this service setup
import './StartForm.css'; // Your CSS file

// --- Helper Functions --- moved here ---
// Ensure these are defined BEFORE StartForm component uses them internally
function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function getTomorrowDate() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return formatDate(tomorrow);
}
// --- End Helper Functions ---

export default function StartForm() {
  const {
    setJourneyProcessed,
    setSelectedOrigin,
    setSelectedDestination,
    setActivePane,
    setIsLoading,
    setRouteData,
    setAnalyticsData,
    setEnergyData,
    setStationDataList,
    resetJourneyData,
    setIsTracking,
    setGpsOriginCoords,
    journeyProcessed,
    isLoading // Destructure isLoading for use in handleSubmit
  } = useContext(AppContext);

  const { logout } = useContext(AuthContext);

  const [isFetchingLocationOnSubmit, setIsFetchingLocationOnSubmit] = useState(false);
  const [showProcessedWarning, setShowProcessedWarning] = useState(false);
  const warningBoxRef = useRef(null);
  const processButtonRef = useRef(null);

  // Initialize form state
  const [formData, setFormData] = useState(() => {
     // Default form state - include your sessionStorage logic if needed
      return {
        fuelType: 'Diesel', pallets: 20, vehicleModel: 'VOLVO FH 520',
        originDepot: 'London', destinationDepot: 'Manchester', vehicleAge: 3,
        fuelAtOrigin: 20, fuelStation1: 30, fuelStation2: 80,
        dispatchTime: '12:00:00', journeyDate: getTomorrowDate()
      };
  });

  const [error, setError] = useState('');

  // Date Helper needed within the component scope
  function getUpcomingDates() {
    const dates = [];
    for (let i = 1; i <= 4; i++) {
      const date = new Date();
      date.setDate(date.getDate() + i);
      dates.push({
        value: formatDate(date), // Now formatDate is accessible
        label: formatDate(date)
      });
    }
    return dates;
  }

  // Handle form input changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    if (name === 'originDepot' && value !== 'GPS') setError('');
  };

  // Handle fuel type button clicks
  const handleFuelTypeChange = (fuelType) => {
    let updatedFormData = { ...formData, fuelType: fuelType };
    if (fuelType === 'Diesel') updatedFormData.vehicleModel = 'VOLVO FH 520';
    else if (fuelType === 'Hydrogen') updatedFormData.vehicleModel = 'HVS HGV';
    else if (fuelType === 'Electric') updatedFormData.vehicleModel = 'Volvo FE Electric';
    if (formData.originDepot === 'GPS') updatedFormData.originDepot = 'London';
    setFormData(updatedFormData);
    setError('');
  };

  // Handle "New Query" button click
  const handleReset = () => {
    resetJourneyData();
    setIsFetchingLocationOnSubmit(false);
    setShowProcessedWarning(false);
    setError('');
    setFormData({ // Reset local form state
      fuelType: 'Diesel', pallets: 20, vehicleModel: 'VOLVO FH 520',
      originDepot: 'London', destinationDepot: 'Manchester', vehicleAge: 3,
      fuelAtOrigin: 20, fuelStation1: 30, fuelStation2: 80,
      dispatchTime: '12:00:00', journeyDate: getTomorrowDate()
    });
  };

  // Get current GPS location
  const getCurrentLocation = useCallback(() => {
    return new Promise((resolve, reject) => {
      if (!('geolocation' in navigator)) {
        return reject(new Error('Geolocation is not supported. Please select a depot.'));
      }
      navigator.geolocation.getCurrentPosition(
        (position) => resolve({ lat: position.coords.latitude, lon: position.coords.longitude }),
        (err) => reject(new Error(`Error getting location: ${err.message}. Select depot or try again.`)),
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
      );
    });
  }, []); // Keep useCallback dependency array empty if it has no external dependencies

  // Handle form submission ("Process" button)
  const handleSubmit = async (e) => {
    e.preventDefault(); // Prevent default form submission
    console.log("Process button clicked"); // Add log to confirm handler runs
    setError('');
    setShowProcessedWarning(false);

    if (journeyProcessed) {
      console.log("Journey already processed, showing warning.");
      setShowProcessedWarning(true);
      return; // Stop if journey already processed
    }

    let currentOriginCoords = null;
    // --- GPS Handling ---
    if (formData.originDepot === 'GPS') {
      console.log("Origin is GPS, attempting to fetch location...");
      setIsFetchingLocationOnSubmit(true);
      setIsLoading(true); // Show global loading indicator
      try {
        currentOriginCoords = await getCurrentLocation();
        console.log("GPS Location fetched:", currentOriginCoords);
        setError(''); // Clear previous errors
      } catch (locationError) {
        console.error("GPS Error:", locationError);
        setError(locationError.message);
        setIsFetchingLocationOnSubmit(false);
        setIsLoading(false); // Hide loading indicator
        return; // Stop submission on GPS error
      }
      // Don't set loading/fetching false here if successful, API call follows
    }
    // --- End GPS Handling ---


    // Ensure loading is true for the API call phase
    // Corrected logic: Don't set true if already true from GPS fetch
    if (!isLoading && !isFetchingLocationOnSubmit) { // Only set if not already loading
         setIsLoading(true);
    }
    setActivePane(null); // Close form panel

    // --- Save Form Data (Optional) ---
    // (Keep your existing logic if needed)
    const dataToSave = { ...formData };
    if (formData.originDepot === 'GPS') dataToSave.originDepot = 'GPS_USED';
     try {
       sessionStorage.setItem('lastFormData', JSON.stringify(dataToSave));
       sessionStorage.setItem('currentFuelType', formData.fuelType);
     } catch (err) { console.error("Error storing form data:", err); }
    // --- End Save Form Data ---


    // --- API Call ---
    try {
      console.log("Preparing form data for API...");
      const apiFormData = new FormData();
      // Append fields (same as before)
      apiFormData.append('pallets', formData.pallets);
      apiFormData.append('vehicleModel', formData.vehicleModel);
      apiFormData.append('destinationDepot', formData.destinationDepot);
      apiFormData.append('vehicleAge', formData.vehicleAge);
      apiFormData.append('dispatchTime', formData.dispatchTime);
      apiFormData.append('journeyDate', formData.journeyDate);

      let originValueForDisplay = '';
      if (formData.originDepot === 'GPS' && currentOriginCoords) {
        apiFormData.append('originLat', currentOriginCoords.lat);
        apiFormData.append('originLon', currentOriginCoords.lon);
        originValueForDisplay = 'GPS';
        setGpsOriginCoords(currentOriginCoords);
      } else {
        apiFormData.append('originDepot', formData.originDepot);
        originValueForDisplay = formData.originDepot;
        setGpsOriginCoords(null);
      }

      if (formData.fuelType === 'Hydrogen' || formData.fuelType === 'Electric') {
        apiFormData.append('fuelAtOrigin', formData.fuelAtOrigin);
        apiFormData.append('fuelStation1', formData.fuelStation1);
        apiFormData.append('fuelStation2', formData.fuelStation2);
      }

      // Reset previous results
      setRouteData(null);
      setStationDataList([]);
      setEnergyData(null);
      setAnalyticsData(null);

      console.log("Calling API for:", formData.fuelType);
      let result;
      if (formData.fuelType === 'Diesel') result = await api.calculateDieselRoute(apiFormData);
      else if (formData.fuelType === 'Hydrogen') result = await api.calculateHydrogenRoute(apiFormData);
      else if (formData.fuelType === 'Electric') result = await api.calculateElectricRoute(apiFormData);

      console.log("API Result:", result);
      // Process result
      if (result && result.success) {
        setRouteData(result.route);
        setAnalyticsData(result.analytics);
        // setStationDataList(result.stations || []); // Uncomment if needed
        // setEnergyData(result.energy || null); // Uncomment if needed
        setSelectedOrigin(originValueForDisplay);
        setSelectedDestination(formData.destinationDepot);
        setJourneyProcessed(true);
        setIsTracking(originValueForDisplay === 'GPS');
        setError('');
        console.log("Journey processed successfully.");
      } else {
        setError(result?.error || 'An error occurred processing your request');
        setJourneyProcessed(false);
        setIsTracking(false);
        setGpsOriginCoords(null);
        console.error("API Error/Failure:", result?.error);
      }
    } catch (error) {
      console.error('Error submitting form (catch block):', error);
      setError('Failed to connect to the server. Please try again.');
      setJourneyProcessed(false);
      setIsTracking(false);
      setGpsOriginCoords(null);
    } finally {
      console.log("Submit handling finished, setting loading states false.");
      setIsLoading(false); // Stop global loading indicator
      setIsFetchingLocationOnSubmit(false); // Stop GPS fetching indicator
    }
    // --- End API Call ---
  };


  // Effect for handling clicks outside the warning box
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target) return;
      if ( showProcessedWarning && warningBoxRef.current && !warningBoxRef.current.contains(event.target) && processButtonRef.current && !processButtonRef.current.contains(event.target) ) {
        setShowProcessedWarning(false);
      }
    };
    if (showProcessedWarning) document.addEventListener('mousedown', handleClickOutside);
    else document.removeEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showProcessedWarning]); // Dependency only on showProcessedWarning


  // Combined handler for Logout button
  const handleLogoutAndReset = () => {
    console.log("StartForm logout button clicked: Resetting journey and logging out...");
    resetJourneyData(); // Reset the journey state first
    logout();         // Then perform the logout
  };


  // Depot list
  const depots = [
    'London', 'Liverpool', 'Manchester', 'Leeds',
    'Birmingham', 'Glasgow', 'Cardiff', 'Aberdeen'
  ];


  // --- JSX Rendering ---
  return (
    // Ensure the form has position: relative for the absolute positioned warning box
    <form className="start-form" onSubmit={handleSubmit} style={{ position: 'relative' }}>
      {/* Error and Info Messages */}
      {error && <div className="form-error">{error}</div>}
      {isFetchingLocationOnSubmit && <div className="form-info">Getting current location...</div>}

      {/* --- Form Groups --- */}

      {/* Fuel Type Buttons */}
      <div className="form-group">
        <label>Fuel Type:</label>
        <div className="fuel-type-buttons">
          {['Diesel', 'Hydrogen', 'Electric'].map(type => (
            <button
              key={type}
              type="button"
              className={`fuel-btn ${formData.fuelType === type ? 'active' : ''}`}
              onClick={() => handleFuelTypeChange(type)}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Pallets Input */}
      <div className="form-group">
        <label htmlFor="pallets">Number of Pallets:</label>
        <input type="number" id="pallets" name="pallets" value={formData.pallets} onChange={handleChange} min="0"/>
      </div>

      {/* Vehicle Model Select */}
      <div className="form-group">
        <label htmlFor="vehicleModel">Vehicle Model:</label>
        <select id="vehicleModel" name="vehicleModel" value={formData.vehicleModel} onChange={handleChange}>
           {formData.fuelType === 'Diesel' ? ( <> <option value="VOLVO FH 520">VOLVO FH 520</option> <option value="VOLVO FL 420">VOLVO FL 420</option> <option value="DAF XF 105.510">DAF XF 105.510</option> <option value="DAF XG 530">DAF XG 530</option> <option value="SCANIA R 450">SCANIA R 450</option> </> )
           : formData.fuelType === 'Hydrogen' ? ( <> <option value="HVS HGV">HVS HGV</option> <option value="HVS MCV">HVS MCV</option> <option value="Hymax Series">Hymax Series</option> </> )
           : ( <> <option value="Volvo FE Electric">Volvo FE Electric</option> <option value="DAF CF Electric">DAF CF Electric</option> <option value="Mercedes eActros">Mercedes eActros</option> <option value="MAN eTGM">MAN eTGM</option> <option value="Renault E-Tech D">Renault E-Tech D</option> <option value="Scania BEV">Scania BEV</option> <option value="Volvo FL Electric">Volvo FL Electric</option> <option value="FUSO eCanter">FUSO eCanter</option> <option value="Freightliner eCascadia">Freightliner eCascadia</option> <option value="BYD ETM6">BYD ETM6</option> </> )}
        </select>
      </div>

      {/* Origin Depot Select */}
      <div className="form-group">
        <label htmlFor="originDepot">Origin Depot:</label>
        <select id="originDepot" name="originDepot" value={formData.originDepot} onChange={handleChange}>
          <option value="GPS">My Current Location</option>
          {depots.map(depot => (<option key={depot} value={depot}>{depot}</option>))}
        </select>
      </div>

      {/* Destination Depot Select */}
      <div className="form-group">
        <label htmlFor="destinationDepot">Destination Depot:</label>
        <select id="destinationDepot" name="destinationDepot" value={formData.destinationDepot} onChange={handleChange}>
           {depots.map(depot => (<option key={depot} value={depot}>{depot}</option>))}
        </select>
      </div>

      {/* Vehicle Age Input */}
      <div className="form-group">
        <label htmlFor="vehicleAge">Vehicle Age:</label>
        <input type="number" id="vehicleAge" name="vehicleAge" value={formData.vehicleAge} onChange={handleChange} min="0" />
      </div>

      {/* Fuel At Origin Input */}
      <div className="form-group">
        <label htmlFor="fuelAtOrigin">Fuel at Origin (%):</label>
        <input type="number" id="fuelAtOrigin" name="fuelAtOrigin" value={formData.fuelAtOrigin} onChange={handleChange} min="0" max="100"/>
      </div>

      {/* Fuel Station Inputs (Conditional) */}
      {(formData.fuelType === 'Hydrogen' || formData.fuelType === 'Electric') && (
        <>
          <div className="form-group">
            <label htmlFor="fuelStation1">Min Fuel Range at Station 1 (%):</label>
            <input type="number" id="fuelStation1" name="fuelStation1" value={formData.fuelStation1} onChange={handleChange} min="0" max="100"/>
          </div>
          <div className="form-group">
            <label htmlFor="fuelStation2">Min Fuel Range at Station 2 (%):</label>
            <input type="number" id="fuelStation2" name="fuelStation2" value={formData.fuelStation2} onChange={handleChange} min="0" max="100"/>
          </div>
        </>
      )}

      {/* Dispatch Time Input */}
      <div className="form-group">
        <label htmlFor="dispatchTime">Dispatch Time Window:</label>
        <input type="time" id="dispatchTime" name="dispatchTime" step="1" value={formData.dispatchTime} onChange={handleChange} />
      </div>

      {/* Journey Date Select */}
      <div className="form-group">
        <label htmlFor="journeyDate">Journey Date:</label>
        <select id="journeyDate" name="journeyDate" value={formData.journeyDate} onChange={handleChange}>
           {getUpcomingDates().map(date => (<option key={date.value} value={date.value}>{date.label}</option> ))}
        </select>
      </div>

      {/* --- Form Buttons --- */}
      <div className="form-buttons">
        {/* Process button uses the form's onSubmit */}
        <button
          ref={processButtonRef}
          type="submit" // This triggers the form's onSubmit={handleSubmit}
          className="submit-btn"
          disabled={isFetchingLocationOnSubmit} // Only disable while fetching GPS
        >
          Process
        </button>
        {/* "New Query" button uses handleReset */}
        <button type="button" className="reset-btn" onClick={handleReset}>New Query</button>
        {/* "Logout" button uses the combined handler */}
        <button type="button" className="logout-btn" onClick={handleLogoutAndReset}>Logout</button>
      </div>

      {/* Conditional Warning Box for already processed journey */}
      {showProcessedWarning && (
        <div ref={warningBoxRef} className="processed-warning-box">
          <div className="warning-box-pointer"></div>
          <p>A journey result is already displayed.</p>
          <p>Please click 'New Query'</p>
          {/* Optional close button
          <button onClick={() => setShowProcessedWarning(false)} className="close-warning-btn" aria-label="Close warning">&times;</button>
          */}
        </div>
      )}
    </form>
  );
}