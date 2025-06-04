import React, { useState, useContext, useCallback, useRef, useEffect } from 'react';
import { AppContext } from '../AppContext';
import { AuthContext } from '../AuthContext';
import api from '../services/api';
import './StartForm.css';
import { toast} from 'react-toastify';

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
    isLoading
  } = useContext(AppContext);

  const { logout } = useContext(AuthContext);

  const [isFetchingLocationOnSubmit, setIsFetchingLocationOnSubmit] = useState(false);
  const [showProcessedWarning, setShowProcessedWarning] = useState(false);
  const warningBoxRef = useRef(null);
  const processButtonRef = useRef(null);

  const [formData, setFormData] = useState(() => {
      return {
        fuelType: 'Diesel', pallets: 20, vehicleModel: 'VOLVO FH 520',
        originDepot: 'London', destinationDepot: 'Manchester', vehicleAge: 3,
        fuelAtOrigin: 20, fuelStation1: 30, fuelStation2: 80,
        dispatchTime: '12:00:00', journeyDate: getTomorrowDate()
      };
  });

  const [error, setError] = useState('');

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
    setFormData({ ...formData, [name]: value });
    if (name === 'originDepot' && value !== 'GPS') setError('');
  };

  const handleFuelTypeChange = (fuelType) => {
    let updatedFormData = { ...formData, fuelType: fuelType };
    if (fuelType === 'Diesel') updatedFormData.vehicleModel = 'VOLVO FH 520';
    else if (fuelType === 'Hydrogen') updatedFormData.vehicleModel = 'HVS HGV';
    else if (fuelType === 'Electric') updatedFormData.vehicleModel = 'Volvo FE Electric';
    if (formData.originDepot === 'GPS') updatedFormData.originDepot = 'London';
    setFormData(updatedFormData);
    setError('');
  };

  const handleReset = () => {
    resetJourneyData();
    setIsFetchingLocationOnSubmit(false);
    setShowProcessedWarning(false);
    setError('');
    setFormData({
      fuelType: 'Diesel', pallets: 20, vehicleModel: 'VOLVO FH 520',
      originDepot: 'London', destinationDepot: 'Manchester', vehicleAge: 3,
      fuelAtOrigin: 20, fuelStation1: 30, fuelStation2: 80,
      dispatchTime: '12:00:00', journeyDate: getTomorrowDate()
    });
  };

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
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    console.log("Process button clicked");
    setError('');
    setShowProcessedWarning(false);

    if (journeyProcessed) {
      console.log("Journey already processed, showing warning.");
      setShowProcessedWarning(true);
      return;
    }

    let currentOriginCoords = null;
    if (formData.originDepot === 'GPS') {
      console.log("Origin is GPS, attempting to fetch location...");
      setIsFetchingLocationOnSubmit(true);
      setIsLoading(true);
      try {
        currentOriginCoords = await getCurrentLocation();
        console.log("GPS Location fetched:", currentOriginCoords);
        setError('');
      } catch (locationError) {
        console.error("GPS Error:", locationError);
        setError(locationError.message);
        setIsFetchingLocationOnSubmit(false);
        setIsLoading(false);
        return;
      }
    }


    if (!isLoading && !isFetchingLocationOnSubmit) {
         setIsLoading(true);
    }
    setActivePane(null);

    const dataToSave = { ...formData };
    if (formData.originDepot === 'GPS') dataToSave.originDepot = 'GPS_USED';
     try {
       sessionStorage.setItem('lastFormData', JSON.stringify(dataToSave));
       sessionStorage.setItem('currentFuelType', formData.fuelType);
     } catch (err) { console.error("Error storing form data:", err); }


    try {
      console.log("Preparing form data for API...");
      const apiFormData = new FormData();
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
      if (result && result.success) {
        setRouteData(result.route);
        setAnalyticsData(result.analytics);
        setSelectedOrigin(originValueForDisplay);
        setSelectedDestination(formData.destinationDepot);
        setJourneyProcessed(true);
        setIsTracking(originValueForDisplay === 'GPS');
        setError('');
        console.log("Journey processed successfully.");
      } else {
        setError(result?.error || result?.message || 'An error occurred processing your request');
        setJourneyProcessed(false);
        setIsTracking(false);
        setGpsOriginCoords(null);
        console.error("API Error/Failure:", result?.error || result?.message);
      }
    } catch (error) {
      console.error('Error submitting form (catch block):', error);
      if (error && error.status === 429 && error.data && error.data.error_type === "RATE_LIMIT_EXCEEDED") {
        toast.warn("Too many API requests. Wait a bit and try again.");
      } else if (error && error.message) {
        setError(error.message);
      } else {
        setError('Failed to connect to the server or an unknown error occurred. Please try again.');
      }
      setJourneyProcessed(false);
      setIsTracking(false);
      setGpsOriginCoords(null);
    } finally {
      console.log("Submit handling finished, setting loading states false.");
      setIsLoading(false);
      setIsFetchingLocationOnSubmit(false);
    }
  };


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
  }, [showProcessedWarning]);

  const handleLogoutAndReset = () => {
    console.log("StartForm logout button clicked: Resetting journey and logging out...");
    resetJourneyData();
    logout();
  };

  const depots = [
    'London', 'Liverpool', 'Manchester', 'Leeds',
    'Birmingham', 'Glasgow', 'Cardiff', 'Aberdeen'
  ];

  return (
    <>
      <form className="start-form" onSubmit={handleSubmit} style={{ position: 'relative' }}>
        {error && <div className="form-error">{error}</div>}
        {isFetchingLocationOnSubmit && <div className="form-info">Getting current location...</div>}

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

        <div className="form-group">
          <label htmlFor="pallets">Number of Pallets:</label>
          <input type="number" id="pallets" name="pallets" value={formData.pallets} onChange={handleChange} min="0"/>
        </div>

        <div className="form-group">
          <label htmlFor="vehicleModel">Vehicle Model:</label>
          <select id="vehicleModel" name="vehicleModel" value={formData.vehicleModel} onChange={handleChange}>
             {formData.fuelType === 'Diesel' ? ( <> <option value="VOLVO FH 520">VOLVO FH 520</option> <option value="VOLVO FL 420">VOLVO FL 420</option> <option value="DAF XF 105.510">DAF XF 105.510</option> <option value="DAF XG 530">DAF XG 530</option> <option value="SCANIA R 450">SCANIA R 450</option> </> )
             : formData.fuelType === 'Hydrogen' ? ( <> <option value="HVS HGV">HVS HGV</option> <option value="HVS MCV">HVS MCV</option> <option value="Hymax Series">Hymax Series</option> </> )
             : ( <> <option value="Volvo FE Electric">Volvo FE Electric</option> <option value="DAF CF Electric">DAF CF Electric</option> <option value="Mercedes eActros">Mercedes eActros</option> <option value="MAN eTGM">MAN eTGM</option> <option value="Renault E-Tech D">Renault E-Tech D</option> <option value="Scania BEV">Scania BEV</option> <option value="Volvo FL Electric">Volvo FL Electric</option> <option value="FUSO eCanter">FUSO eCanter</option> <option value="Freightliner eCascadia">Freightliner eCascadia</option> <option value="BYD ETM6">BYD ETM6</option> </> )}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="originDepot">Origin Depot:</label>
          <select id="originDepot" name="originDepot" value={formData.originDepot} onChange={handleChange}>
            <option value="GPS">My Current Location</option>
            {depots.map(depot => (<option key={depot} value={depot}>{depot}</option>))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="destinationDepot">Destination Depot:</label>
          <select id="destinationDepot" name="destinationDepot" value={formData.destinationDepot} onChange={handleChange}>
             {depots.map(depot => (<option key={depot} value={depot}>{depot}</option>))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="vehicleAge">Vehicle Age:</label>
          <input type="number" id="vehicleAge" name="vehicleAge" value={formData.vehicleAge} onChange={handleChange} min="0" />
        </div>

        <div className="form-group">
          <label htmlFor="fuelAtOrigin">Fuel at Origin (%):</label>
          <input type="number" id="fuelAtOrigin" name="fuelAtOrigin" value={formData.fuelAtOrigin} onChange={handleChange} min="0" max="100"/>
        </div>

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

        <div className="form-group">
          <label htmlFor="dispatchTime">Dispatch Time Window:</label>
          <input type="time" id="dispatchTime" name="dispatchTime" step="1" value={formData.dispatchTime} onChange={handleChange} />
        </div>

        <div className="form-group">
          <label htmlFor="journeyDate">Journey Date:</label>
          <select id="journeyDate" name="journeyDate" value={formData.journeyDate} onChange={handleChange}>
             {getUpcomingDates().map(date => (<option key={date.value} value={date.value}>{date.label}</option> ))}
          </select>
        </div>

        <div className="form-buttons">
          <button
            ref={processButtonRef}
            type="submit"
            className="submit-btn"
            disabled={isFetchingLocationOnSubmit}
          >
            Process
          </button>
          <button type="button" className="reset-btn" onClick={handleReset}>New Query</button>
          <button type="button" className="logout-btn" onClick={handleLogoutAndReset}>Logout</button>
        </div>

        {showProcessedWarning && (
          <div ref={warningBoxRef} className="processed-warning-box">
            <div className="warning-box-pointer"></div>
            <p>A journey result is already displayed.</p>
            <p>Please click 'New Query'</p>
          </div>
        )}
      </form>
    </>
  );
}