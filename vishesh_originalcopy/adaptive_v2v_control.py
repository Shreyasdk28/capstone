#!/usr/bin/env python3
"""
Combined Adaptive Traffic Control and V2V Communication System
"""
import os
import sys
import traci
import random
import math
import time
from collections import defaultdict, deque

# Add SUMO tools to Python path
if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# Add SUMO tools to Python path
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
        self.messages = deque(maxlen=100)  # Store recent messages
    
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
    """Create RSUs at intersections and along roads at 200m intervals"""
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
    
    print(f"Creating RSUs for network: {net.getNetName()}")
    
    # 1. Add RSUs at intersections (nodes)
    for node in net.getNodes():
        x, y = node.getCoord()
        connected_edges = [e.getID() for e in node.getOutgoing() + node.getIncoming()]
        rsus.append(RSU(rsu_id, (x, y), connected_edges))
        rsu_id += 1
    
    # 2. Add RSUs along edges at 200m intervals
    for edge in net.getEdges():
        if edge.getLength() > 200:  # Only add RSUs to longer edges
            num_rsus = int(edge.getLength() / 200)
            if num_rsus > 0:
                for i in range(1, num_rsus + 1):
                    pos = (i * 200) / edge.getLength()  # Position along edge (0-1)
                    x, y = edge.getFromNode().getCoord()
                    x2, y2 = edge.getToNode().getCoord()
                    # Interpolate position
                    rsu_x = x + (x2 - x) * pos
                    rsu_y = y + (y2 - y) * pos
                    rsus.append(RSU(rsu_id, (rsu_x, rsu_y), [edge.getID()]))
                    rsu_id += 1
    
    print(f"Created {len(rsus)} RSUs in total")
    return rsus

def adjust_traffic_lights(rsus, vehicles):
    """Adjust traffic lights and handle V2V communication"""
    # Update vehicle positions and handle V2V communication
    vehicle_positions = {}
    vehicle_objects = {}
    
    # Get all vehicles and their positions
    for veh_id in traci.vehicle.getIDList():
        try:
            pos = traci.vehicle.getPosition(veh_id)
            if veh_id not in vehicles:
                vehicles[veh_id] = Vehicle(veh_id)
            vehicle_positions[veh_id] = pos
            vehicle_objects[veh_id] = vehicles[veh_id]
        except:
            continue
    
    # Update RSU vehicle counts
    for rsu in rsus:
        rsu.update_vehicle_count(vehicle_positions)
    
    # V2V Communication
    for veh_id, vehicle in vehicle_objects.items():
        neighbors = vehicle.get_neighbors(vehicle_objects)
        if neighbors:
            # Example: Send speed information to neighbors
            speed = vehicle.get_speed()
            if speed > 0:  # Only send if vehicle is moving
                neighbor_ids = [n[0] for n in neighbors]
                vehicle.send_message(f"Speed: {speed:.1f} m/s", neighbor_ids)
        
        # Process received messages
        messages = vehicle.receive_messages()
        if messages:
            # Example: React to messages (e.g., slow down if receiving warning)
            for msg_time, msg in messages:
                if "warning" in msg.lower():
                    # Slow down if warning received
                    traci.vehicle.slowDown(veh_id, max(0, vehicle.get_speed() * 0.8), 1)
    
    # First, group RSUs by their nearest traffic light
    tls_dict = {}
    for rsu in rsus:
        # Find nearest traffic light to this RSU
        min_dist = float('inf')
        nearest_tls = None
        
        for tls_id in traci.trafficlight.getIDList():
            tls_pos = traci.junction.getPosition(tls_id)
            dist = ((rsu.position[0] - tls_pos[0])**2 + (rsu.position[1] - tls_pos[1])**2)**0.5
            if dist < min_dist and dist < 100:  # Only consider RSUs within 100m of a traffic light
                min_dist = dist
                nearest_tls = tls_id
        
        if nearest_tls:
            if nearest_tls not in tls_dict:
                tls_dict[nearest_tls] = []
            tls_dict[nearest_tls].append(rsu)
    
    # Adjust traffic lights based on RSU data
    for tls_id, tls_rsus in tls_dict.items():
        try:
            # Calculate average vehicle density for this traffic light's RSUs
            total_vehicles = 0
            total_rsus = len(tls_rsus)
            
            for rsu in tls_rsus:
                # Update RSU color based on its own vehicle count
                rsu_vehicles = sum(rsu.edge_vehicle_count.values())
                total_vehicles += rsu_vehicles
                
                # Update RSU visualization
                if hasattr(rsu, 'veh_id'):
                    if rsu_vehicles > 5:
                        traci.vehicle.setColor(rsu.veh_id, (255, 0, 0, 255))  # Red
                    elif rsu_vehicles > 2:
                        traci.vehicle.setColor(rsu.veh_id, (255, 255, 0, 255))  # Yellow
                    else:
                        traci.vehicle.setColor(rsu.veh_id, (0, 255, 0, 255))  # Green
            
            # Calculate average vehicle density per RSU
            avg_vehicles = total_vehicles / max(1, total_rsus)
            
            # Adjust traffic light timing based on density
            if avg_vehicles > 5:  # Heavy traffic
                traci.trafficlight.setPhaseDuration(tls_id, max(5, traci.trafficlight.getNextSwitch(tls_id) - 1))
            elif avg_vehicles > 2:  # Medium traffic
                traci.trafficlight.setPhaseDuration(tls_id, 10)  # Default timing
            else:  # Light traffic
                traci.trafficlight.setPhaseDuration(tls_id, min(30, traci.trafficlight.getNextSwitch(tls_id) + 1))
                
        except Exception as e:
            print(f"Error adjusting traffic light {tls_id}: {e}")

def run_simulation():
    """Main simulation loop"""
    try:
        # Set SUMO_HOME if not already set
        if 'SUMO_HOME' not in os.environ:
            os.environ['SUMO_HOME'] = '/usr/share/sumo'
        
        # Basic SUMO command
        sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
        config_file = os.path.abspath('test_config.sumocfg')
        
        # Simple command without extra parameters that might cause issues
        sumo_cmd = [sumo_binary, "-c", config_file]
        
        print("Starting SUMO with command:", " ".join(sumo_cmd))
        
        # Add a small delay to ensure SUMO is fully started
        time.sleep(2)
        
        # Start TraCI connection
        traci.start(sumo_cmd)
        
        # Set up visualization
        traci.gui.setSchema("View #0", "real world")
        
        # Create RSUs
        rsus = create_rsus()
        vehicles = {}
        print(f"Created {len(rsus)} RSUs")
        
        # Add RSUs as special vehicles for visualization
        for rsu in rsus:
            try:
                veh_id = f"rsu_{rsu.id}"
                x, y = rsu.position
                # Add a special vehicle to represent the RSU
                # Using 'rsu_vehicle' type defined in rsu.add.xml
                try:
                    traci.vehicle.add(
                        veh_id, 
                        "",  # route ID (empty for teleport)
                        typeID="rsu_vehicle",
                        depart=0,
                        departPos=0,
                        departSpeed=0,
                        departLane=0
                    )
                    traci.vehicle.moveToXY(veh_id, "", 0, x, y, keepRoute=2)
                    traci.vehicle.setColor(veh_id, (0, 255, 0, 255))  # Green
                    traci.vehicle.setSpeed(veh_id, 0)  # Stationary
                    traci.vehicle.setWidth(veh_id, 3)  # Make RSUs more visible
                    traci.vehicle.setLength(veh_id, 3)
                    traci.vehicle.setLine(veh_id, f"RSU-{rsu.id}")  # Show RSU ID as label
                    rsu.veh_id = veh_id
                    print(f"Added RSU {rsu.id} as vehicle {veh_id} at position {x},{y}")
                except Exception as e:
                    print(f"Error adding RSU vehicle {rsu.id}: {e}")
                    # Fallback to POI if vehicle creation fails
                    try:
                        traci.poi.add(f"rsu_{rsu.id}", x, y, (0, 255, 0, 255), 0, "rsu", 5, 5)
                        print(f"Added RSU {rsu.id} as POI at position {x},{y}")
                    except Exception as e2:
                        print(f"Failed to add RSU {rsu.id} as POI: {e2}")
            except Exception as e:
                print(f"Error adding RSU {rsu.id}: {e}")
        
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
