import { createContext, useState } from 'react';

export const AppContext = createContext(null);

export const AppProvider = ({ children }) => {
  const [journeyProcessed, setJourneyProcessed] = useState(false);
  const [selectedOrigin, setSelectedOrigin] = useState(null);
  const [selectedDestination, setSelectedDestination] = useState(null);
  const [activePane, setActivePane] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [routeData, setRouteData] = useState(null);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [energyData, setEnergyData] = useState(null); // Energy data
  const [stationDataList, setStationDataList] = useState([]); // Store station data list

  // Reset function to clear data when starting a new journey
  const resetJourneyData = () => {
    setJourneyProcessed(false);
    setSelectedOrigin(null);
    setSelectedDestination(null);
    setRouteData(null);
    setAnalyticsData(null);
    setEnergyData(null);
    setStationDataList([]); // Also clear station data
    
    // Clear session storage
    sessionStorage.removeItem('currentFuelType');
    sessionStorage.removeItem('stationNames');
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
      resetJourneyData
    }}>
      {children}
    </AppContext.Provider>
  );
};