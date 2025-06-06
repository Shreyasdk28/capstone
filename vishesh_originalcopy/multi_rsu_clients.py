import os
import sys
import traci
import socket
import time
import random

if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")
tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
sys.path.append(tools)

RSU_RANGE = 100  # meters
SERVER_IP = "127.0.0.1"
SERVER_PORT = 9999

# Example: randomly select some vehicles as ambulances at the start
AMBULANCE_PROB = 0.1  # 10% vehicles are ambulances
AMBULANCE_URGENCY = "HIGH"

def get_signal_positions():
    signal_positions = {}
    traffic_light_ids = traci.trafficlight.getIDList()
    for tl_id in traffic_light_ids:
        controlled_lanes = traci.trafficlight.getControlledLanes(tl_id)
        if controlled_lanes:
            lane_id = controlled_lanes[0]
            pos = traci.lane.getShape(lane_id)[0]
            signal_positions[tl_id] = pos
    return signal_positions

def assign_ambulances():
    vehicle_ids = traci.vehicle.getIDList()
    ambulance_ids = []
    for vid in vehicle_ids:
        if random.random() < AMBULANCE_PROB:
            amb_id = f"AMB_{vid}"
            traci.vehicle.setType(vid, "ambulance")  # if type exists in your SUMO config
            traci.vehicle.setColor(vid, (255, 0, 0))  # Mark ambulance red
            ambulance_ids.append(vid)
    return set(ambulance_ids)

def vehicles_in_rsu_range(rsu_pos, rsu_range, ambulance_ids):
    vehicle_ids = traci.vehicle.getIDList()
    count = 0
    ambulance_in_range = None
    ambulance_lane = None
    for vid in vehicle_ids:
        pos = traci.vehicle.getPosition(vid)
        dist = ((pos[0] - rsu_pos[0]) ** 2 + (pos[1] - rsu_pos[1]) ** 2) ** 0.5
        if dist <= rsu_range:
            count += 1
            if vid in ambulance_ids:
                ambulance_in_range = vid
                ambulance_lane = traci.vehicle.getLaneID(vid)
    return count, ambulance_in_range, ambulance_lane

def run():
    sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "config/simulation.sumocfg"]
    traci.start(sumo_cmd)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    signal_positions = get_signal_positions()
    ambulance_ids = set()
    assigned = False

    print(f"Discovered signals (RSUs): {signal_positions}")

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        if not assigned:
            ambulance_ids = assign_ambulances()
            assigned = True

        for tl_id, rsu_pos in signal_positions.items():
            count, ambulance, ambulance_lane = vehicles_in_rsu_range(rsu_pos, RSU_RANGE, ambulance_ids)
            msg = {
                "signal_id": tl_id,
                "vehicle_count": count,
                "ambulance": False
            }
            if ambulance:
                msg["ambulance"] = True
                msg["urgency"] = AMBULANCE_URGENCY
                msg["ambulance_lane"] = ambulance_lane
                # Simulate V2V: ambulance broadcasts dummy message
                print(f"AMBULANCE {ambulance} V2V: 'Urgency={AMBULANCE_URGENCY}', approaching lane {ambulance_lane}")
            s.sendto(str(msg).encode(), (SERVER_IP, SERVER_PORT))
        time.sleep(0.2)

    traci.close()
    s.close()

if __name__ == "__main__":
    run()