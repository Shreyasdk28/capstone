#!/usr/bin/env python

import os
import sys
import csv
import traci
import random
from datetime import datetime

# Add SUMO_HOME to PATH if not already there
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

def analyze_network():
    """Analyze the network structure and return lane information"""
    lane_info = {}
    print("\nAnalyzing network structure:")
    print("-" * 50)
    print("All available lanes in the network:")
    print("-" * 50)
    
    for edge_id in traci.edge.getIDList():
        try:
            num_lanes = traci.edge.getLaneNumber(edge_id)
            print(f"\nEdge {edge_id}:")
            for lane_idx in range(num_lanes):
                lane_id = f"{edge_id}_{lane_idx}"
                length = traci.lane.getLength(lane_id)
                lane_info[lane_id] = length
                print(f"  Lane {lane_id}: {length:.3f}m")
        except traci.TraCIException as e:
            print(f"Warning: Could not analyze lane {edge_id}: {e}")
    
    return lane_info

class TrafficController:
    def __init__(self):
        self.current_phase = 0
        self.min_green_time = 5
        self.max_green_time = 20
        self.yellow_time = 3
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Analyze network structure
        self.lane_info = analyze_network()
        
        # Get all traffic light IDs from the network
        self.traffic_lights = traci.trafficlight.getIDList()
        print(f"Found traffic lights: {self.traffic_lights}")
        
        # Create detector IDs for each approach of each intersection
        self.detector_ids = {
            "10074640066": {
                ":10074640066_1_0": "detector_10074640066_1_0",
                ":10074640066_1_1": "detector_10074640066_1_1",
                ":10074640066_3_0": "detector_10074640066_3_0",
                ":10074640066_3_1": "detector_10074640066_3_1"
            },
            "10074640049": {
                ":10074640049_1_0": "detector_10074640049_1_0",
                ":10074640049_2_0": "detector_10074640049_2_0"
            },
            "10074640060": {
                ":10074640060_4_0": "detector_10074640060_4_0",
                ":10074640060_5_0": "detector_10074640060_5_0"
            }
        }
        
        self.log_file = "logs/traffic_log.csv"
        self._init_logging()

    def _init_logging(self):
        """Initialize the CSV log file with headers"""
        try:
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                headers = ['Timestamp', 'TrafficLight_ID']
                for tl_id in self.detector_ids.keys():
                    for lane in self.detector_ids[tl_id].keys():
                        headers.append(f"{tl_id}_{lane}_Density")
                headers.extend(['Selected_Phase', 'Green_Duration'])
                writer.writerow(headers)
        except Exception as e:
            print(f"Warning: Could not initialize log file: {e}")

    def get_traffic_density(self, tl_id):
        """Get traffic density for all approaches of a specific intersection"""
        densities = {}
        if tl_id in self.detector_ids:
            for lane, detector_id in self.detector_ids[tl_id].items():
                try:
                    vehicle_count = traci.inductionloop.getLastStepVehicleNumber(detector_id)
                    occupancy = traci.inductionloop.getLastStepOccupancy(detector_id)
                    densities[lane] = (vehicle_count * occupancy) / 100.0
                except traci.TraCIException:
                    try:
                        vehicle_count = traci.lane.getLastStepVehicleNumber(lane)
                        length = traci.lane.getLength(lane)
                        densities[lane] = vehicle_count / length if length > 0 else 0
                    except traci.TraCIException:
                        densities[lane] = 0
        return densities

    def determine_next_phase(self, tl_id, densities):
        """Determine the next traffic signal phase based on traffic density"""
        if not densities:
            return None
            
        max_density = max(densities.values())
        candidates = [
            lane for lane, density in densities.items()
            if density == max_density
        ]
        
        if len(candidates) > 1:
            return random.choice(candidates)
        return candidates[0]

    def calculate_green_time(self, density):
        """Calculate green time based on traffic density"""
        green_time = self.min_green_time + (
            (self.max_green_time - self.min_green_time) * density
        )
        return min(max(green_time, self.min_green_time), self.max_green_time)

    def log_traffic_data(self, tl_id, densities, selected_phase, green_time):
        """Log traffic data and controller decisions"""
        try:
            with open(self.log_file, 'a', newline='') as f:
                writer = csv.writer(f)
                row = [datetime.now(), tl_id]
                if tl_id in self.detector_ids:
                    for lane in self.detector_ids[tl_id].keys():
                        row.append(densities.get(lane, 0))
                row.extend([selected_phase, green_time])
                writer.writerow(row)
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")

    def run(self):
        """Main control loop"""
        try:
            while traci.simulation.getMinExpectedNumber() > 0:
                # Process each traffic light
                for tl_id in self.traffic_lights:
                    try:
                        densities = self.get_traffic_density(tl_id)
                        next_phase = self.determine_next_phase(tl_id, densities)
                        if next_phase is None:
                            continue
                            
                        green_time = self.calculate_green_time(densities[next_phase])
                        
                        current_phase = traci.trafficlight.getPhase(tl_id)
                        traci.trafficlight.setPhase(tl_id, current_phase)
                        traci.trafficlight.setPhaseDuration(tl_id, green_time)
                        
                        self.log_traffic_data(tl_id, densities, next_phase, green_time)
                    except Exception as e:
                        print(f"Warning: Error processing traffic light {tl_id}: {e}")
                        continue
                
                traci.simulationStep()

        except Exception as e:
            print(f"Error in simulation: {e}")
        finally:
            traci.close()

def main():
    sumo_binary = "sumo-gui"
    sumo_cmd = [sumo_binary, "-c", "config/simulation.sumocfg"]
    
    try:
        traci.start(sumo_cmd)
        controller = TrafficController()
        controller.run()
    except Exception as e:
        print(f"Error starting simulation: {e}")

if __name__ == "__main__":
    main() 