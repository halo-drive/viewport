import { useEffect, useRef, useContext, useState } from "react";
import { AppContext } from "../AppContext";
import analytics from "../assets/analytics.png";
import cost from "../assets/cost.png";
import energy from "../assets/energy.png";
import fleet from "../assets/fleet.png";
import journey from "../assets/journey.png";
import SlidingPanel from "./SlidingPanel";
import StationCards from "./StationCards";
import start from "../assets/start.png";

export default function LeftBar() {
  const paneRef = useRef(null);
  const { 
    journeyProcessed, 
    activePane, 
    setActivePane 
  } = useContext(AppContext);

  useEffect(() => {
    function handleClickOutside(event) {
      if (paneRef.current && !paneRef.current.contains(event.target)) {
        setActivePane(null);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [setActivePane]);

  const [showEnergyCards, setShowEnergyCards] = useState(false);

  const togglePane = (paneName) => {
    if (paneName === "energy") {
      if (journeyProcessed) {
        setShowEnergyCards(!showEnergyCards);
        setActivePane(null);
      }
      return;
    }
    
    if (!journeyProcessed && paneName !== "start") {
      return;
    }
    
    if (showEnergyCards) {
      setShowEnergyCards(false);
    }
    
    setActivePane(activePane === paneName ? null : paneName);
  };

  return (
    <>
      <div ref={paneRef}>
        <div className="left-bar">
          <button className="bar-button" onClick={() => togglePane("start")}>
            <img src={start} alt="start" className="button-logo" />
            <span className="button-label">start</span>
          </button>
          <button 
            className={`bar-button ${!journeyProcessed ? "disabled-button" : ""}`} 
            onClick={() => togglePane("energy")}
          >
            <img src={energy} alt="energy" className="button-logo" />
            <span className="button-label">energy</span>
          </button>
          <button 
            className={`bar-button ${!journeyProcessed ? "disabled-button" : ""}`} 
            onClick={() => togglePane("cost")}
          >
            <img src={cost} alt="cost" className="button-logo" />
            <span className="button-label">cost</span>
          </button>
          <button 
            className={`bar-button ${!journeyProcessed ? "disabled-button" : ""}`} 
            onClick={() => togglePane("journey")}
          >
            <img src={journey} alt="journey" className="button-logo" />
            <span className="button-label">journey</span>
          </button>
          <button 
            className={`bar-button ${!journeyProcessed ? "disabled-button" : ""}`} 
            onClick={() => togglePane("fleet")}
          >
            <img src={fleet} alt="fleet" className="button-logo" />
            <span className="button-label">fleet</span>
          </button>
          <button 
            className={`bar-button ${!journeyProcessed ? "disabled-button" : ""}`} 
            onClick={() => togglePane("analytics")}
          >
            <img src={analytics} alt="analytics" className="button-logo" />
            <span className="button-label">analytics</span>
          </button>
        </div>
        
        <SlidingPanel />
      </div>
      
      {showEnergyCards && journeyProcessed && <StationCards onClose={() => setShowEnergyCards(false)} />}
    </>
  );
}