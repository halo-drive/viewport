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
        // London coordinates (starting point)
        const londonCoordinates = [51.461883, -0.087581];
        
        // Create map centered on London with a lower zoom to show more area
        const map = L.map('map-background', {
          center: londonCoordinates,
          zoom: 10,  // Lower zoom to show more of the UK
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
        
        // Create a continuous panning effect that preloads tiles
        // This uses Leaflet's own methods to ensure tiles are loaded properly
        const panStep = () => {
          const currentCenter = map.getCenter();
          // Move consistently northward (up the UK)
          const newLat = currentCenter.lat + 0.02; // Small increment for smooth movement
          
          // Ensure we're still showing map tiles (stay within UK northern limits)
          if (newLat < 58.5) { // Northern tip of Scotland is around 58.5 latitude
            // Pan to new location
            map.panTo([newLat, currentCenter.lng], {
              animate: true,
              duration: 2.0, // Smooth animation over 2 seconds
              easeLinearity: 1 // Linear movement (no acceleration/deceleration)
            });
            
            // Schedule next pan after this one completes
            setTimeout(panStep, 2100); // Slightly longer than animation duration
          } else {
            // We've reached northern Scotland, reset to London
            // Use a quick fade out/in effect to hide the transition
            document.getElementById('map-background').style.opacity = 0;
            
            setTimeout(() => {
              map.panTo(londonCoordinates, { animate: false });
              document.getElementById('map-background').style.opacity = 1;
              
              // Restart the movement
              setTimeout(panStep, 500);
            }, 1000);
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
    };
  }, []);

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
          <h1 className="login-title">{isSignup ? 'Create Account' : 'Welcome Back'}</h1>
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
              type="email" 
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