import React, { useContext } from 'react';
import { AppContext } from '../AppContext';

import totalFuel from '../assets/totalFuel.png';
import totalOverhead from '../assets/totalOverhead.png';
import efficiency from '../assets/efficiency.png';
import consumption from '../assets/consumption.png';
import perMile from '../assets/perMile.png';

export default function FloatingCards() {
    const { journeyProcessed, analyticsData } = useContext(AppContext);
    
    // If journey isn't processed, don't render the cards
    if (!journeyProcessed || !analyticsData) return null;
    
    // Get the current fuel type from sessionStorage
    const getCurrentFuelType = () => {
        try {
            return sessionStorage.getItem('currentFuelType') || 'Diesel';
        } catch (e) {
            console.error("Error accessing sessionStorage:", e);
            return 'Diesel'; // Default to Diesel if error
        }
    };
    
    const fuelType = getCurrentFuelType();
    
    // Get appropriate units based on fuel type
    const getEfficiencyUnit = () => {
        if (fuelType === 'Electric') {
            return 'mi/kWh';
        } else if (fuelType === 'Hydrogen') {
            return 'mi/kg';
        } else {
            return 'mpg';
        }
    };
    
    const getConsumptionUnit = () => {
        if (fuelType === 'Electric') {
            return 'kWh';
        } else if (fuelType === 'Hydrogen') {
            return 'kg';
        } else {
            return 'gal';
        }
    };
    
    // Create card data from real analytics data
    const cardData = [
        {
            id: 1,
            title: `Total ${fuelType === 'Electric' ? 'Energy' : 'Fuel'} Cost`,
            value: `£${analyticsData.total_fuel_cost}`,
            icon: totalFuel,
            color: "#4e7aff"
        },
        {
            id: 2,
            title: "Fuel + Overhead Cost",
            value: `£${analyticsData.total_final_cost}`,
            icon: totalOverhead,
            color: "#ff6b6b"
        },
        {
            id: 3,
            title: `${fuelType === 'Electric' ? 'Energy' : 'Fuel'} Efficiency`,
            value: `${analyticsData.efficiency_prediction} ${getEfficiencyUnit()}`,
            icon: efficiency,
            color: "#4ecdc4"
        },
        {
            id: 4,
            title: `${fuelType === 'Electric' ? 'Energy' : 'Fuel'} Consumption`,
            value: `${analyticsData.total_required_fuel} ${getConsumptionUnit()}`,
            icon: consumption,
            color: "#ffbe0b"
        },
        {
            id: 5,
            title: "Cost per Mile",
            value: `£${analyticsData.cost_per_mile}`,
            icon: perMile,
            color: "#8a2be2"
        }
    ];
  
    return (
        <div className="floating-cards-container">
            {cardData.map(card => (
                <div 
                    key={card.id} 
                    className="floating-card"
                    style={{ borderTop: `3px solid ${card.color}` }}
                >
                    <div className="card-icon" style={{ backgroundColor: `${card.color}20` }}>
                        <img src={card.icon} alt={card.title} className="card-icon-img" />
                    </div>
                    <div className="card-content">
                        <h3 className="card-title">{card.title}</h3>
                        <p className="card-value">{card.value}</p>
                    </div>
                </div>
            ))}
        </div>
    );
}