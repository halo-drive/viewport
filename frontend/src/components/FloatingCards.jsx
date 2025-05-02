import React, { useContext } from 'react';
import { AppContext } from '../AppContext';

import totalFuel from '../assets/totalFuel.png';
import totalOverhead from '../assets/totalOverhead.png';
import efficiency from '../assets/efficiency.png';
import consumption from '../assets/consumption.png';
import perMile from '../assets/perMile.png';
import co2 from '../assets/co2.png'; // Import the new CO2 icon

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
            // Assuming 'Diesel' or default is gallons
            return 'gal';
        }
    };

    // Create base card data from real analytics data
    const cardData = [
        {
            id: 1,
            title: `Total ${fuelType === 'Electric' ? 'Energy' : 'Fuel'} Cost`,
            // Ensure value exists before trying to use it
            value: `£${analyticsData.total_fuel_cost !== undefined ? analyticsData.total_fuel_cost.toFixed(2) : '--'}`,
            icon: totalFuel,
            color: "#4e7aff"
        },
        {
            id: 2,
            title: "Fuel + Overhead Cost",
            value: `£${analyticsData.total_final_cost !== undefined ? analyticsData.total_final_cost.toFixed(2) : '--'}`,
            icon: totalOverhead,
            color: "#ff6b6b"
        },
        {
            id: 3,
            title: `${fuelType === 'Electric' ? 'Energy' : 'Fuel'} Efficiency`,
            value: `${analyticsData.efficiency_prediction !== undefined ? analyticsData.efficiency_prediction.toFixed(2) : '--'} ${getEfficiencyUnit()}`,
            icon: efficiency,
            color: "#4ecdc4"
        },
        {
            id: 4,
            title: `${fuelType === 'Electric' ? 'Energy' : 'Fuel'} Consumption`,
            // Handle potential "Infinity" string from backend
            value: `${(analyticsData.total_required_fuel !== undefined && analyticsData.total_required_fuel !== "Infinity") ? parseFloat(analyticsData.total_required_fuel).toFixed(2) : analyticsData.total_required_fuel || '--'} ${getConsumptionUnit()}`,
            icon: consumption,
            color: "#ffbe0b"
        },
        {
            id: 5,
            title: "Cost per Mile",
            value: `£${analyticsData.cost_per_mile !== undefined ? analyticsData.cost_per_mile.toFixed(2) : '--'}`,
            icon: perMile,
            color: "#8a2be2"
        }
    ];

    // --- Add CO2 Card Conditionally for Diesel ---
    if (fuelType === 'Diesel' && analyticsData.total_required_fuel !== undefined) {
        let co2Emissions = 'N/A'; // Default value

        // Ensure total_required_fuel is a valid number before calculating
        const fuelRequired = parseFloat(analyticsData.total_required_fuel);
        if (!isNaN(fuelRequired) && isFinite(fuelRequired)) {
             // Calculate CO2 emissions (Gallons * 10.16 kg/gallon)
            co2Emissions = (fuelRequired * 10.16).toFixed(2);
        }

        cardData.push({
            id: 6, // Next available ID
            title: "Carbon Dioxide Emissions",
            value: `${co2Emissions} kg CO2`, // Append units if calculated
            icon: co2, // Use the imported CO2 icon
            color: "#708090" // Example color (Slate Gray)
        });
    }
    // --- End CO2 Card Logic ---

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