import React, { useContext, useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { AuthContext } from '../AuthContext';
import { AppContext } from '../AppContext'; 
import logoutIcon from '../assets/logout.png';
import './LogoutControl.css'; 

const LogoutControl = () => {
  const map = useMap();
  const { logout } = useContext(AuthContext);
  const { resetJourneyData } = useContext(AppContext); 

  useEffect(() => {
    if (map.buttons && map.buttons.logout) {
        return;
    }

    const LogoutButton = L.Control.extend({
      options: {
        position: 'topright' 
      },

      onAdd: function(map) {
        const container = L.DomUtil.create('div', 'leaflet-control leaflet-control-custom logout-button-container');
        const button = L.DomUtil.create('a', 'logout-button', container);
        const img = L.DomUtil.create('img', '', button);
        img.src = logoutIcon;
        img.alt = 'Logout';
        button.href = '#';
        button.role = 'button';
        button.ariaLabel = 'Logout';

        L.DomEvent.disableClickPropagation(container);
        L.DomEvent.on(button, 'click', L.DomEvent.stop);
        L.DomEvent.on(button, 'click', () => {
          console.log("Logout button clicked: Resetting journey and logging out..."); 
          resetJourneyData(); 
          logout();         
        });

        this._button = button;
        return container;
      },

      onRemove: function(map) {
        if (this._button) {
          L.DomEvent.off(this._button);
        }
        console.log("LogoutControl removed");
      }
    });

    const logoutControl = new LogoutButton();
    logoutControl.addTo(map);

    if (!map.buttons) map.buttons = {};
    map.buttons.logout = logoutControl;


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
  }, [map, logout, resetJourneyData]); 
  
  return null;
};

export default LogoutControl;