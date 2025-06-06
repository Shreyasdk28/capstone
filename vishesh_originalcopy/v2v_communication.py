import os
import sys
import traci
import random
import time

# Add SUMO tools to Python path
if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# Import SUMO tools
tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
sys.path.append(tools)

def run_simulation():
    # Start SUMO with GUI
    sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "config/simulation.sumocfg"]
    
    # Start TraCI connection
    traci.start(sumo_cmd)
    
    # Dictionary to store vehicle messages
    vehicle_messages = {}
    
    # Simulation loop
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        
        # Get all vehicle IDs
        vehicle_ids = traci.vehicle.getIDList()
        
        # For each vehicle
        for veh_id in vehicle_ids:
            # Get vehicle position
            pos = traci.vehicle.getPosition(veh_id)
            
            # Randomly decide if vehicle should send a message (10% chance)
            if random.random() < 0.1:
                # Create a random message
                message = f"Vehicle {veh_id} sending message: {random.randint(1, 100)}"
                vehicle_messages[veh_id] = message
                
                # Find nearby vehicles (within 50 meters)
                for other_veh in vehicle_ids:
                    if other_veh != veh_id:
                        other_pos = traci.vehicle.getPosition(other_veh)
                        distance = ((pos[0] - other_pos[0])**2 + (pos[1] - other_pos[1])**2)**0.5
                        
                        if distance < 50:  # If within 50 meters
                            print(f"Message from {veh_id} to {other_veh}: {message}")
                            
                            # Add visual indicator in SUMO
                            traci.vehicle.setColor(other_veh, (255, 0, 0))  # Red color
                            time.sleep(0.1)  # Brief pause to make it visible
                            traci.vehicle.setColor(other_veh, (255, 255, 255))  # Back to white
        
        # Clear old messages
        vehicle_messages = {k: v for k, v in vehicle_messages.items() if k in vehicle_ids}
    
    traci.close()

if __name__ == "__main__":
    run_simulation() 