import { createContext, useState, useEffect } from 'react'; 

export const AppContext = createContext(null);

export const AppProvider = ({ children }) => {
  const [journeyProcessed, setJourneyProcessed] = useState(false);
  const [selectedOrigin, setSelectedOrigin] = useState(null); 
  const [selectedDestination, setSelectedDestination] = useState(null);
  const [activePane, setActivePane] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [routeData, setRouteData] = useState(null);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [energyData, setEnergyData] = useState(null); 
  const [stationDataList, setStationDataList] = useState([]); 

  const [liveLocation, setLiveLocation] = useState({ lat: null, lon: null });
  const [isTracking, setIsTracking] = useState(false);
  const [gpsOriginCoords, setGpsOriginCoords] = useState(null); 

  const watchIdRef = useState(null);

  useEffect(() => {
    if (isTracking) {
      console.log("Starting location tracking...");
      if ('geolocation' in navigator) {
        watchIdRef.current = navigator.geolocation.watchPosition(
          (position) => {
            setLiveLocation({
              lat: position.coords.latitude,
              lon: position.coords.longitude,
            });
          },
          (error) => {
            console.error("Error watching position:", error);
          },
          {
            enableHighAccuracy: true,
            maximumAge: 0, 
            timeout: 10000,
          }
        );
      } else {
        console.error("Geolocation is not supported by this browser.");
        setIsTracking(false); 
      }
    } else {
      if (watchIdRef.current !== null) {
        console.log("Stopping location tracking...");
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
        setLiveLocation({ lat: null, lon: null }); 
      }
    }

    return () => {
      if (watchIdRef.current !== null) {
        console.log("Stopping location tracking on unmount...");
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
  }, [isTracking]); 


  const resetJourneyData = () => {
    setJourneyProcessed(false);
    setSelectedOrigin(null);
    setSelectedDestination(null);
    setRouteData(null);
    setAnalyticsData(null);
    setEnergyData(null);
    setStationDataList([]); 
    setIsTracking(false); 
    setGpsOriginCoords(null); 

    sessionStorage.removeItem('currentFuelType');
    sessionStorage.removeItem('stationNames');
    sessionStorage.removeItem('lastFormData'); 
  };

  return (
    <AppContext.Provider value={{
      journeyProcessed,
      setJourneyProcessed,
      selectedOrigin,
      setSelectedOrigin,
      selectedDestination,
      setSelectedDestination,
      activePane,
      setActivePane,
      isLoading,
      setIsLoading,
      routeData,
      setRouteData,
      analyticsData,
      setAnalyticsData,
      energyData,
      setEnergyData,
      stationDataList,
      setStationDataList,
      resetJourneyData,
      liveLocation,
      setLiveLocation, 
      isTracking,
      setIsTracking,
      gpsOriginCoords,
      setGpsOriginCoords
    }}>
      {children}
    </AppContext.Provider>
  );
};