import React, { useEffect, useRef } from 'react';
import './FuelGauge.css';

const FuelGauge = ({ value, maxValue, type }) => {
  const pathRef = useRef(null);
  const [pathLength, setPathLength] = React.useState(188); 
  
  const percentage = Math.min(100, Math.max(0, (value / maxValue) * 100));
  
  const getColor = () => {
    if (percentage < 30) return '#e74c3c'; 
    if (percentage < 60) return '#f39c12'; 
    return '#2ecc71'; 
  };
  
  const rotationAngle = -90 + (percentage * 180 / 100);
  
  useEffect(() => {
    if (pathRef.current) {
      const length = pathRef.current.getTotalLength();
      setPathLength(length);
    }
  }, []);
  
  return (
    <div className="fuel-gauge">
      <svg className='fuelBar' width="250" height="120" viewBox="0 0 150 100">
        <path 
          ref={pathRef}
          d="M 15,85 A 70,70 0 0,1 135,85" 
          stroke="#e0e0e0" 
          strokeWidth="10" 
          fill="none" 
        />
        
        <path 
          d="M 15,85 A 70,70 0 0,1 135,85" 
          stroke={getColor()} 
          strokeWidth="10" 
          strokeDasharray={pathLength}
          strokeDashoffset={pathLength * (1 - percentage / 100)} 
          fill="none" 
        />
        
        <line 
          x1="75" 
          y1="85" 
          x2="75" 
          y2="55" 
          stroke="#333" 
          strokeWidth="2" 
          transform={`rotate(${rotationAngle}, 75, 85)`} 
        />
        
        <circle cx="75" cy="85" r="5" fill="#333" />
        
        <text x="10" y="70" fontSize="12" fill="#666">0</text>
        <text x="70" y="40" fontSize="12" fill="#666">50%</text>
        <text x="130" y="70" fontSize="12" fill="#666">100%</text>
      </svg>
    </div>
  );
};

export default FuelGauge;