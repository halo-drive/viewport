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
    const initMap = async () => {
      const L = await import('leaflet');

      if (!mapRef.current) {
        const londonCoordinates = [51.461883, -0.087581];
        const glasgowCoordinates = [55.8642, -4.2518]; 

        const startLat = londonCoordinates[0];
        const startLon = londonCoordinates[1];
        const endLat = glasgowCoordinates[0];
        const endLon = glasgowCoordinates[1];

        const deltaLat = endLat - startLat; 
        const deltaLon = endLon - startLon; 

        const latStep = 0.02;
        const lonStep = (deltaLat !== 0) ? deltaLon * (latStep / deltaLat) : 0;

        const map = L.map('map-background', {
          center: londonCoordinates,
          zoom: 10, 
          zoomControl: false,
          attributionControl: false,
          dragging: false,
          scrollWheelZoom: false,
          doubleClickZoom: false,
          keyboard: false,
          touchZoom: false
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '© OpenStreetMap contributors'
        }).addTo(map);

        mapRef.current = map;

        const panStep = () => {
          const currentCenter = map.getCenter();

          const newLat = currentCenter.lat + latStep;
          const newLon = currentCenter.lng + lonStep;

          if (newLat < endLat) {
            map.panTo([newLat, newLon], {
              animate: true,
              duration: 2.0, 
              easeLinearity: 1 
            });

            setTimeout(panStep, 2100); 
          } else {
            document.getElementById('map-background').style.opacity = 0;
            setTimeout(() => {
              map.panTo(londonCoordinates, { animate: false }); 
              document.getElementById('map-background').style.opacity = 1;
              setTimeout(panStep, 500); 
            }, 1000); 
          }
        };
        panStep();
      }
    };

    initMap();

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
        setIsSignup(false); 
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
