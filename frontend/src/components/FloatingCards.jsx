import React, { useContext } from 'react';
import { AppContext } from '../AppContext';

import totalFuel from '../assets/totalFuel.png';
import totalOverhead from '../assets/totalOverhead.png';
import efficiency from '../assets/efficiency.png';
import consumption from '../assets/consumption.png';
import perMile from '../assets/perMile.png';
import co2 from '../assets/co2.png'; 

export default function FloatingCards() {
    const { journeyProcessed, analyticsData } = useContext(AppContext);

    if (!journeyProcessed || !analyticsData) return null;

    const getCurrentFuelType = () => {
        try {
            return sessionStorage.getItem('currentFuelType') || 'Diesel';
        } catch (e) {
            console.error("Error accessing sessionStorage:", e);
            return 'Diesel'; 
        }
    };

    const fuelType = getCurrentFuelType();

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

    const cardData = [
        {
            id: 1,
            title: `Total ${fuelType === 'Electric' ? 'Energy' : 'Fuel'} Cost`,
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

    if (fuelType === 'Diesel' && analyticsData.total_required_fuel !== undefined) {
        let co2Emissions = 'N/A'; 

        const fuelRequired = parseFloat(analyticsData.total_required_fuel);
        if (!isNaN(fuelRequired) && isFinite(fuelRequired)) {
            co2Emissions = (fuelRequired * 10.16).toFixed(2);
        }

        cardData.push({
            id: 6, 
            title: "Carbon Dioxide Emissions",
            value: `${co2Emissions} kg CO2`, 
            icon: co2, 
            color: "#708090" 
        });
    }

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