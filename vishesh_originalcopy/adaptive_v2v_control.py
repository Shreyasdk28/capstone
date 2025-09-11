#!/usr/bin/env python3
"""
Combined Adaptive Traffic Control and V2V Communication System
"""
import os
import sys
import time
import random
import math
import traci
import sumolib
from sumolib import geomhelper
from collections import defaultdict, deque

# Add SUMO tools to Python path
if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# Add SUMO tools to Python path
tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
sys.path.append(tools)

class RSU:
    def __init__(self, rsu_id, edge_id, lane_pos, range=100):
        self.id = rsu_id
        self.position = None  # Will be set when added to simulation
        self.edge_id = edge_id
        self.edge_id = edge_id
        self.lane_pos = lane_pos
        self.range = range
        self.connected_vehicles = set()
        self.edge_vehicle_count = defaultdict(int)
        self.messages = deque(maxlen=100)  # Store recent messages
        self.poi_id = f"rsu_{rsu_id}"
        self.range_polygon = f"rsu_range_{rsu_id}"
        self.detector_id = f"e1detector_{rsu_id}"
    
    def update_vehicle_count(self, vehicle_positions):
        """Update vehicle count for vehicles in range"""
        self.connected_vehicles.clear()
        
        # Count vehicles in range of this RSU
        for veh_id, pos in vehicle_positions.items():
            if self.in_range(pos):
                self.connected_vehicles.add(veh_id)
        
        # Update edge vehicle count for this RSU's edge
        self.edge_vehicle_count[self.edge_id] = len(self.connected_vehicles)
    
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
    
    def broadcast_message(self, message):
        """Broadcast a message to vehicles in range"""
        self.messages.append((time.time(), message))
        return len(self.messages) - 1  # Return message ID

class Vehicle:
    def __init__(self, veh_id):
        self.id = veh_id
        self.communication_range = 50  # meters
        self.message_queue = deque(maxlen=50)
        self.last_communication = {}
    
    def get_position(self):
        """Get current position of the vehicle"""
        try:
            return traci.vehicle.getPosition(self.id)
        except:
            return None
    
    def get_speed(self):
        """Get current speed of the vehicle"""
        try:
            return traci.vehicle.getSpeed(self.id)
        except:
            return 0
    
    def get_neighbors(self, all_vehicles):
        """Find other vehicles within communication range"""
        neighbors = []
        pos = self.get_position()
        if pos is None:
            return neighbors
            
        for veh_id, vehicle in all_vehicles.items():
            if veh_id == self.id:
                continue
                
            other_pos = vehicle.get_position()
            if other_pos is None:
                continue
                
            distance = ((pos[0]-other_pos[0])**2 + (pos[1]-other_pos[1])**2)**0.5
            if distance <= self.communication_range:
                neighbors.append((veh_id, distance))
                
        return neighbors
    
    def send_message(self, message, target_vehicles):
        """Send a message to target vehicles"""
        for veh_id in target_vehicles:
            self.message_queue.append((time.time(), f"To {veh_id}: {message}"))
    
    def receive_messages(self):
        """Check for new messages"""
        return list(self.message_queue)

def create_rsus():
    """Create RSUs along roads at 200m intervals"""
    rsus = []
    rsu_id = 1
    
    # Get all edges from the network
    net_file = os.path.abspath('net_clean_final.net.xml')
    print(f"Reading network from: {net_file}")
    try:
        net = sumolib.net.readNet(net_file)
        print(f"Successfully loaded network with {len(net.getNodes())} nodes and {len(net.getEdges())} edges")
    except Exception as e:
        print(f"Error loading network file: {e}")
        # Try alternative network files
        for alt_net in ['net.net.xml', 'net_clean.net.xml', 'net_with_tls.net.xml', 'test_net.net.xml']:
            try:
                alt_path = os.path.abspath(alt_net)
                print(f"Trying alternative network file: {alt_path}")
                net = sumolib.net.readNet(alt_path)
                print(f"Successfully loaded alternative network: {alt_net}")
                break
            except Exception as alt_e:
                print(f"Failed to load {alt_net}: {alt_e}")
        else:
            raise RuntimeError("Could not load any network file. Please check if the .net.xml files exist.")
    
    
    # Add RSUs along edges at 200m intervals
    for edge in net.getEdges():
        edge_length = edge.getLength()
        if edge_length < 50:  # Skip very short edges
            continue
            
        # Calculate number of RSUs to place along this edge (at least 1)
        num_rsus = max(1, int(edge_length / 200))
        interval = edge_length / (num_rsus + 1)
        
        for i in range(1, num_rsus + 1):
            pos = i * interval
            # Create the RSU object without coordinates for now
            rsu = RSU(rsu_id, edge.getID(), pos, range=100)
            rsus.append(rsu)
            rsu_id += 1
    
    print(f"Created {len(rsus)} RSUs along the roads")
    return rsus

def adjust_traffic_lights(rsus, vehicles):
    """Adjust traffic lights based on RSU vehicle counts"""
    # Update vehicle positions
    vehicle_positions = {}
    for veh_id in traci.vehicle.getIDList():
        try:
            pos = traci.vehicle.getPosition(veh_id)
            if veh_id not in vehicles:
                vehicles[veh_id] = Vehicle(veh_id)
            vehicle_positions[veh_id] = pos
        except:
            continue
    
    # Update RSU vehicle counts
    for rsu in rsus:
        rsu.update_vehicle_count(vehicle_positions)
    
    # Group RSUs by their nearest traffic light
    tls_rsu_groups = defaultdict(list)
    for rsu in rsus:
        try:
            # Find nearest traffic light to this RSU
            min_dist = float('inf')
            nearest_tls = None
            
            for tls_id in traci.trafficlight.getIDList():
                tls_pos = traci.junction.getPosition(tls_id)
                dist = ((rsu.position[0]-tls_pos[0])**2 + (rsu.position[1]-tls_pos[1])**2)**0.5
                if dist < min_dist and dist < 100:  # Only consider TLS within 100m
                    min_dist = dist
                    nearest_tls = tls_id
            
            if nearest_tls is not None:
                tls_rsu_groups[nearest_tls].append(rsu)
        except Exception as e:
            print(f"Error finding nearest TLS for RSU {rsu.id}: {e}")
    
    # Adjust each traffic light based on nearby RSU data
    for tls_id, nearby_rsus in tls_rsu_groups.items():
        try:
            if not nearby_rsus:
                continue
                
            # Calculate average vehicle count from nearby RSUs
            total_vehicles = sum(rsu.edge_vehicle_count.get(rsu.edge_id, 0) for rsu in nearby_rsus)
            avg_vehicles = total_vehicles / len(nearby_rsus)
            
            # Get current phase and timing
            current_phase = traci.trafficlight.getPhase(tls_id)
            time_in_phase = traci.trafficlight.getPhaseDuration(tls_id) - traci.trafficlight.getNextSwitch(tls_id)
            
            # Adjust timing based on vehicle density
            if avg_vehicles > 5:  # Heavy traffic
                new_duration = max(10, time_in_phase + 2)  # Extend green time
                traci.trafficlight.setPhaseDuration(tls_id, new_duration)
                
            elif avg_vehicles > 2:  # Medium traffic
                # Keep default timing
                pass
                
            else:  # Light traffic
                new_duration = max(5, time_in_phase - 1)  # Reduce green time
                traci.trafficlight.setPhaseDuration(tls_id, new_duration)
                
            # Log the adjustment
            print(f"TLS {tls_id}: Avg vehicles={avg_vehicles:.1f}, Phase={current_phase}, "
                  f"Time in phase={time_in_phase:.1f}s")
                
        except Exception as e:
            print(f"Error adjusting traffic light {tls_id}: {e}")

def add_rsus_to_simulation(rsus):
    """Add RSUs to the simulation as POIs with detectors"""
    for rsu in rsus:
        try:
            # Get the first lane of the edge to place the RSU
            lane_id = traci.edge.getLaneID(rsu.edge_id, 0)
            
            # Use a temporary vehicle to find the precise (x, y) coordinates
            temp_veh_id = f"temp_veh_for_rsu_{rsu.id}"
            traci.route.add(f"route_for_{temp_veh_id}", [rsu.edge_id])
            traci.vehicle.add(temp_veh_id, f"route_for_{temp_veh_id}", departLane=0, departPos=rsu.lane_pos)
            x, y = traci.vehicle.getPosition(temp_veh_id)
            traci.vehicle.remove(temp_veh_id)
            
            # Update the RSU object with its final position
            rsu.position = (x, y)
            
            # Add the RSU as a POI at the correct position
            traci.poi.add(rsu.poi_id, x, y, color=(255, 0, 0), poiType="rsu")
            
            # Add a range indicator (yellow circle)
            traci.polygon.add(rsu.range_polygon, 
                            [(x-rsu.range, y-rsu.range), 
                             (x-rsu.range, y+rsu.range),
                             (x+rsu.range, y+rsu.range),
                             (x+rsu.range, y-rsu.range)],
                            color=(255, 255, 0, 50), fill=True, layer=1)
            
            # Add a detector for this RSU
            try:
                # Find the closest lane to this RSU's position
                lane_id = traci.simulation.convertRoad(x, y, isGeo=False, vClass="passenger")
                if lane_id and lane_id[0]:
                    # Add detector 10m from the start of the lane
                    traci.lanearea.add(rsu.detector_id, lane_id[0], pos=10, length=5)
                    print(f"Added detector {rsu.detector_id} for RSU {rsu.id} on lane {lane_id[0]}")
            except Exception as e:
                print(f"Error adding detector for RSU {rsu.id}: {e}")
                
        except Exception as e:
            print(f"Error adding RSU {rsu.id}: {e}")

def run_simulation():
    """Main simulation loop"""
    try:
        # Set SUMO_HOME if not already set
        if 'SUMO_HOME' not in os.environ:
            os.environ['SUMO_HOME'] = '/usr/share/sumo'
        
        # SUMO command with optimized parameters
        sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
        config_file = os.path.abspath('test_config.sumocfg')
        
        # Simplified SUMO command with logging enabled
        sumo_cmd = [
            sumo_binary,
            "-c", config_file,
            "--start",
            "--quit-on-end",
            "--log-file", "sumo.log",
            "--verbose"
        ]
        
        print("Starting SUMO with command:", " ".join(sumo_cmd))
        
        # Start TraCI connection
        traci.start(sumo_cmd)
        
        # Set up visualization if using GUI
        if "--gui" in sys.argv:
            try:
                view_ids = traci.gui.getIDList()
                if view_ids:
                    traci.gui.setSchema(view_ids[0], "real world")
                    traci.gui.setZoom(view_ids[0], 2000)  # Zoom out to see more of the network
            except Exception as e:
                print(f"Warning: Could not set up GUI view: {e}")
        
        # Create and add RSUs to the simulation
        rsus = create_rsus()
        add_rsus_to_simulation(rsus)
        vehicles = {}
        print(f"Created {len(rsus)} RSUs")

        # Main simulation loop
        step = 0
        max_steps = 3600  # About 30 minutes of simulated time
        
        while traci.simulation.getMinExpectedNumber() > 0 and step < max_steps:
            traci.simulationStep()
            step += 1
            
            # Adjust traffic lights and handle V2V communication every second
            if step % 2 == 0:  # Adjust this to change update frequency
                adjust_traffic_lights(rsus, vehicles)
                
            # Print progress
            if step % 100 == 0:
                print(f"Step {step}: {len(vehicles)} vehicles, {len(rsus)} RSUs active")
        
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
