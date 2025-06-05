# VANET (Vehicular Ad Hoc Network) Project

## Project Overview

This project simulates a **Vehicular Ad Hoc Network (VANET)** for optimizing traffic signal control at an intersection. The simulation is implemented using **SUMO** (Simulation of Urban MObility) software and models a four-way intersection with traffic density detection systems. The system uses **radiation-based sensors** to collect real-time traffic data and determines optimal signal timings based on the traffic density.

## Current Project Structure

```
VANET/
├── controller.py             # Central controller logic for traffic signal optimization
├── detector_output.xml       # Output data from traffic detectors
├── detectors.add.xml         # Configuration for radiation-based detector sensors
├── edges.edg.xml             # Road edges definition for SUMO network
├── network.net.xml           # SUMO network configuration file
├── nodes.nod.xml             # Intersection nodes definition
├── routes.rou.xml            # Vehicle routes and traffic flow configuration
├── simulation.sumocfg        # SUMO simulation configuration
├── README.md                 # Project documentation
└── traffic_log.csv           # Log file for traffic density data and signal timings
```

## Functionality

### Traffic Density Detection System
- The simulation models a four-way intersection with each road equipped with radiation-based sensors implemented as induction loops in SUMO.
- Sensors are placed as pole-like structures (defined in detectors.add.xml) that detect vehicles and measure traffic density.

### Central Controller Logic
- `controller.py` implements the central intersection controller that:
  - Collects real-time traffic density information from sensors
  - Analyzes traffic data to determine which lanes have the highest density
  - Implements a priority-based tie-breaker system
  - Dynamically adjusts signal timings (5-20 seconds) based on traffic conditions
  - Logs traffic data and decisions to `traffic_log.csv`

## How to Run the Simulation

1. Ensure SUMO and TraCI are installed on your system.
2. Run the controller script:
   ```bash
   python controller.py
   ```
3. The simulation will launch in SUMO-GUI and the controller will begin adjusting traffic signals based on detected vehicle density.

## Technologies Used

- **SUMO**: For traffic simulation and modeling
- **Python**: For implementing the controller logic
- **TraCI (Traffic Control Interface)**: For real-time interaction with the SUMO simulation

## Future Plans

- Organize files into a more structured directory format
- Implement AI-based decision-making for dynamic traffic signal adjustments
- Expand to a network of multiple intersections
- Add vehicle-to-vehicle (V2V) communication capabilities
- Integrate with real-world data sources