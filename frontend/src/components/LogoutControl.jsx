import React, { useContext, useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { AuthContext } from '../AuthContext';
import { AppContext } from '../AppContext'; // Import AppContext
import logoutIcon from '../assets/logout.png';
import './LogoutControl.css'; // Ensure CSS is imported

const LogoutControl = () => {
  const map = useMap();
  const { logout } = useContext(AuthContext);
  const { resetJourneyData } = useContext(AppContext); // Get resetJourneyData

  useEffect(() => {
    // Prevent adding multiple controls if component re-renders
    if (map.buttons && map.buttons.logout) {
        return;
    }

    const LogoutButton = L.Control.extend({
      options: {
        position: 'topright' // Position in the top right corner
      },

      onAdd: function(map) {
        // Create the container and button elements
        const container = L.DomUtil.create('div', 'leaflet-control leaflet-control-custom logout-button-container');
        const button = L.DomUtil.create('a', 'logout-button', container);
        const img = L.DomUtil.create('img', '', button);
        img.src = logoutIcon;
        img.alt = 'Logout';
        // NOTE: Inline styles for width/height removed to allow CSS control
        button.href = '#';
        button.role = 'button';
        button.ariaLabel = 'Logout';

        // Prevent map interactions when clicking the button
        L.DomEvent.disableClickPropagation(container);
        L.DomEvent.on(button, 'click', L.DomEvent.stop);
        L.DomEvent.on(button, 'click', () => {
          console.log("Logout button clicked: Resetting journey and logging out..."); // Optional: for debugging
          resetJourneyData(); // Call reset first
          logout();         // Then call logout
        });

        this._button = button;
        return container;
      },

      onRemove: function(map) {
        // Clean up event listeners
        if (this._button) {
          L.DomEvent.off(this._button);
        }
        console.log("LogoutControl removed");
      }
    });

    // Add the control to the map
    const logoutControl = new LogoutButton();
    logoutControl.addTo(map);

    // Store reference to prevent duplicates
    if (!map.buttons) map.buttons = {};
    map.buttons.logout = logoutControl;


    // Cleanup function to remove the control when the component unmounts
    return () => {
       if (map && map.buttons && map.buttons.logout) {
            try {
                map.removeControl(map.buttons.logout);
                delete map.buttons.logout;
            } catch (error) {
                console.warn("Could not remove LogoutControl:", error);
            }
       }
    };
  }, [map, logout, resetJourneyData]); // Add resetJourneyData to dependencies

  // This component only adds the control to the map, it doesn't render anything itself
  return null;
};

export default LogoutControl;