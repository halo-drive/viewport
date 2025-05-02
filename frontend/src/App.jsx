// App.jsx
import { useContext } from "react"; // React hook for context
import "leaflet/dist/leaflet.css"; // Leaflet base CSS
import { MapContainer, TileLayer } from "react-leaflet"; // React Leaflet components
import "leaflet-routing-machine/dist/leaflet-routing-machine.css"; // Routing machine CSS
import logoViolet from "./assets/logo-violet.png"; // App logo

// Core components
import Login from "./components/Login";
import AdminDashboard from "./components/AdminDashboard";
import LeftBar from "./components/LeftBar";
import FloatingCards from "./components/FloatingCards";
import RouteDisplay from "./components/RouteDisplay";
import Loading from "./components/Loading";
import GoToLocationControl from "./components/GoToLocationControl"; // GPS control
import LogoutControl from "./components/LogoutControl"; // New Logout control

// Contexts
import { AppContext } from "./AppContext";
import { AuthContext } from "./AuthContext"; // Ensure AuthContext is imported

// CSS Imports
import "./components/Loading.css";
import "./components/LogoutControl.css"; // CSS for Logout control
// import "./components/GoToLocationControl.css"; // CSS for GPS control (ensure it's loaded if needed)


export default function App() {
  // Consume Authentication Context - *** Restored this section ***
  const {
    isLoggedIn,
    userRole,
    loading: authLoading // Rename loading from AuthContext to avoid naming conflict
  } = useContext(AuthContext);

  // Consume Application Context
  const {
    journeyProcessed,
    selectedOrigin,
    selectedDestination,
    isLoading, // Loading state from AppContext (e.g., for route calculation)
    isTracking
  } = useContext(AppContext);

  // --- Authentication Flow ---

  // 1. Show loading indicator while checking auth status or logging out/in
  if (authLoading) {
    // Check if we were previously logged in to show "Logging out..." message
    const isLoggingOut = isLoggedIn === true && userRole !== null;
    return <Loading message={isLoggingOut ? "Logging out..." : "Authenticating..."} />;
  }

  // 2. If not logged in, show the Login component
  if (!isLoggedIn) {
    return <Login />;
  }

  // 3. If logged in as admin, show the Admin Dashboard
  if (userRole === 'admin') {
    return <AdminDashboard />;
  }

  // --- Main Application View (Logged-in User) ---
  return (
    <>
      <MapContainer
          center={[53.0, -2.0]} // Initial map center (UK focus)
          zoom={6}              // Initial zoom level
          zoomControl={false}     // Disable default zoom control if using custom
          style={{ height: "100vh", width: "100%" }} // Full screen map
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" // Standard OpenStreetMap tiles
        />

        {/* --- Map Controls --- */}

        {/* Always display Logout button when logged in (as Login/Admin screens are handled above) */}
        <LogoutControl />

        {/* Conditionally display Go To Location button */}
        {/* Render only if: A journey is processed, The origin was GPS, Live tracking is active */}
        {journeyProcessed && selectedOrigin === 'GPS' && isTracking && (
          <GoToLocationControl />
        )}

        {/* --- Map Overlays --- */}

        {/* Display the calculated route if available */}
        {journeyProcessed && selectedOrigin && selectedDestination && (
          <RouteDisplay
            origin={selectedOrigin}
            destination={selectedDestination}
          />
        )}
      </MapContainer>

      {/* --- Other UI Elements (Outside Map Container) --- */}
      <FloatingCards />
      <LeftBar /> {/* This renders the SlidingPanel which contains StartForm */}
      <div className="map-logo">
        <img src={logoViolet} alt="Logo" />
      </div>

      {/* Show loading overlay for app-specific actions (e.g., route calculation) */}
      {isLoading && <Loading message="Calculating optimal route..." />}
    </>
  );
}