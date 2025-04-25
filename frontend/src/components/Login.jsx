import React, { useState, useContext, useEffect, useRef } from 'react';
import './Login.css';
import logoViolet from '../assets/logo-violet.png';
import { AuthContext } from '../AuthContext';
import 'leaflet/dist/leaflet.css';

export default function Login() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSignup, setIsSignup] = useState(false);
  const mapRef = useRef(null);
  
  const { login, signup, loading, error } = useContext(AuthContext);
  
  useEffect(() => {
    // We need to dynamically import Leaflet because it requires window
    const initMap = async () => {
      // Only import leaflet on client-side
      const L = await import('leaflet');

      // Initialize map if it doesn't exist yet
      if (!mapRef.current) {
        // Define coordinates
        const londonCoordinates = [51.461883, -0.087581];
        const glasgowCoordinates = [55.8642, -4.2518]; // Glasgow coordinates

        // --- Calculate direction vector ---
        const startLat = londonCoordinates[0];
        const startLon = londonCoordinates[1];
        const endLat = glasgowCoordinates[0];
        const endLon = glasgowCoordinates[1];

        const deltaLat = endLat - startLat; // Total change in latitude
        const deltaLon = endLon - startLon; // Total change in longitude

        // --- Define step size ---
        // Keep vertical movement similar to before for consistent speed feel
        const latStep = 0.02;
        // Calculate proportional longitude step (avoid division by zero if deltaLat is 0)
        const lonStep = (deltaLat !== 0) ? deltaLon * (latStep / deltaLat) : 0;
        // -----------------------------

        // Create map centered on London
        const map = L.map('map-background', {
          center: londonCoordinates,
          zoom: 10, // Lower zoom to show more of the UK
          zoomControl: false,
          attributionControl: false,
          dragging: false,
          scrollWheelZoom: false,
          doubleClickZoom: false,
          keyboard: false,
          touchZoom: false
        });

        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        // Store map reference
        mapRef.current = map;

        // Create a continuous panning effect towards Glasgow
        const panStep = () => {
          const currentCenter = map.getCenter();

          // Calculate next position
          const newLat = currentCenter.lat + latStep;
          const newLon = currentCenter.lng + lonStep;

          // Check if we've reached or passed Glasgow's latitude
          // (Since we're moving north, we check if newLat is still less than endLat)
          if (newLat < endLat) {
            // Pan to new location along the angled line
            map.panTo([newLat, newLon], {
              animate: true,
              duration: 2.0, // Smooth animation over 2 seconds
              easeLinearity: 1 // Linear movement
            });

            // Schedule next pan after this one completes
            setTimeout(panStep, 2100); // Slightly longer than animation duration
          } else {
            // We've reached Glasgow (or slightly passed), reset to London
            // Optional: Snap exactly to Glasgow first for a brief moment?
            // map.panTo(glasgowCoordinates, { animate: false });

            // Use a quick fade out/in effect to hide the transition
            document.getElementById('map-background').style.opacity = 0;

            setTimeout(() => {
              map.panTo(londonCoordinates, { animate: false }); // Reset to London
              document.getElementById('map-background').style.opacity = 1;

              // Restart the movement
              setTimeout(panStep, 500); // Wait half a second before starting again
            }, 1000); // Fade transition time
          }
        };

        // Start the panning effect
        panStep();
      }
    };

    initMap();

    // Clean up on unmount
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
      // Clear any pending timeouts if component unmounts mid-animation
      // Note: This requires storing timeout IDs, adding complexity.
      // For a purely decorative background, maybe not strictly necessary.
    };
  }, []); // Empty dependency array ensures this runs only once

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (isSignup) {
      if (!username || !email || !password) {
        alert('Please fill in all fields');
        return;
      }
      
      const result = await signup(username, email, password);
      if (result.success) {
        alert(result.message);
        setIsSignup(false); // Switch back to login
        setUsername('');
        setEmail('');
        setPassword('');
      }
    } else {
      if (!email || !password) {
        alert('Please fill in all fields');
        return;
      }
      
      await login(email, password);
    }
  };

  const togglePassword = () => {
    setShowPassword(!showPassword);
  };

  return (
    <div className="login-container">
      <div id="map-background" className="map-container"></div>
      <div className="overlay-gradient"></div>
      <div className="login-card">
        <div className="login-header">
          <img src={logoViolet} alt="Logo" className="login-logo" />
          <h1 className="login-title">{isSignup ? 'Create Account' : ''}</h1>
        </div>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          {isSignup && (
            <div className="form-group">
              <i className="fa fa-user-circle input-icon"></i>
              <input 
                className="form-input" 
                type="text" 
                placeholder="Username" 
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required 
              />
            </div>
          )}
          
          <div className="form-group">
            <i className="fa fa-envelope input-icon"></i>
            <input 
              className="form-input" 
               
              placeholder="Email Address" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
          </div>
          
          <div className="form-group">
            <i className="fa fa-lock input-icon"></i>
            <input 
              className="form-input" 
              type={showPassword ? "text" : "password"} 
              placeholder="Password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
            <button 
              type="button" 
              className="password-toggle" 
              onClick={togglePassword}
              tabIndex="-1"
            >
              <i className={`fa ${showPassword ? "fa-eye-slash" : "fa-eye"}`}></i>
            </button>
          </div>
          
          <button 
            type="submit" 
            className="primary-button" 
            disabled={loading}
          >
            {loading 
              ? (isSignup ? "Creating Account..." : "Signing In...") 
              : (isSignup ? "Sign Up" : "Sign In")
            }
          </button>
          
          <div className="secondary-actions">
            {!isSignup && (
              <button type="button" className="text-button">
                Forgot Password?
              </button>
            )}
            <button 
              type="button" 
              className="text-button"
              onClick={() => {
                setIsSignup(!isSignup);
                setUsername('');
                setEmail('');
                setPassword('');
              }}
            >
              {isSignup ? "Already have an account? Sign In" : "Need an account? Sign Up"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
