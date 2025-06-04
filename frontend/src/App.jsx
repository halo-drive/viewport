import { useContext } from "react"; 
import "leaflet/dist/leaflet.css"; 
import { MapContainer, TileLayer } from "react-leaflet"; 
import "leaflet-routing-machine/dist/leaflet-routing-machine.css"; 
import logoViolet from "./assets/logo-violet.png"; 

import Login from "./components/Login";
import AdminDashboard from "./components/AdminDashboard";
import LeftBar from "./components/LeftBar";
import FloatingCards from "./components/FloatingCards";
import RouteDisplay from "./components/RouteDisplay";
import Loading from "./components/Loading";
import GoToLocationControl from "./components/GoToLocationControl"; 
import LogoutControl from "./components/LogoutControl"; 

import { AppContext } from "./AppContext";
import { AuthContext } from "./AuthContext"; 

import "./components/Loading.css";
import "./components/LogoutControl.css"; 

import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';


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
    isLoading, 
    isTracking
  } = useContext(AppContext);


  if (authLoading) {
    const isLoggingOut = isLoggedIn === true && userRole !== null;
    return <Loading message={isLoggingOut ? "Logging out..." : "Authenticating..."} />;
  }

  if (!isLoggedIn) {
    return <Login />;
  }

  if (userRole === 'admin') {
    return <AdminDashboard />;
  }

  return (
    <>
      <ToastContainer
        position="bottom-center"
        autoClose={6000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="dark"
        style={{ zIndex: 99999 }}
      />
      <MapContainer
          center={[53.0, -2.0]} 
          zoom={6}             
          zoomControl={false}     
          style={{ height: "100vh", width: "100%" }} 
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" 
        />
        
        <LogoutControl />

        {journeyProcessed && selectedOrigin === 'GPS' && isTracking && (
          <GoToLocationControl />
        )}

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
      {isLoading && <Loading message="Calculating optimal route..." />}
    </>
  );
}