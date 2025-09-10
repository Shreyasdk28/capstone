#!/usr/bin/env python3
"""
Adaptive Traffic Control System with RSUs at Traffic Signals
"""
import os
import sys
import traci
import math
import xml.etree.ElementTree as ET
from collections import defaultdict

# Add SUMO tools to Python path
if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# Add SUMO tools to Python path
tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
sys.path.append(tools)

# Import SUMO tools
try:
    from sumolib import checkBinary
except ImportError:
    sys.exit("Could not find sumolib. Please check your SUMO installation.")

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
                    dist = math.sqrt((pos[0]-edge_pos[0])**2 + (pos[1]-edge_pos[1])**2)
                    if dist < min_dist:
                        min_dist = dist
                        closest_edge = edge
                if closest_edge is not None:
                    self.edge_vehicle_count[closest_edge] += 1
                    
    def get_edge_position(self, edge_id):
        """Get position of an edge (approximated as the middle point)"""
        try:
            lanes = traci.edge.getLaneNumber(edge_id)
            if lanes > 0:
                lane_id = f"{edge_id}_0"
                shape = traci.lane.getShape(lane_id)
                if shape:
                    # Return the middle point of the edge
                    return shape[len(shape)//2]
        except:
            pass
        return None
    
    def in_range(self, position):
        """Check if a position is within this RSU's range"""
        dx = self.position[0] - position[0]
        dy = self.position[1] - position[1]
        return (dx*dx + dy*dy) <= (self.range * self.range)

def get_traffic_light_nodes():
    """Extract traffic light nodes and their controlled edges from the network"""
    try:
        tree = ET.parse('net_clean_final.net.xml')
        root = tree.getroot()
        
        tl_nodes = {}
        
        # First pass: find all traffic light nodes
        for tl in root.findall('.//tlLogic'):
            tl_id = tl.get('id')
            tl_nodes[tl_id] = {
                'position': None,
                'edges': set()
            }
        
        # If no traffic lights found, return empty
        if not tl_nodes:
            print("No traffic lights found in network file.")
            return {}
        
        # Second pass: find node positions
        for node in root.findall('.//node'):
            node_id = node.get('id')
            if node_id in tl_nodes:
                x = float(node.get('x'))
                y = float(node.get('y'))
                tl_nodes[node_id]['position'] = (x, y)
        
        # Third pass: find edges controlled by each traffic light
        for connection in root.findall('.//connection'):
            tl = connection.get('tl')
            if tl and tl in tl_nodes:
                from_edge = connection.get('from')
                to_edge = connection.get('to')
                if from_edge:
                    tl_nodes[tl]['edges'].add(from_edge)
                if to_edge:
                    tl_nodes[tl]['edges'].add(to_edge)
        
        return tl_nodes
        
    except Exception as e:
        print(f"Error processing traffic light nodes: {e}")
        return {}

def create_rsus_at_signals():
    """Create RSUs at traffic light locations and along roads"""
    rsus = []
    
    # Try to get traffic light nodes first
    tl_nodes = get_traffic_light_nodes()
    
    # Create RSUs at traffic lights
    for i, (tl_id, data) in enumerate(tl_nodes.items(), 1):
        if data['position'] and data['edges']:
            rsu_id = f"rsu_tl_{i}"
            rsus.append(RSU(rsu_id, data['position'], list(data['edges'])))
    
    # If no traffic lights found, create RSUs along major roads
    if not rsus:
        print("No traffic lights found. Creating RSUs along roads...")
        try:
            # Get all edges in the network
            edges = traci.edge.getIDList()
            
            # Sample some edges for RSU placement (every 100m)
            for i, edge_id in enumerate(edges[:10]):  # Limit to first 10 edges for demo
                try:
                    # Get edge shape (list of points)
                    lanes = traci.edge.getLaneNumber(edge_id)
                    if lanes > 0:
                        lane_id = f"{edge_id}_0"
                        shape = traci.lane.getShape(lane_id)
                        if shape:
                            # Place RSU at the middle of the edge
                            mid_point = shape[len(shape)//2]
                            rsus.append(RSU(f"rsu_{i}", mid_point, [edge_id], 150))
                except:
                    continue
        except:
            print("Could not create RSUs along roads. Using default positions.")
            # Add default RSUs if automatic placement fails
            rsus.extend([
                RSU("rsu1", (1000, 500), ["edge1", "edge2"], 150),
                RSU("rsu2", (1500, 500), ["edge3", "edge4"], 150)
            ])
    
    return rsus

def adjust_traffic_lights(rsus):
    """Adjust traffic light phases based on vehicle density"""
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
            
            # Only proceed if we have traffic light data
            if hasattr(rsu, 'tl_id'):
                tl_id = rsu.tl_id
            else:
                # Try to find a traffic light ID from the edges
                for edge_id in rsu.edges:
                    try:
                        # Get the junction this edge leads to
                        to_node = traci.edge.getToNode(edge_id)
                        tl_id = f"{to_node}"
                        rsu.tl_id = tl_id
                        break
                    except:
                        continue
                else:
                    continue  # Skip if no traffic light found
            
            try:
                # Get current state and program
                current_state = traci.trafficlight.getRedYellowGreenState(tl_id)
                current_phase = traci.trafficlight.getPhase(tl_id)
                program = traci.trafficlight.getAllProgramLogics(tl_id)
                
                if not program:
                    continue
                    
                # Simple adaptive logic: extend green for direction with more vehicles
                if rsu.edge_vehicle_count:
                    max_edge = max(rsu.edge_vehicle_count.items(), key=lambda x: x[1])
                    if max_edge[1] > 3:  # Minimum threshold
                        # Find the phase that serves this edge
                        for phase_idx, phase in enumerate(program[0].phases):
                            # This is a simplified example - you'd need to map edges to phases
                            if 'g' in phase.state.lower():
                                # Extend green time for this phase
                                traci.trafficlight.setPhaseDuration(tl_id, 10)  # Extend by 10 seconds
                                break
                
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
                print(f"Error adjusting traffic light {rsu.id}: {str(e)}")
                continue

def run_simulation():
    """Main simulation loop"""
    try:
        # Start SUMO with GUI
        sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
        sumo_cmd = [
            sumo_binary,
            "-c", "config/adaptive_traffic.sumocfg",
            "--start",  # Start the simulation after loading
            "--quit-on-end",  # Quit when simulation ends
            "--gui-settings-file", "viewsettings.xml"  # Use view settings if available
        ]
        
        print("Starting SUMO with command:", " ".join(sumo_cmd))
        
        # Start TraCI connection
        traci.start(sumo_cmd)
        
        # Enable traffic light visualization
        traci.gui.setSchema("View #0", "real world")
        
        # Create RSUs at traffic signals
        rsus = create_rsus_at_signals()
        
        # If no RSUs were created, create some at fixed positions as fallback
        if not rsus:
            print("No traffic lights found. Creating RSUs at fixed positions...")
            rsus = [
                RSU("rsu1", (1000, 500), ["edge1", "edge2"], 150),
                RSU("rsu2", (1500, 500), ["edge3", "edge4"], 150)
            ]
        
        print(f"Created {len(rsus)} RSUs at traffic signals")
        
        # Add RSUs to visualization
        for i, rsu in enumerate(rsus):
            traci.poi.add(f"rsu_{i}", rsu.position[0], rsu.position[1], (255, 0, 0, 255), 5, "RSU")
        
        # Main simulation loop
        step = 0
        while traci.simulation.getMinExpectedNumber() > 0 and step < 1000:  # Limit to 1000 steps for testing
            traci.simulationStep()
            step += 1
            
            # Adjust traffic lights every 10 seconds
            if step % 100 == 0:
                adjust_traffic_lights(rsus)
                print(f"Step {step}: Adjusted traffic lights at {len(rsus)} locations")
        
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
