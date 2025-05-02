import React, { useContext, useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { AppContext } from '../AppContext';
import gpsIcon from '../assets/gps.png'; // Make sure this path is correct
import './GoToLocationControl.css';

const GoToLocationControl = () => {
  const map = useMap();
  const { liveLocation } = useContext(AppContext);

  useEffect(() => {
    if (map.buttons && map.buttons.goToLocation) {
        return;
    }

    const GoToLocationButton = L.Control.extend({
      options: {
        position: 'topright'
      },

      onAdd: function(map) {
        const container = L.DomUtil.create('div', 'leaflet-control leaflet-control-custom gps-button-container');
        const button = L.DomUtil.create('a', 'gps-button', container);
        const img = L.DomUtil.create('img', '', button);
        img.src = gpsIcon;
        img.alt = 'Go to Current Location';
        
        button.href = '#';
        button.role = 'button';
        button.ariaLabel = 'Go to Current Location';

        L.DomEvent.disableClickPropagation(container);
        L.DomEvent.on(button, 'click', L.DomEvent.stop);
        L.DomEvent.on(button, 'click', () => {
          // Prioritize liveLocation if available
          if (liveLocation && liveLocation.lat && liveLocation.lon) {
            // Use flyTo for smooth animation
            map.flyTo([liveLocation.lat, liveLocation.lon], 15, { // Target zoom level 15
              animate: true,
              duration: 1.5 // Animation duration in seconds (adjust as desired)
            });
          } else {
            // Fallback: Use map.locate but without setView: true
            if ('geolocation' in navigator) {
              console.log("Attempting to locate user...");
              // Trigger location search, animation will happen in 'locationfound' event
              map.locate({ maxZoom: 15 });
            } else {
               alert("Geolocation is not supported by your browser.");
            }
          }
        });

        // Remove previous listeners before adding new ones to prevent duplicates
        map.off('locationfound');
        map.off('locationerror');

        // Handle location found: Use flyTo here instead of map.locate's setView
        map.on('locationfound', (e) => {
             console.log("Location found:", e.latlng);
             // Smoothly fly to the found location
             // Determine target zoom: use map's current zoom if it's already higher than 15, else use 15
             const targetZoom = Math.max(map.getZoom(), 15);
             map.flyTo(e.latlng, targetZoom, {
               animate: true,
               duration: 1.5 // Animation duration in seconds
             });
        });

        // Handle location error
        map.on('locationerror', (e) => {
             console.error("Leaflet location error:", e.message);
             alert(`Could not retrieve your current location: ${e.message}`);
        });

        this._button = button;
        return container;
      },

      onRemove: function(map) {
        if (this._button) {
          L.DomEvent.off(this._button);
        }
        // Make sure to remove the specific listeners added in onAdd
        map.off('locationfound');
        map.off('locationerror');
        console.log("GoToLocationControl removed");
      }
    });

    const goToLocationControl = new GoToLocationButton();
    goToLocationControl.addTo(map);

    if (!map.buttons) map.buttons = {};
    map.buttons.goToLocation = goToLocationControl;

    return () => {
       if (map && map.buttons && map.buttons.goToLocation) {
            try {
                map.removeControl(map.buttons.goToLocation);
                delete map.buttons.goToLocation;
            } catch (error) {
                console.warn("Could not remove GoToLocationControl:", error);
            }
       }
    };
  }, [map, liveLocation]); // Keep dependencies

  return null;
};

export default GoToLocationControl;