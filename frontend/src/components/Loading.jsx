import React, { useState, useEffect } from 'react';

// Loading component with spinner and message
const Loading = ({ message = "Processing your request..." }) => {
  const [dots, setDots] = useState('');
  
  // Animate dots for a more dynamic loading message
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prevDots => {
        if (prevDots.length >= 3) return '';
        return prevDots + '.';
      });
    }, 500);
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="loading-overlay">
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p className="loading-message">{message}{dots}</p>
      </div>
    </div>
  );
};

export default Loading;