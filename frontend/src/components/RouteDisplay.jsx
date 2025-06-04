import React, { useEffect, useState, useContext, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet-routing-machine';
import markerImg from "../assets/marker.png"; 
import dieselPumpImg from "../assets/diesel-pump.png";
import hydrogenPumpImg from "../assets/hydrogen-pump.png";
import chargingStationImg from "../assets/charging-station.png";
import { AppContext } from '../AppContext';
import { getStationLocationNames } from './StationLocationFinder';
import StationCard from './StationCard';
import './pulsatingIcon.css';

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

  const routeLineLayerRef = useRef(null);
  const originMarkerLayerRef = useRef(null);
  const currentPosMarkerLayerRef = useRef(null); 
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

  useEffect(() => {
    cleanupMap();

    if (!origin || !destination || !journeyProcessed) return;

    const fuelType = getCurrentFuelType();

    const originDestIcon = L.icon({ iconUrl: markerImg, iconSize: [38, 38], iconAnchor: [19, 38], popupAnchor: [0, -38] });
    const getFuelStationIcon = () => {
      let iconUrl = dieselPumpImg;
      if (fuelType === 'Electric') iconUrl = chargingStationImg;
      else if (fuelType === 'Hydrogen') iconUrl = hydrogenPumpImg;
      return L.icon({ iconUrl: iconUrl, iconSize: [32, 32], iconAnchor: [16, 32], popupAnchor: [0, -32] });
    };
    const fuelStationIcon = getFuelStationIcon();

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

    if (routeData && routeData.coordinates && routeData.coordinates.length > 0) {
      const routeCoordinates = routeData.coordinates.map(coord => L.latLng(coord[0], coord[1]));

      const polyline = L.polyline(routeCoordinates, { color: '#6f42c1', weight: 6, opacity: 0.8 });
      routeLineLayerRef.current = addLayerToMap(polyline);

      if (origin !== 'GPS') {
        const actualStartLatLng = routeCoordinates[0]; 
        const originMarker = L.marker(actualStartLatLng, { icon: originDestIcon, draggable: false })
          .bindPopup(`${origin} (Origin)`);
        originMarkerLayerRef.current = addLayerToMap(originMarker);
      } else {
         originMarkerLayerRef.current = null;
      }

      addLayerToMap(L.marker(routeCoordinates[routeCoordinates.length - 1], { icon: originDestIcon, draggable: false })
        .bindPopup(`${destination} (Destination)`));

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
      console.warn("No route data from backend, falling back to leaflet-routing-machine.");
      const startLatLng = L.latLng(startPointCoords[0], startPointCoords[1]);
      const endLatLng = L.latLng(endPointCoords[0], endPointCoords[1]);

      const newRouteControl = L.Routing.control({
        waypoints: [ startLatLng, endLatLng ],
        routeWhileDragging: false, showAlternatives: false,
        lineOptions: { styles: [{ color: '#6f42c1', opacity: 0.8, weight: 6 }] },
        createMarker: (i, waypoint) => {
          if (i === 1 || origin !== 'GPS') {
             const marker = L.marker(waypoint.latLng, { icon: originDestIcon });
             marker.bindPopup(i === 0 ? `${origin} (Origin)` : `${destination} (Destination)`);
             mapLayersRef.current.push(marker);
             if (i === 0) originMarkerLayerRef.current = marker; 
             return marker;
          }
          return null; 
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


  const throttledUpdate = useRef(throttle((newLatLng) => {
    const pulsatingIcon = L.divIcon({
      className: 'pulsating-dot-container', 
      html: '<div class="pulsating-dot"></div>',
      iconSize: [15, 15], 
      iconAnchor: [7.5, 7.5] 
    });

    if (origin === 'GPS' && routeLineLayerRef.current) {
        const latlngs = routeLineLayerRef.current.getLatLngs();
        if (latlngs && latlngs.length > 0) {
            latlngs[0] = newLatLng; 
            routeLineLayerRef.current.setLatLngs(latlngs);
        }
    }
    if (currentPosMarkerLayerRef.current) {
        currentPosMarkerLayerRef.current.setLatLng(newLatLng);
    } else {
         const currentPosMarker = L.marker(newLatLng, {
             icon: pulsatingIcon, 
             zIndexOffset: 1000 
         }).bindPopup("Your Current Location");
         currentPosMarkerLayerRef.current = addLayerToMap(currentPosMarker);
    }
  }, 1000)).current; 

  useEffect(() => {
    if (isTracking && liveLocation.lat && liveLocation.lon) {
       const newLatLng = L.latLng(liveLocation.lat, liveLocation.lon);
       throttledUpdate(newLatLng);
    } else {
       if (currentPosMarkerLayerRef.current) {
           if (map.hasLayer(currentPosMarkerLayerRef.current)) {
               map.removeLayer(currentPosMarkerLayerRef.current);
           }
           mapLayersRef.current = mapLayersRef.current.filter(layer => layer !== currentPosMarkerLayerRef.current);
           currentPosMarkerLayerRef.current = null;
       }
    }
  }, [isTracking, liveLocation, throttledUpdate, origin]); 


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