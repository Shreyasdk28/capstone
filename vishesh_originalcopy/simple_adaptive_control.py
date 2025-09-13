#!/usr/bin/env python3
"""
Simple Adaptive Traffic Control System with RSUs
"""
import os
import sys
import traci
import time
from collections import defaultdict

# Add SUMO tools to Python path
if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
sys.path.append(tools)

class RSU:
    def __init__(self, rsu_id, position, edges, range=100):
        self.id = rsu_id
        self.position = position
        self.range = range
        self.edges = edges
        self.connected_vehicles = set()
        self.edge_vehicle_count = defaultdict(int)
    
    def update_vehicle_count(self, vehicle_positions):
        """Update vehicle count for each edge in range"""
        self.edge_vehicle_count.clear()
        for edge in self.edges:
            self.edge_vehicle_count[edge] = 0
            
        for veh_id, pos in vehicle_positions.items():
            if self.in_range(pos):
                # Find the closest edge
                min_dist = float('inf')
                closest_edge = None
                for edge in self.edges:
                    edge_pos = self.get_edge_position(edge)
                    if edge_pos is None:
                        continue
                    dist = ((pos[0]-edge_pos[0])**2 + (pos[1]-edge_pos[1])**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        closest_edge = edge
                if closest_edge is not None:
                    self.edge_vehicle_count[closest_edge] += 1
    
    def get_edge_position(self, edge_id):
        """Get position of an edge (approximated as the middle point)"""
        try:
            lane_id = f"{edge_id}_0"
            shape = traci.lane.getShape(lane_id)
            if shape:
                return shape[len(shape)//2]
        except:
            return None
    
    def in_range(self, position):
        """Check if a position is within this RSU's range"""
        dx = self.position[0] - position[0]
        dy = self.position[1] - position[1]
        return (dx*dx + dy*dy) <= (self.range * self.range)

def create_rsus():
    """Create RSUs at fixed positions for demonstration"""
    rsus = []
    # Add RSUs at fixed positions (you can adjust these coordinates)
    rsus.append(RSU("rsu1", (1000, 500), ["edge1", "edge2"], 150))
    rsus.append(RSU("rsu2", (1500, 500), ["edge3", "edge4"], 150))
    return rsus

def adjust_traffic_lights(rsus):
    """Simple traffic light adjustment based on vehicle density"""
    for rsu in rsus:
        if not rsu.edges:
            continue
            
        try:
            # Get all vehicles in the network
            vehicle_ids = traci.vehicle.getIDList()
            
            # Get vehicle positions in range
            vehicle_positions = {}
            for veh_id in vehicle_ids:
                try:
                    pos = traci.vehicle.getPosition(veh_id)
                    if rsu.in_range(pos):
                        vehicle_positions[veh_id] = pos
                except:
                    continue
            
            # Update vehicle counts per edge
            rsu.update_vehicle_count(vehicle_positions)
            
            # Visual feedback: change RSU color based on traffic density
            total_vehicles = sum(rsu.edge_vehicle_count.values())
            if total_vehicles > 5:
                # Red for high traffic
                traci.poi.setColor(f"{rsu.id}_poi", (255, 0, 0, 255))
            elif total_vehicles > 2:
                # Yellow for medium traffic
                traci.poi.setColor(f"{rsu.id}_poi", (255, 255, 0, 255))
            else:
                # Green for low traffic
                traci.poi.setColor(f"{rsu.id}_poi", (0, 255, 0, 255))
                
        except Exception as e:
            print(f"Error in RSU {rsu.id}: {str(e)}")
            continue

def run_simulation():
    """Main simulation loop"""
    try:
        # Start SUMO with GUI
        sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
        sumo_cmd = [
            sumo_binary,
            "-c", "test_config.sumocfg",
            "--start",
            "--quit-on-end",
            "--gui-settings-file", "viewsettings.xml"
        ]
        
        print("Starting SUMO with command:", " ".join(sumo_cmd))
        
        # Start TraCI connection
        traci.start(sumo_cmd)
        
        # Set up visualization
        traci.gui.setSchema("View #0", "real world")
        
        # Create RSUs
        rsus = create_rsus()
        print(f"Created {len(rsus)} RSUs")
        
        # Add RSUs to visualization
        for rsu in rsus:
            traci.poi.add(f"{rsu.id}_poi", *rsu.position, (0, 255, 0, 255), 5, rsu.id)
        
        # Main simulation loop
        step = 0
        max_steps = 1000  # Limit simulation steps for testing
        
        while traci.simulation.getMinExpectedNumber() > 0 and step < max_steps:
            traci.simulationStep()
            step += 1
            
            # Adjust traffic lights every 10 seconds
            if step % 100 == 0:
                adjust_traffic_lights(rsus)
                print(f"Step {step}: Adjusted traffic lights")
        
        print("Simulation completed successfully.")
        
    except Exception as e:
        print(f"Error in simulation: {e}")
    finally:
        try:
            traci.close()
        except:
            pass

if __name__ == "__main__":
    run_simulation()
