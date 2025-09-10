import os
import sys
import traci
import random
import time
import threading
import xml.etree.ElementTree as ET

# Add SUMO tools to Python path
if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# Import SUMO tools
tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
sys.path.append(tools)

class RSU:
    def __init__(self, rsu_id, position, range=150):
        self.id = rsu_id
        self.position = position
        self.range = range
        self.connected_vehicles = set()
        self.vehicle_data = {}

    def in_range(self, vehicle_pos):
        return ((self.position[0] - vehicle_pos[0])**2 + 
                (self.position[1] - vehicle_pos[1])**2) <= (self.range**2)

    def process_data(self):
        """Analyzes vehicle data to detect congestion and returns an alert if needed."""
        if not self.connected_vehicles:
            return None
        
        speeds = [data['speed'] for veh_id, data in self.vehicle_data.items() if veh_id in self.connected_vehicles]
        if not speeds:
            return None

        avg_speed = sum(speeds) / len(speeds)
        if avg_speed < 10:  # Congestion threshold: average speed less than 10 m/s
            print(f"RSU {self.id}: Congestion detected! Average speed: {avg_speed:.2f} m/s")
            return "congestion_warning"
        return "all_clear"

    def receive_message(self, message, vehicle_id):
        self.vehicle_data[vehicle_id] = {
            'speed': message['speed'],
            'position': message['position'],
            'time': message['time']
        }
        # print(f"RSU {self.id} received from {vehicle_id}: speed {message['speed']:.2f} m/s")
        return self.process_data()

def run_simulation():
    # Start SUMO with GUI
    sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "config/simulation_rsu.sumocfg"]
    
    # Start TraCI connection
    traci.start(sumo_cmd)
    
    rsus = load_rsus_from_xml("config/rsu.add.xml")
    if not rsus:
        print("Warning: No RSUs loaded. Check rsu.add.xml file.")
    
    # Dictionary to store vehicle messages
    vehicle_messages = {}
    
    # Simulation loop
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        current_time = traci.simulation.getTime()
        
        # Get all vehicle IDs
        vehicle_ids = traci.vehicle.getIDList()
        
        # For each vehicle
        for veh_id in vehicle_ids:
            # Get vehicle position and speed
            pos = traci.vehicle.getPosition(veh_id)
            speed = traci.vehicle.getSpeed(veh_id)
            
            # Check if vehicle is in range of any RSU
            for rsu in rsus:
                if rsu.in_range(pos):
                    if veh_id not in rsu.connected_vehicles:
                        rsu.connected_vehicles.add(veh_id)
                        print(f"{veh_id} connected to {rsu.id}")
                    
                    # Send periodic updates to RSU (every 5 seconds)
                    if int(current_time) % 5 == 0:
                        message = {
                            'type': 'status',
                            'vehicle_id': veh_id,
                            'position': pos,
                            'speed': speed,
                            'time': current_time
                        }
                        response = rsu.receive_message(message, veh_id)
                        
                        if response == "congestion_warning":
                            traci.vehicle.slowDown(veh_id, max(5, speed * 0.7), 3) # Slow down
                            traci.vehicle.setColor(veh_id, (255, 255, 0))  # Yellow for congestion
                        else:
                            traci.vehicle.setColor(veh_id, (0, 255, 0))  # Green for normal RSU comms
                else:
                    if veh_id in rsu.connected_vehicles:
                        rsu.connected_vehicles.remove(veh_id)
                        if veh_id in rsu.vehicle_data:
                            del rsu.vehicle_data[veh_id]
                        print(f"{veh_id} disconnected from {rsu.id}")
                        traci.vehicle.setColor(veh_id, (255, 255, 255)) # Reset color on disconnect
            
            # V2V Communication (10% chance per vehicle per second)
            if random.random() < 0.1 and veh_id in traci.vehicle.getIDList():
                try:
                    message = {
                        'type': 'v2v',
                        'from': veh_id,
                        'position': pos,
                        'speed': speed,
                        'time': current_time,
                        'data': f"Message from {veh_id} at {current_time:.1f}s"
                    }
                    
                    # Find nearby vehicles (within 50 meters)
                    current_vehicles = traci.vehicle.getIDList()
                    for other_veh in current_vehicles:
                        if other_veh != veh_id:
                            try:
                                other_pos = traci.vehicle.getPosition(other_veh)
                                distance = ((pos[0] - other_pos[0])**2 + (pos[1] - other_pos[1])**2)**0.5
                                
                                if distance < 50:  # If within 50 meters
                                    print(f"V2V: {veh_id} -> {other_veh}: {message['data']}")
                                    
                                    # Visual feedback for V2V communication
                                    if veh_id in current_vehicles:
                                        traci.vehicle.setColor(veh_id, (0, 0, 255))    # Blue for V2V
                                    if other_veh in current_vehicles:
                                        traci.vehicle.setColor(other_veh, (0, 0, 255))  # Blue for V2V
                                    
                                    # Reset color after a short delay
                                    threading.Timer(1.0, lambda v=veh_id: reset_vehicle_color(v)).start()
                                    threading.Timer(1.0, lambda v=other_veh: reset_vehicle_color(v)).start()
                            except traci.TraCIException:
                                continue  # Skip if vehicle no longer exists
                except traci.TraCIException:
                    pass  # Skip if vehicle no longer exists
        
        # Clear old messages
        vehicle_messages = {k: v for k, v in vehicle_messages.items() if k in vehicle_ids}
        
        # Small delay to prevent high CPU usage
        time.sleep(0.01)
    
    traci.close()

def load_rsus_from_xml(filepath):
    rsus = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        for poi in root.findall('poi'):
            rsu_id = poi.get('id')
            x = float(poi.get('x'))
            y = float(poi.get('y'))
            # You can add a range attribute to your XML if you want
            rsus.append(RSU(rsu_id, (x, y)))
        print(f"Loaded {len(rsus)} RSUs from {filepath}")
    except (ET.ParseError, FileNotFoundError) as e:
        print(f"Error loading RSUs from {filepath}: {e}")
    return rsus

def reset_vehicle_color(veh_id):
    try:
        # Check if vehicle still exists in the simulation
        if veh_id in traci.vehicle.getIDList():
            # Check if vehicle is still connected to an RSU before resetting color
            # This prevents overriding RSU-related colors
            traci.vehicle.setColor(veh_id, (255, 255, 255))  # Back to white
    except traci.TraCIException:
        pass # Vehicle might have left simulation

if __name__ == "__main__":
    run_simulation() 