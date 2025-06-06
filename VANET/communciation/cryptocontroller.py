import traci
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import os
import hashlib
import math

# SUMO start
sumoCmd = ["sumo-gui", "-c", "simple.sumocfg"]
traci.start(sumoCmd)

COMM_COLOR = (0, 255, 0, 255)
DEFAULT_COLOR = (255, 0, 0, 255)

RSU_IDS = ["rsu_intersection", "rsu_main"]
TLS_ID = "n1"
GREEN_STATE = "G"
RED_STATE = "r"

def calculate_distance(veh1_id, veh2_id):
    pos1 = traci.vehicle.getPosition(veh1_id)
    pos2 = traci.vehicle.getPosition(veh2_id)
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

def get_stopped_vehicles_near_tls():
    stopped_vehicles = set()
    for rsu_id in RSU_IDS:
        try:
            veh_ids = traci.inductionloop.getLastStepVehicleIDs(rsu_id)
            for vid in veh_ids:
                if traci.vehicle.getSpeed(vid) < 0.1:
                    stopped_vehicles.add(vid)
        except Exception:
            continue
    return list(stopped_vehicles)

def is_emergency_vehicle(veh_id):
    try:
        return 'emergency' in traci.vehicle.getTypeID(veh_id).lower() or 'emergency' in veh_id.lower()
    except Exception:
        return False

vehicle_shared_keys = {}
def get_shared_secret(sender, receiver):
    ids = "_".join(sorted([sender, receiver]))
    return hashlib.sha256(ids.encode()).digest()
def pqc_handshake(sender, receiver):
    shared_secret = get_shared_secret(sender, receiver)
    vehicle_shared_keys[(sender, receiver)] = shared_secret
    vehicle_shared_keys[(receiver, sender)] = shared_secret
def send_secure_message(sender, receiver, message):
    if (sender, receiver) not in vehicle_shared_keys:
        pqc_handshake(sender, receiver)
    key = vehicle_shared_keys[(sender, receiver)]
    cipher = ChaCha20Poly1305(key)
    nonce = os.urandom(12)
    ad = b"VANET_MESSAGE"
    ct = cipher.encrypt(nonce, message.encode(), ad)
    return nonce + ct
def receive_secure_message(receiver, sender, encrypted_msg):
    key = vehicle_shared_keys[(receiver, sender)]
    nonce = encrypted_msg[:12]
    ct = encrypted_msg[12:]
    ad = b"VANET_MESSAGE"
    cipher = ChaCha20Poly1305(key)
    try:
        pt = cipher.decrypt(nonce, ct, ad)
        return pt.decode()
    except Exception:
        return None

step = 0
already_communicated = set()
traffic_light_green = False
green_duration = 20
red_duration = 20
phase_timer = 0

# For RSU: track which vehicles have been detected and when
rsu_detection_log = {}

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()

    for veh_id in traci.vehicle.getIDList():
        traci.vehicle.setColor(veh_id, DEFAULT_COLOR)

    # RSU: Only print the first detection time for each vehicle at each RSU
    for rsu_id in RSU_IDS:
        try:
            vehicles_at_rsu = traci.inductionloop.getLastStepVehicleIDs(rsu_id)
            for veh_id in vehicles_at_rsu:
                if (rsu_id, veh_id) not in rsu_detection_log:
                    print(f"[{step}] RSU {rsu_id}: Detected {veh_id}")
                    rsu_detection_log[(rsu_id, veh_id)] = step
        except Exception:
            pass

    stopped_vehicles = get_stopped_vehicles_near_tls()
    num_stopped = len(stopped_vehicles)
    if num_stopped > 3:
        traffic_light_green = True
        phase_timer = 0

    num_signals = len(traci.trafficlight.getRedYellowGreenState(TLS_ID))
    if traffic_light_green:
        traci.trafficlight.setRedYellowGreenState(TLS_ID, GREEN_STATE * num_signals)
        phase_timer += 1
        if phase_timer >= green_duration:
            traffic_light_green = False
            phase_timer = 0
    else:
        traci.trafficlight.setRedYellowGreenState(TLS_ID, RED_STATE * num_signals)
        phase_timer += 1
        if phase_timer >= red_duration:
            traffic_light_green = True
            phase_timer = 0

    # V2V: front vehicle → all behind at red (new varied messages)
    if not traffic_light_green and num_stopped >= 2:
        positions = [(vid, traci.vehicle.getLanePosition(vid)) for vid in stopped_vehicles]
        positions.sort(key=lambda x: -x[1])
        front_vehicle = positions[0][0]
        behind_vehicles = [vid for vid, _ in positions[1:]]
        v2v_msgs = [
            "Signal is RED, please wait.",
            "I'm stopped at the intersection.",
            "Caution! Approaching red light.",
            "Queue is forming ahead.",
            "Traffic is heavy at the signal."
        ]
        for idx, behind_vehicle in enumerate(behind_vehicles):
            pair = (front_vehicle, behind_vehicle)
            if pair not in already_communicated:
                msg = v2v_msgs[idx % len(v2v_msgs)]
                encrypted_msg = send_secure_message(front_vehicle, behind_vehicle, msg)
                decrypted_msg = receive_secure_message(behind_vehicle, front_vehicle, encrypted_msg)
                print(f"[{step}] V2V {front_vehicle}->{behind_vehicle}: '{decrypted_msg}'")
                traci.vehicle.setColor(front_vehicle, COMM_COLOR)
                traci.vehicle.setColor(behind_vehicle, COMM_COLOR)
                already_communicated.add(pair)
        # Let other vehicles also message about the signal status to all stopped vehicles
        for idx, (veh_id, _) in enumerate(positions[1:]):
            others_msg = f"The signal is currently red. Waiting for green."
            for other_id, _ in positions:
                if veh_id != other_id:
                    pair_other = (veh_id, other_id)
                    if pair_other not in already_communicated:
                        encrypted_msg = send_secure_message(veh_id, other_id, others_msg)
                        decrypted_msg = receive_secure_message(other_id, veh_id, encrypted_msg)
                        print(f"[{step}] V2V {veh_id}->{other_id}: '{decrypted_msg}'")
                        traci.vehicle.setColor(veh_id, COMM_COLOR)
                        traci.vehicle.setColor(other_id, COMM_COLOR)
                        already_communicated.add(pair_other)

    # WiMAX: emergency vehicle direct to fog
    for veh_id in traci.vehicle.getIDList():
        if is_emergency_vehicle(veh_id):
            print(f"[{step}] WiMAX {veh_id}->Fog: EMERGENCY")
            traci.trafficlight.setRedYellowGreenState(TLS_ID, GREEN_STATE * num_signals)

    step += 1

traci.close()