import os
import sys
import traci
import socket
import time

# SUMO setup
if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")
tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
sys.path.append(tools)

# CONFIG: Set the RSU position and range
RSU_POSITION = (500, 500)  # example coordinates
RSU_RANGE = 100            # meters

# CONFIG: Server address
SERVER_IP = "127.0.0.1"
SERVER_PORT = 9999

def vehicles_in_range(rsu_pos, rsu_range):
    """Return IDs of vehicles within RSU's range."""
    vehicle_ids = traci.vehicle.getIDList()
    vehicles_nearby = []
    for vid in vehicle_ids:
        pos = traci.vehicle.getPosition(vid)
        dist = ((pos[0] - rsu_pos[0])**2 + (pos[1] - rsu_pos[1])**2)**0.5
        if dist <= rsu_range:
            vehicles_nearby.append(vid)
    return vehicles_nearby

def run():
    # SUMO launch
    sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "config/simulation.sumocfg"]
    traci.start(sumo_cmd)

    # Open socket to server
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        vehicles = vehicles_in_range(RSU_POSITION, RSU_RANGE)
        msg = f"RSU at {RSU_POSITION} sees {len(vehicles)} vehicles: {vehicles}"
        s.sendto(msg.encode(), (SERVER_IP, SERVER_PORT))
        time.sleep(0.2)  # Avoid flooding

    traci.close()
    s.close()

if __name__ == "__main__":
    run()