# VANET (Vehicular Ad Hoc Network) Traffic Control System

## Project Overview

This project implements a Vehicular Ad Hoc Network (VANET) for optimizing traffic signal control at an intersection. The system uses SUMO (Simulation of Urban MObility) to simulate traffic flow and implements an intelligent traffic control algorithm that adapts signal timings based on real-time traffic density.

## Project Structure

```
.
├── config/
│   ├── detectors.add.xml     # Detector configurations
│   ├── simulation.sumocfg    # SUMO simulation configuration
│   └── gui-settings.cfg      # GUI settings for visualization
├── traffic/
│   └── controller.py         # Main traffic control logic
├── logs/
│   ├── detector_output.xml   # Raw detector data
│   └── traffic_log.csv       # Traffic density and timing logs
├── net.net.xml              # SUMO network file
├── routes.rou.xml           # Vehicle routes definition
└── README.md                # Project documentation
```

## Features

- Real-time traffic density monitoring using induction loop detectors
- Adaptive traffic signal timing based on current traffic conditions
- Dynamic green time calculation (5-20 seconds) based on traffic density
- Priority-based phase selection for optimal traffic flow
- Comprehensive logging system for traffic data analysis
- Visualization support through SUMO-GUI

## Prerequisites

1. SUMO (Simulation of Urban MObility) - version 1.8.0 or higher
2. Python 3.7 or higher
3. TraCI (Traffic Control Interface) - included with SUMO

## Installation

1. Install SUMO:
   - Windows: Download from [SUMO website](https://sumo.dlr.de/docs/Downloads.php)
   - Set the SUMO_HOME environment variable

2. Clone this repository:
   ```bash
   git clone <repository-url>
   cd vanet-traffic-control
   ```

## Usage

1. Start the simulation:
   ```bash
   python traffic/controller.py
   ```

2. The SUMO-GUI will launch, showing the intersection and vehicle movements
3. Traffic data will be logged to `logs/traffic_log.csv`

## Configuration

### Detector Settings
- Detectors are placed 50 meters from the intersection
- Sampling frequency: 1 second
- Data logged to logs/detector_output.xml

### Traffic Signal Parameters
- Minimum green time: 5 seconds
- Maximum green time: 20 seconds
- Yellow time: 3 seconds

## Data Analysis

The system generates two types of log files:
1. `detector_output.xml`: Raw detector data
2. `traffic_log.csv`: Processed traffic data including:
   - Timestamp
   - Traffic density for each approach
   - Selected phase
   - Green time duration

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- SUMO Team for providing the traffic simulation framework
- Contributors to the TraCI Python API #   c a p s t o n e  
 