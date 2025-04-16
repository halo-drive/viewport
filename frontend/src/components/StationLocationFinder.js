// Function to find location names for stations based on coordinates
// Can be added to RouteDisplay.jsx or as a separate utility

/**
 * Gets location names for coordinates using reverse geocoding
 * @param {Array} coordinates - Array of [lat, lng] coordinates
 * @returns {Promise<Array>} Array of location names
 */
export const getStationLocationNames = async (stations) => {
    if (!stations || !stations.length) {
      console.log("No station coordinates provided");
      return [];
    }
    
    //console.log("Finding location names for stations:", stations);
    
    try {
      const locationPromises = stations.map(async (station) => {
        const [lat, lng] = station.coordinates;
        
        // Using Nominatim OpenStreetMap for reverse geocoding
        // Note: For production use, consider using a geocoding service with appropriate API key
        const response = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`,
          {
            headers: {
              // Add a user agent as required by Nominatim usage policy
              'User-Agent': 'TransportLogisticsApp/1.0'
            }
          }
        );
        
        if (!response.ok) {
          throw new Error(`Geocoding API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Format location name from address components
        let locationName = '';
        
        if (data.address) {
          const address = data.address;
          
          // Try to get a meaningful name based on address components
          const components = [];
          
          // Add road/street if available
          if (address.road) components.push(address.road);
          
          // Add area info
          if (address.suburb) components.push(address.suburb);
          else if (address.neighbourhood) components.push(address.neighbourhood);
          
          // Add city/town
          if (address.city) components.push(address.city);
          else if (address.town) components.push(address.town);
          else if (address.village) components.push(address.village);
          
          // Fallback to display name if no components
          locationName = components.length > 0 
            ? components.join(', ') 
            : data.display_name.split(',').slice(0, 2).join(',');
        } else {
          locationName = data.display_name || `Station at ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        }
        
        // Get the first part before the comma and add "Station"
        const firstPart = locationName.split(',')[0].trim();
        const stationName = `${firstPart} Station`;
        
        //console.log(`Station at [${lat}, ${lng}] -> "${locationName}" -> "${stationName}"`);
        
        return {
          coordinates: [lat, lng],
          name: locationName,
          stationName: stationName,
          rawData: data
        };
      });
      
      const locations = await Promise.all(locationPromises);
      return locations;
    } catch (error) {
      console.error("Error getting location names:", error);
      return stations.map(station => ({
        coordinates: station.coordinates,
        name: `Station at ${station.coordinates[0].toFixed(4)}, ${station.coordinates[1].toFixed(4)}`,
        stationName: `Location Station`
      }));
    }
  };
  
  // Example usage in RouteDisplay.jsx
  /*
  useEffect(() => {
    if (routeData && routeData.stations && routeData.stations.length > 0) {
      // Get location names for stations
      getStationLocationNames(routeData.stations)
        .then(locationsWithNames => {
          console.log("Stations with location names:", locationsWithNames);
        });
    }
  }, [routeData]);
  */