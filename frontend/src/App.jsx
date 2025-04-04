import { useContext } from "react";
import "leaflet/dist/leaflet.css";
import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet-routing-machine/dist/leaflet-routing-machine.css";
import logoViolet from "./assets/logo-violet.png";
import Login from "./components/Login";
import AdminDashboard from "./components/AdminDashboard";
import { AppContext } from "./AppContext";
import { AuthContext } from "./AuthContext";
import LeftBar from "./components/LeftBar";
import FloatingCards from "./components/FloatingCards";
import RouteDisplay from "./components/RouteDisplay";
import Loading from "./components/Loading";
import "./components/Loading.css";

export default function App() {
  const { 
    isLoggedIn, 
    userRole, 
    loading: authLoading 
  } = useContext(AuthContext);
  
  const { 
    journeyProcessed, 
    selectedOrigin, 
    selectedDestination, 
    isLoading 
  } = useContext(AppContext);

 // If auth is still loading, show appropriate loading screen
if (authLoading) {
  // Check if user is logging out or authenticating
  const isLoggingOut = isLoggedIn === true && userRole !== null;
  return <Loading message={isLoggingOut ? "Logging out..." : "Authenticating..."} />;
}

  // If not logged in, show login page
  if (!isLoggedIn) {
    return <Login />;
  }
  
  // If logged in as admin, show admin dashboard
  if (userRole === 'admin') {
    return <AdminDashboard />;
  }
  
  // Otherwise show the map application for regular users
  return (
    <>
      <MapContainer center={[53.0, -2.0]} zoom={6} zoomControl={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {/* Only display route when a journey is processed */}
        {journeyProcessed && selectedOrigin && selectedDestination && (
          <RouteDisplay 
            origin={selectedOrigin} 
            destination={selectedDestination} 
          />
        )}
      </MapContainer>
      <FloatingCards /> 
      <LeftBar />
      <div className="map-logo">
        <img src={logoViolet} alt="Logo" />
      </div>

      {/* Show loading overlay when loading */}
      {isLoading && <Loading message="Calculating optimal route..." />}
    </>
  );
}