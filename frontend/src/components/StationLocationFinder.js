
export const getStationLocationNames = async (stations) => {
    if (!stations || !stations.length) {
      console.log("No station coordinates provided");
      return [];
    }
    
    
    try {
      const locationPromises = stations.map(async (station) => {
        const [lat, lng] = station.coordinates;
        
        const response = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`,
          {
            headers: {
              'User-Agent': 'TransportLogisticsApp/1.0'
            }
          }
        );
        
        if (!response.ok) {
          throw new Error(`Geocoding API error: ${response.status}`);
        }
        
        const data = await response.json();
        
        let locationName = '';
        
        if (data.address) {
          const address = data.address;
          
          const components = [];
          
          if (address.road) components.push(address.road);
          
          if (address.suburb) components.push(address.suburb);
          else if (address.neighbourhood) components.push(address.neighbourhood);
          
          if (address.city) components.push(address.city);
          else if (address.town) components.push(address.town);
          else if (address.village) components.push(address.village);
          
          locationName = components.length > 0 
            ? components.join(', ') 
            : data.display_name.split(',').slice(0, 2).join(',');
        } else {
          locationName = data.display_name || `Station at ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        }
        
        const firstPart = locationName.split(',')[0].trim();
        const stationName = `${firstPart} Station`;
        
        
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
  