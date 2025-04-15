import React, { useEffect, useState, useContext, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet-routing-machine';
import markerImg from "../assets/marker.png";
import dieselPumpImg from "../assets/diesel-pump.png";
import hydrogenPumpImg from "../assets/hydrogen-pump.png";
import chargingStationImg from "../assets/charging-station.png"; // Add this image asset
import { AppContext } from '../AppContext';

// Import the station location finder
import { getStationLocationNames } from './StationLocationFinder';

// Import the station card component for single station display
import StationCard from './StationCard';

// Depot coordinates mapping (UK cities)
const depotCoordinates = {
  'London': [51.5074, -0.1278],
  'Liverpool': [53.4084, -2.9916],
  'Manchester': [53.4808, -2.2426],
  'Leeds': [53.8008, -1.5491],
  'Birmingham': [52.4862, -1.8904],
  'Glasgow': [55.8642, -4.2518],
  'Cardiff': [51.4816, -3.1791],
  'Aberdeen': [57.1497, -2.0943]
};

const RouteDisplay = ({ origin, destination }) => {
  const map = useMap();
  const [routeControl, setRouteControl] = useState(null);
  const mapLayersRef = useRef([]);
  const [selectedStationIndex, setSelectedStationIndex] = useState(null);
  
  const { 
    setIsLoading,
    routeData,
    journeyProcessed,
    stationDataList,
    setStationDataList
  } = useContext(AppContext);

  // Get the current fuel type from sessionStorage
  const getCurrentFuelType = () => {
    try {
      return sessionStorage.getItem('currentFuelType') || 'Diesel';
    } catch (e) {
      console.error("Error accessing sessionStorage:", e);
      return 'Diesel'; // Default to Diesel if error
    }
  };

  // Clean up all map elements
  const cleanupMap = () => {
    // Remove all layers we've added to the map
    mapLayersRef.current.forEach(layer => {
      if (map.hasLayer(layer)) {
        map.removeLayer(layer);
      }
    });
    
    // Clear the layers array
    mapLayersRef.current = [];
    
    // Clean up route control
    if (routeControl) {
      map.removeControl(routeControl);
      setRouteControl(null);
    }
    
    // Also try to remove all layers with a more brute-force approach
    map.eachLayer(layer => {
      // Don't remove the tile layer (base map)
      if (!(layer instanceof L.TileLayer)) {
        map.removeLayer(layer);
      }
    });
  };

  // Add a layer to the map and track it for cleanup
  const addLayerToMap = (layer) => {
    layer.addTo(map);
    mapLayersRef.current.push(layer);
    return layer;
  };

  // Effect to get station location names when route data changes
  useEffect(() => {
    if (routeData && routeData.stations && routeData.stations.length > 0) {
      console.log("Found stations in route data:", routeData.stations);
      
      // Clear existing station data when route data changes
      setStationDataList([]);
      
      // Get location names for stations
      getStationLocationNames(routeData.stations)
        .then(locationsWithNames => {
          console.log("Stations with location names:", locationsWithNames);
        })
        .catch(error => {
          console.error("Error getting station location names:", error);
        });
    }
  }, [routeData, setStationDataList]);

  useEffect(() => {
    // Clean up previous route elements
    cleanupMap();
    
    if (!origin || !destination || !journeyProcessed) return;

    // Get the fuel type
    const fuelType = getCurrentFuelType();
    console.log("Current fuel type:", fuelType);

    // Get coordinates for origin and destination
    const startPoint = depotCoordinates[origin] || [51.5074, -0.1278]; // Default to London
    const endPoint = depotCoordinates[destination] || [53.4808, -2.2426]; // Default to Manchester

    // Create custom icon using the marker image from assets
    const customIcon = L.icon({
      iconUrl: markerImg,
      iconSize: [38, 38],
      iconAnchor: [19, 38],
      popupAnchor: [0, -38]
    });

    // Create custom icon for fuel stations based on fuel type
    const getFuelStationIcon = () => {
      if (fuelType === 'Electric') {
        return L.icon({
          iconUrl: chargingStationImg,
          iconSize: [32, 32],
          iconAnchor: [16, 32],
          popupAnchor: [0, -32]
        });
      } else if (fuelType === 'Hydrogen') {
        return L.icon({
          iconUrl: hydrogenPumpImg,
          iconSize: [32, 32],
          iconAnchor: [16, 32],
          popupAnchor: [0, -32]
        });
      } else {
        return L.icon({
          iconUrl: dieselPumpImg,
          iconSize: [32, 32],
          iconAnchor: [16, 32],
          popupAnchor: [0, -32]
        });
      }
    };

    const fuelStationIcon = getFuelStationIcon();

    // Create new markers and route line
    if (routeData && routeData.coordinates && routeData.coordinates.length > 0) {
      // If we have route coordinates from the API
      const routeCoordinates = routeData.coordinates.map(coord => L.latLng(coord[0], coord[1]));
      
      // Create a polyline for the route
      const routeLine = addLayerToMap(L.polyline(routeCoordinates, {
        color: '#6f42c1',
        weight: 6,
        opacity: 0.8
      }));
      
      // Add origin marker
      addLayerToMap(L.marker(routeCoordinates[0], { icon: customIcon, draggable: false })
        .bindPopup(`${origin} (Origin)`));
      
      // Add destination marker
      addLayerToMap(L.marker(routeCoordinates[routeCoordinates.length - 1], { icon: customIcon, draggable: false  })
        .bindPopup(`${destination} (Destination)`));
      
      // Add fuel station markers if present
      if (routeData.stations && routeData.stations.length > 0) {
        // First try to get location names (async)
        getStationLocationNames(routeData.stations)
          .then(stationsWithNames => {
            // Store station names in session storage for Energy tab
            try {
              sessionStorage.setItem('stationNames', JSON.stringify(
                stationsWithNames.map(station => station.stationName)
              ));
            } catch (e) {
              console.error("Error storing station names:", e);
            }
            
            // Add markers with actual location names
            stationsWithNames.forEach((station, index) => {
              const stationCoord = L.latLng(station.coordinates[0], station.coordinates[1]);
              const marker = L.marker(stationCoord, { icon: fuelStationIcon, draggable: false });
              
              // Add click handler to show single station card
              marker.on('click', () => {
                setSelectedStationIndex(index);
              });
              
              const stationTypeLabel = fuelType === 'Electric' ? 'Charging' : fuelType;
              marker.bindPopup(`${stationTypeLabel} ${station.stationName}`);
              
              addLayerToMap(marker);
            });
          })
          .catch(() => {
            // Fallback to simple stations without location names
            routeData.stations.forEach((station, index) => {
              const stationCoord = L.latLng(station.coordinates[0], station.coordinates[1]);
              const marker = L.marker(stationCoord, { icon: fuelStationIcon, draggable: false });
              
              // Add click handler to show single station card
              marker.on('click', () => {
                setSelectedStationIndex(index);
              });
              
              const stationTypeLabel = fuelType === 'Electric' ? 'Charging' : fuelType;
              marker.bindPopup(`${stationTypeLabel} Station ${index + 1}`);
              
              addLayerToMap(marker);
            });
          });
      }
      
      // Fit map to route bounds
      map.fitBounds(routeLine.getBounds(), { padding: [50, 50] });
      
    } else {
      // Fallback to default routing if no API data
      const newRouteControl = L.Routing.control({
        waypoints: [
          L.latLng(startPoint[0], startPoint[1]),
          L.latLng(endPoint[0], endPoint[1])
        ],
        routeWhileDragging: false,
        showAlternatives: false,
        lineOptions: {
          styles: [
            { color: '#6f42c1', opacity: 0.8, weight: 6 },
            { color: '#5e35b1', opacity: 0.9, weight: 4 }
          ]
        },
        createMarker: function(i, waypoint, n) {
          // Use the custom marker for both origin and destination
          const marker = L.marker(waypoint.latLng, { icon: customIcon });
          
          // Add a popup to distinguish between origin and destination
          marker.bindPopup(i === 0 ? `${origin} (Origin)` : `${destination} (Destination)`);
          
          // Add to tracked layers
          mapLayersRef.current.push(marker);
          
          return marker;
        }
      }).addTo(map);

      // Add route calculation complete listener
      newRouteControl.on('routesfound', function(e) {
        // Route calculation complete, hide loading indicator
        setIsLoading(false);
      });

      // Hide the itinerary panel
      const container = newRouteControl.getContainer();
      if (container) {
        container.style.display = 'none';
      }

      setRouteControl(newRouteControl);
      
      // Fit map bounds to route
      const bounds = L.latLngBounds([startPoint, endPoint]);
      map.fitBounds(bounds, { padding: [50, 50] });
    }

    // Clean up function
    return cleanupMap;
  }, [map, origin, destination, setIsLoading, routeData, journeyProcessed]);

  // Close station card when clicking outside
  useEffect(() => {
    const handleMapClick = (e) => {
      // Check if the click is on a marker (has original event property)
      if (!e.originalEvent) return;
      
      // Check if the click is on the map and not on a marker or station card
      const stationCard = document.querySelector('.single-station-card');
      if (stationCard && !stationCard.contains(e.originalEvent.target)) {
        // Check if click was directly on the map (not on a marker)
        const markers = document.querySelectorAll('.leaflet-marker-icon');
        let clickedOnMarker = false;
        
        markers.forEach(marker => {
          if (marker.contains(e.originalEvent.target)) {
            clickedOnMarker = true;
          }
        });
        
        if (!clickedOnMarker) {
          setSelectedStationIndex(null);
        }
      }
    };
    
    map.on('click', handleMapClick);
    
    return () => {
      map.off('click', handleMapClick);
    };
  }, [map]);

  // Force cleanup when component unmounts
  useEffect(() => {
    return cleanupMap;
  }, []);

  // Render the single station card if a station is selected
  return (
    <>
      {selectedStationIndex !== null && stationDataList && stationDataList[selectedStationIndex] && (
        <StationCard 
          stationData={stationDataList[selectedStationIndex]} 
          onClose={() => setSelectedStationIndex(null)}
        />
      )}
    </>
  );
};

export default RouteDisplay;