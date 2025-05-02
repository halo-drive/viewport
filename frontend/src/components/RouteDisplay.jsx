import React, { useEffect, useState, useContext, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet-routing-machine';
import markerImg from "../assets/marker.png"; // Origin/Destination Marker (kept for non-GPS origin)
// Removed: import currentPosMarkerImg from "../assets/marker-current.png"; // We'll use CSS instead
import dieselPumpImg from "../assets/diesel-pump.png";
import hydrogenPumpImg from "../assets/hydrogen-pump.png";
import chargingStationImg from "../assets/charging-station.png";
import { AppContext } from '../AppContext';
import { getStationLocationNames } from './StationLocationFinder';
import StationCard from './StationCard';
import './pulsatingIcon.css'; // <-- Import the new CSS file

// Depot coordinates mapping (UK cities) - Used for non-GPS origin/destination fallback
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

// Throttle function (unchanged)
function throttle(func, limit) {
  let inThrottle;
  return function() {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  }
}

const RouteDisplay = ({ origin, destination }) => {
  const map = useMap();
  const [routeControl, setRouteControl] = useState(null);
  const [selectedStationIndex, setSelectedStationIndex] = useState(null);

  // Refs for Leaflet layers
  const routeLineLayerRef = useRef(null);
  const originMarkerLayerRef = useRef(null);
  const currentPosMarkerLayerRef = useRef(null); // Marker for live position (will use pulsating icon)
  const mapLayersRef = useRef([]);

  const {
    setIsLoading,
    routeData,
    journeyProcessed,
    stationDataList,
    liveLocation,
    isTracking,
    gpsOriginCoords
  } = useContext(AppContext);

  const getCurrentFuelType = () => {
    try { return sessionStorage.getItem('currentFuelType') || 'Diesel'; }
    catch (e) { console.error("Error accessing sessionStorage:", e); return 'Diesel'; }
  };

  const addLayerToMap = (layer) => {
    layer.addTo(map);
    mapLayersRef.current.push(layer);
    return layer;
  };

  const cleanupMap = () => {
    mapLayersRef.current.forEach(layer => {
      if (map.hasLayer(layer)) map.removeLayer(layer);
    });
    mapLayersRef.current = [];
    if (routeControl) {
      map.removeControl(routeControl);
      setRouteControl(null);
    }
    map.eachLayer(layer => {
      if (!(layer instanceof L.TileLayer)) map.removeLayer(layer);
    });
    routeLineLayerRef.current = null;
    originMarkerLayerRef.current = null;
    currentPosMarkerLayerRef.current = null;
  };

  // --- Effect to Draw Initial Route ---
  useEffect(() => {
    cleanupMap();

    if (!origin || !destination || !journeyProcessed) return;

    const fuelType = getCurrentFuelType();

    // --- Define Icons ---
    const originDestIcon = L.icon({ iconUrl: markerImg, iconSize: [38, 38], iconAnchor: [19, 38], popupAnchor: [0, -38] });
    // Pulsating icon is defined later in the live update section
    const getFuelStationIcon = () => {
      let iconUrl = dieselPumpImg;
      if (fuelType === 'Electric') iconUrl = chargingStationImg;
      else if (fuelType === 'Hydrogen') iconUrl = hydrogenPumpImg;
      return L.icon({ iconUrl: iconUrl, iconSize: [32, 32], iconAnchor: [16, 32], popupAnchor: [0, -32] });
    };
    const fuelStationIcon = getFuelStationIcon();
    // --- End Icons ---

    // --- Determine Start Point ---
    let startPointCoords;
    if (origin === 'GPS' && gpsOriginCoords) {
      startPointCoords = [gpsOriginCoords.lat, gpsOriginCoords.lon];
    } else if (origin !== 'GPS') {
      startPointCoords = depotCoordinates[origin] || depotCoordinates['London'];
    } else {
      console.error("Origin is GPS but no coordinates available initially.");
      return;
    }
    const endPointCoords = depotCoordinates[destination] || depotCoordinates['Manchester'];
    // --- End Start Point ---

    // --- Draw Route based on routeData from Backend ---
    if (routeData && routeData.coordinates && routeData.coordinates.length > 0) {
      const routeCoordinates = routeData.coordinates.map(coord => L.latLng(coord[0], coord[1]));

      const polyline = L.polyline(routeCoordinates, { color: '#6f42c1', weight: 6, opacity: 0.8 });
      routeLineLayerRef.current = addLayerToMap(polyline);

      // --- MODIFICATION START: Conditional Origin Marker ---
      // Only add the standard origin marker if the origin is NOT GPS
      if (origin !== 'GPS') {
        const actualStartLatLng = routeCoordinates[0]; // Use first point of polyline for depot origin
        const originMarker = L.marker(actualStartLatLng, { icon: originDestIcon, draggable: false })
          .bindPopup(`${origin} (Origin)`);
        originMarkerLayerRef.current = addLayerToMap(originMarker);
      } else {
        // If origin is GPS, originMarkerLayerRef remains null initially.
        // The pulsating marker will represent the starting/current GPS location.
         originMarkerLayerRef.current = null;
      }
      // --- MODIFICATION END ---

      // Add Destination Marker (unchanged)
      addLayerToMap(L.marker(routeCoordinates[routeCoordinates.length - 1], { icon: originDestIcon, draggable: false })
        .bindPopup(`${destination} (Destination)`));

      // Add Station Markers (unchanged logic, uses addLayerToMap)
      if (routeData.stations && routeData.stations.length > 0) {
        getStationLocationNames(routeData.stations)
          .then(stationsWithNames => {
            try { sessionStorage.setItem('stationNames', JSON.stringify(stationsWithNames.map(s => s.stationName))); }
            catch (e) { console.error("Error storing station names:", e); }

            stationsWithNames.forEach((station, index) => {
              const stationCoord = L.latLng(station.coordinates[0], station.coordinates[1]);
              const marker = L.marker(stationCoord, { icon: fuelStationIcon, draggable: false });
              marker.on('click', () => setSelectedStationIndex(index));
              const stationTypeLabel = fuelType === 'Electric' ? 'Charging' : fuelType;
              marker.bindPopup(`${stationTypeLabel} ${station.stationName || `Station ${index + 1}`}`);
              addLayerToMap(marker);
            });
          })
          .catch(() => {
             routeData.stations.forEach((station, index) => {
                const stationCoord = L.latLng(station.coordinates[0], station.coordinates[1]);
                const marker = L.marker(stationCoord, { icon: fuelStationIcon, draggable: false });
                marker.on('click', () => setSelectedStationIndex(index));
                const stationTypeLabel = fuelType === 'Electric' ? 'Charging' : fuelType;
                marker.bindPopup(`${stationTypeLabel} Station ${index + 1}`);
                addLayerToMap(marker);
             });
          });
      }

      map.fitBounds(polyline.getBounds(), {
        paddingTopLeft: [0, 100],   
        paddingBottomRight: [0, 0] 
      });

      setIsLoading(false);

    } else {
      // Fallback to leaflet-routing-machine (unchanged)
      console.warn("No route data from backend, falling back to leaflet-routing-machine.");
      const startLatLng = L.latLng(startPointCoords[0], startPointCoords[1]);
      const endLatLng = L.latLng(endPointCoords[0], endPointCoords[1]);

      const newRouteControl = L.Routing.control({
        waypoints: [ startLatLng, endLatLng ],
        routeWhileDragging: false, showAlternatives: false,
        lineOptions: { styles: [{ color: '#6f42c1', opacity: 0.8, weight: 6 }] },
        createMarker: (i, waypoint) => {
          // --- MODIFICATION START: Conditional Origin Marker (Fallback) ---
          // Only create the marker for the destination (i=1) or if origin is not GPS
          if (i === 1 || origin !== 'GPS') {
             const marker = L.marker(waypoint.latLng, { icon: originDestIcon });
             marker.bindPopup(i === 0 ? `${origin} (Origin)` : `${destination} (Destination)`);
             mapLayersRef.current.push(marker);
             if (i === 0) originMarkerLayerRef.current = marker; // Store ref only if depot origin
             return marker;
          }
          return null; // Don't create a marker for GPS origin in fallback
          // --- MODIFICATION END ---
        }
      }).addTo(map);

      newRouteControl.on('routesfound', () => setIsLoading(false));
      const container = newRouteControl.getContainer();
      if (container) container.style.display = 'none';
      setRouteControl(newRouteControl);

      const bounds = L.latLngBounds([startPointCoords, endPointCoords]);
      map.fitBounds(bounds, { padding: [50, 50] });
    }

  }, [map, origin, destination, routeData, journeyProcessed, gpsOriginCoords]);


  // --- Effect for Live Location Update ---
  const throttledUpdate = useRef(throttle((newLatLng) => {
    // --- MODIFICATION START: Define Pulsating Icon ---
    const pulsatingIcon = L.divIcon({
      className: 'pulsating-dot-container', // Optional container class
      html: '<div class="pulsating-dot"></div>', // The div with the pulsating CSS class
      iconSize: [15, 15], // Size of the visible dot
      iconAnchor: [7.5, 7.5] // Center the anchor on the dot
    });
    // --- MODIFICATION END ---

    // --- MODIFICATION START: Update Polyline Start Point if GPS Origin ---
    // If the origin was GPS, update the start of the polyline
    if (origin === 'GPS' && routeLineLayerRef.current) {
        const latlngs = routeLineLayerRef.current.getLatLngs();
        if (latlngs && latlngs.length > 0) {
            latlngs[0] = newLatLng; // Update the first coordinate
            routeLineLayerRef.current.setLatLngs(latlngs);
        }
    }
    // --- MODIFICATION END ---

    // --- MODIFICATION START: Create/Update Pulsating Marker ---
    // Update or create the separate current position marker using the pulsating icon
    if (currentPosMarkerLayerRef.current) {
        currentPosMarkerLayerRef.current.setLatLng(newLatLng);
        // Optionally update icon if needed (e.g., if style changes based on state)
        // currentPosMarkerLayerRef.current.setIcon(pulsatingIcon);
    } else {
         // Create the marker using the divIcon
         const currentPosMarker = L.marker(newLatLng, {
             icon: pulsatingIcon, // Use the divIcon here
             zIndexOffset: 1000 // Ensure it's on top
         }).bindPopup("Your Current Location");
         currentPosMarkerLayerRef.current = addLayerToMap(currentPosMarker);
    }
    // --- MODIFICATION END ---

    // Optional: Pan map to keep marker in view
    // map.panTo(newLatLng);
  }, 1000)).current; // Throttle updates

  useEffect(() => {
    if (isTracking && liveLocation.lat && liveLocation.lon) {
       const newLatLng = L.latLng(liveLocation.lat, liveLocation.lon);
       throttledUpdate(newLatLng);
    } else {
       // If tracking stops, remove the live position marker
       if (currentPosMarkerLayerRef.current) {
           if (map.hasLayer(currentPosMarkerLayerRef.current)) {
               map.removeLayer(currentPosMarkerLayerRef.current);
           }
           mapLayersRef.current = mapLayersRef.current.filter(layer => layer !== currentPosMarkerLayerRef.current);
           currentPosMarkerLayerRef.current = null;
       }
       // --- MODIFICATION START: Restore original polyline if needed ---
       // If tracking stops AND origin was GPS, you might want to reset the
       // polyline to its original state from routeData if you have it stored,
       // or just leave it as is (showing the last tracked start point).
       // Example (leaving as is for now):
       // console.log("Tracking stopped. Polyline shows last tracked start point.");
       // --- MODIFICATION END ---
    }
  }, [isTracking, liveLocation, throttledUpdate, origin]); // Added 'origin' dependency


  // --- Effect for Click Handlers (Station Card, Unchanged) ---
  useEffect(() => {
    const handleMapClick = (e) => {
      if (!e.originalEvent) return;
      const stationCard = document.querySelector('.single-station-card');
      if (stationCard && !stationCard.contains(e.originalEvent.target)) {
        const markers = document.querySelectorAll('.leaflet-marker-icon, .pulsating-dot-container'); // Include pulsating icon container
        let clickedOnMarker = false;
        markers.forEach(marker => { if (marker.contains(e.originalEvent.target)) clickedOnMarker = true; });
        if (!clickedOnMarker) setSelectedStationIndex(null);
      }
    };
    map.on('click', handleMapClick);
    return () => { map.off('click', handleMapClick); };
  }, [map]);

  // --- Effect for Unmount Cleanup (Unchanged) ---
  useEffect(() => {
    return cleanupMap;
  }, []);

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