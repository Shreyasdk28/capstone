import os
import sys
import traci
import socket
import threading

if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")
tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
sys.path.append(tools)

SIGNAL_ID = "YOUR_SIGNAL_ID"  # Set this for each instance
SIGNAL_PORT = 10001           # Set this for each instance

def listen_for_commands(traci, running_flag):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', SIGNAL_PORT))
    sock.settimeout(1.0)
    print(f"Signal controller for {SIGNAL_ID} listening on port {SIGNAL_PORT}")
    while running_flag[0]:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode()
            if msg.startswith("AMBULANCE_DETECTED"):
                _, signal_id, lane, urgency = msg.strip().split("|")
                print(f"\033[93m[ALERT] Ambulance detected at signal {signal_id}, lane {lane}, Urgency: {urgency}\033[0m")
            elif msg.startswith("MAKE_GREEN"):
                _, signal_id, lane = msg.strip().split("|")
                make_lane_green(traci, signal_id, lane)
                print(f"\033[92m[SIGNAL] Signal {signal_id} set to GREEN for lane {lane}\033[0m")
        except socket.timeout:
            continue
        except Exception as e:
            print(f"Error in command listener: {e}")
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
        if found:
            new_state = ''.join(green_states)
            traci.trafficlight.setRedYellowGreenState(signal_id, new_state)
    except Exception as e:
        print(f"Failed to set green for {signal_id} {lane_id}: {e}")

def run():
    sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "config/simulation.sumocfg"]
    traci.start(sumo_cmd)

    running_flag = [True]
    listener_thread = threading.Thread(target=listen_for_commands, args=(traci, running_flag))
    listener_thread.daemon = True
    listener_thread.start()

    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            # Optional: Print lane vehicle counts here if desired
    finally:
        running_flag[0] = False
        listener_thread.join(timeout=1.0)
        traci.close()

if __name__ == "__main__":
    run()