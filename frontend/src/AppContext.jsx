import { createContext, useState, useEffect } from 'react'; // Added useEffect

export const AppContext = createContext(null);

export const AppProvider = ({ children }) => {
  const [journeyProcessed, setJourneyProcessed] = useState(false);
  const [selectedOrigin, setSelectedOrigin] = useState(null); // This can be city name or 'GPS'
  const [selectedDestination, setSelectedDestination] = useState(null);
  const [activePane, setActivePane] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [routeData, setRouteData] = useState(null);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [energyData, setEnergyData] = useState(null); // Energy data
  const [stationDataList, setStationDataList] = useState([]); // Store station data list

  // New state for live tracking
  const [liveLocation, setLiveLocation] = useState({ lat: null, lon: null });
  const [isTracking, setIsTracking] = useState(false);
  const [gpsOriginCoords, setGpsOriginCoords] = useState(null); // Store initial GPS coords if used

  // Watcher ID ref
  const watchIdRef = useState(null);

  // Effect to handle watching position
  useEffect(() => {
    if (isTracking) {
      console.log("Starting location tracking...");
      if ('geolocation' in navigator) {
        watchIdRef.current = navigator.geolocation.watchPosition(
          (position) => {
            // console.log("Watcher Update:", position.coords); // For debugging frequency
            setLiveLocation({
              lat: position.coords.latitude,
              lon: position.coords.longitude,
            });
          },
          (error) => {
            console.error("Error watching position:", error);
            // Optionally stop tracking if persistent error occurs
            // setIsTracking(false);
          },
          {
            enableHighAccuracy: true,
            maximumAge: 0, // Request fresh position data
            timeout: 10000, // Time before error callback is invoked (10s)
          }
        );
      } else {
        console.error("Geolocation is not supported by this browser.");
        setIsTracking(false); // Cannot track
      }
    } else {
      // Cleanup: Clear watcher if tracking stops
      if (watchIdRef.current !== null) {
        console.log("Stopping location tracking...");
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
        setLiveLocation({ lat: null, lon: null }); // Reset live location
      }
    }

    // Cleanup function for component unmount
    return () => {
      if (watchIdRef.current !== null) {
        console.log("Stopping location tracking on unmount...");
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
  }, [isTracking]); // Dependency array ensures this runs when isTracking changes


  // Reset function to clear data when starting a new journey
  const resetJourneyData = () => {
    setJourneyProcessed(false);
    setSelectedOrigin(null);
    setSelectedDestination(null);
    setRouteData(null);
    setAnalyticsData(null);
    setEnergyData(null);
    setStationDataList([]); // Also clear station data
    setIsTracking(false); // Stop tracking on reset
    setGpsOriginCoords(null); // Clear initial GPS coords

    // Clear session storage
    sessionStorage.removeItem('currentFuelType');
    sessionStorage.removeItem('stationNames');
    sessionStorage.removeItem('lastFormData'); // Also clear saved form
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
      // Add live tracking state and setters
      liveLocation,
      setLiveLocation, // Might not be needed externally if App manages update
      isTracking,
      setIsTracking,
      gpsOriginCoords,
      setGpsOriginCoords
    }}>
      {children}
    </AppContext.Provider>
  );
};