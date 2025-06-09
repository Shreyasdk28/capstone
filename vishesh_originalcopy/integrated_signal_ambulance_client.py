import os
import sys
import traci
import socket
import time
import random
import threading

if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")
tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
sys.path.append(tools)

SERVER_IP = "127.0.0.1"
SERVER_PORT = 9999
CLIENT_PORT = 9998

AMBULANCE_PROB = 0.1
AMBULANCE_URGENCY = "HIGH"

def get_signal_lanes():
    signal_lanes = {}
    for tl_id in traci.trafficlight.getIDList():
        lanes = [l for l in traci.trafficlight.getControlledLanes(tl_id) if not l.startswith(":")]
        if lanes:
            signal_lanes[tl_id] = lanes
    return signal_lanes

def assign_ambulances():
    ambulance_ids = set()
    for vid in traci.vehicle.getIDList():
        if random.random() < AMBULANCE_PROB:
            try:
                traci.vehicle.setType(vid, "ambulance")
            except Exception:
                pass
            traci.vehicle.setColor(vid, (255, 0, 0))
            ambulance_ids.add(vid)
    return ambulance_ids

def listen_for_commands(traci, running_flag):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', CLIENT_PORT))
    sock.settimeout(1.0)
    while running_flag[0]:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode()
            if msg.startswith("MAKE_GREEN"):
                _, signal_id, lane_id = msg.strip().split("|")
                make_lane_green(traci, signal_id, lane_id)
                print(f"\033[92m[SERVER] Signal {signal_id} set to GREEN for lane {lane_id}!\033[0m")
            elif msg.startswith("AMBULANCE_DETECTED"):
                _, signal_id, lane_id, urgency = msg.strip().split("|")
                print(f"\033[95m[SERVER] Ambulance detected at signal {signal_id}, lane {lane_id} | Urgency: {urgency}\033[0m")
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Command listener error: {e}")
    sock.close()

def make_lane_green(traci, signal_id, lane_id):
    try:
        links = traci.trafficlight.getControlledLinks(signal_id)
        green_states = list(traci.trafficlight.getRedYellowGreenState(signal_id))
        found = False
        for i, link_group in enumerate(links):
            for sub_link in link_group:
                if sub_link[0] == lane_id:
                    green_states[i] = 'G'
                    found = True
                else:
                    # Optional: set others to red for clarity
                    green_states[i] = 'r'
        if found:
            new_state = ''.join(green_states)
            traci.trafficlight.setRedYellowGreenState(signal_id, new_state)
    except Exception as e:
        print(f"Failed to set green for {signal_id} {lane_id}: {e}")

def density_based_green(traci, signal_id, lanes):
    # Find the lane with highest density (vehicle count)
    max_lane = None
    max_count = -1
    for lane in lanes:
        count = traci.lane.getLastStepVehicleNumber(lane)
        if count > max_count:
            max_count = count
            max_lane = lane
    if max_lane:
        make_lane_green(traci, signal_id, max_lane)
        print(f"\033[96m[DENSITY] Signal {signal_id} set to GREEN for lane {max_lane} (density={max_count})\033[0m")

def run():
    sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "config/simulation.sumocfg"]
    traci.start(sumo_cmd)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    signal_lanes = get_signal_lanes()
    ambulance_ids = set()
    assigned = False

    running_flag = [True]
    listener_thread = threading.Thread(target=listen_for_commands, args=(traci, running_flag))
    listener_thread.daemon = True
    listener_thread.start()

    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            if not assigned:
                ambulance_ids = assign_ambulances()
                assigned = True

            for tl_id, lanes in signal_lanes.items():
                lane_counts = []
                ambulance_present = None
                for lane in lanes:
                    n = traci.lane.getLastStepVehicleNumber(lane)
                    ambulances_in_lane = [vid for vid in traci.lane.getLastStepVehicleIDs(lane) if vid in ambulance_ids]
                    if ambulances_in_lane:
                        ambulance_present = lane
                        for amb in ambulances_in_lane:
                            print(f"\033[93m[V2V] Ambulance {amb} broadcasting on lane {lane}\033[0m")
                            ambulance_report = {
                                "signal_id": tl_id,
                                "lane": lane,
                                "urgency": AMBULANCE_URGENCY,
                                "meta": "AMBULANCE_ALERT",
                                "client_port": CLIENT_PORT
                            }
                            s.sendto(str(ambulance_report).encode(), (SERVER_IP, SERVER_PORT))
                    lane_counts.append(f"{lane}:{n}")
                # Print the report as required
                print(f"signal {tl_id} total vehicles at the moment = {', '.join(lane_counts)}")
                # Ambulance priority: immediately give green to that lane
                if ambulance_present:
                    make_lane_green(traci, tl_id, ambulance_present)
                    print(f"\033[91m[AMBULANCE] PRIORITY GREEN at signal {tl_id} for lane {ambulance_present}\033[0m")
                else:
                    # Density-based: green for the lane with highest count
                    density_based_green(traci, tl_id, lanes)
            time.sleep(0.5)
    finally:
        running_flag[0] = False
        listener_thread.join(timeout=1.0)
        traci.close()
        s.close()

if __name__ == "__main__":
    run()