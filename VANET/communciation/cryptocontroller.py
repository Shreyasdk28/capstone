import traci
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import os
import hashlib
import math

# Start SUMO GUI
sumoCmd = ["sumo-gui", "-c", "simple.sumocfg"]
traci.start(sumoCmd)

COMM_COLOR = (0, 255, 0, 255)    # Green for communication
DEFAULT_COLOR = (255, 0, 0, 255)  # Red for default
BROADCAST_RADIUS = 50  # meters

RSU_IDS = ["rsu_intersection", "rsu_main"]

# ------------------------
# Helper: Calculate distance between two vehicles
# ------------------------
def calculate_distance(veh1_id, veh2_id):
    pos1 = traci.vehicle.getPosition(veh1_id)
    pos2 = traci.vehicle.getPosition(veh2_id)
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

# ------------------------
# Helper: Get vehicles within radius
# ------------------------
def get_vehicles_in_radius(sender_id, radius):
    nearby_vehicles = []
    for veh_id in traci.vehicle.getIDList():
        if veh_id != sender_id:  # Don't include the sender
            distance = calculate_distance(sender_id, veh_id)
            if distance <= radius:
                nearby_vehicles.append(veh_id)
    return nearby_vehicles

# ------------------------
# Helper: Get stopped vehicles near TLS
# ------------------------
def get_stopped_vehicles_near_tls(tls_id):
    lane_ids = traci.trafficlight.getControlledLanes(tls_id)
    stopped_vehicles = []
    for lane in lane_ids:
        veh_ids = traci.multientryexit.getLastStepVehicleIDs(rsu_id)
        for vid in veh_ids:
            speed = traci.vehicle.getSpeed(vid)
            if speed < 0.1:
                stopped_vehicles.append(vid)
    return stopped_vehicles

# ------------------------
# Post-Quantum Crypto Implementation
# ------------------------

vehicle_shared_keys = {}

def get_shared_secret(sender, receiver):
    # Generate same shared secret for both directions using vehicle IDs
    ids = "_".join(sorted([sender, receiver]))
    return hashlib.sha256(ids.encode()).digest()  # 32 bytes

def pqc_handshake(sender, receiver):
    shared_secret = get_shared_secret(sender, receiver)
    vehicle_shared_keys[(sender, receiver)] = shared_secret
    vehicle_shared_keys[(receiver, sender)] = shared_secret

def send_secure_message(sender, receiver, message):
    if (sender, receiver) not in vehicle_shared_keys:
        pqc_handshake(sender, receiver)
    
    key = vehicle_shared_keys[(sender, receiver)]
    cipher = ChaCha20Poly1305(key)
    nonce = os.urandom(12)  # 96-bit nonce for XChaCha20-Poly1305
    associated_data = b"VANET_MESSAGE"  # Additional authenticated data
    
    # Encrypt the message
    ct = cipher.encrypt(nonce, message.encode(), associated_data)
    return nonce + ct

def receive_secure_message(receiver, sender, encrypted_msg):
    key = vehicle_shared_keys[(receiver, sender)]
    nonce = encrypted_msg[:12]
    ct = encrypted_msg[12:]
    associated_data = b"VANET_MESSAGE"
    
    cipher = ChaCha20Poly1305(key)
    try:
        pt = cipher.decrypt(nonce, ct, associated_data)
        return pt.decode()
    except Exception as e:
        print(f"Decryption failed: {e}")
        return None

# ------------------------
# Main Loop
# ------------------------

step = 0
already_communicated = set()

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()
    
    # Reset all vehicle colors
    for veh_id in traci.vehicle.getIDList():
        traci.vehicle.setColor(veh_id, DEFAULT_COLOR)

    tls_state = traci.trafficlight.getRedYellowGreenState("n1")

    if 'r' in tls_state:  # If red light present
        stopped_vehicles = get_stopped_vehicles_near_tls("n1")
        if len(stopped_vehicles) >= 2:
            v1, v2 = stopped_vehicles[:2]
            pair = tuple(sorted((v1, v2)))
            if pair not in already_communicated:
                plain_message = "RED LIGHT ALERT"
                encrypted_msg = send_secure_message(v2, v1, plain_message)
                decrypted_msg = receive_secure_message(v1, v2, encrypted_msg)
                
                if decrypted_msg:
                    print(f"\n[Step {step}] 🛡️ Post-Quantum Secure Communication:")
                    print(f"  📤 Sender: {v2}")
                    print(f"  📥 Receiver: {v1}")
                    print(f"  📝 Plain Text: '{plain_message}'")
                    print(f"  🔒 Encrypted (hex): {encrypted_msg.hex()}")
                    print(f"  📖 Decrypted: '{decrypted_msg}'")
                    
                    # Broadcast to nearby vehicles
                    nearby_vehicles = get_vehicles_in_radius(v2, BROADCAST_RADIUS)
                    if nearby_vehicles:
                        print(f"\n  📢 Broadcasting to {len(nearby_vehicles)} nearby vehicles:")
                        for nearby_veh in nearby_vehicles:
                            distance = calculate_distance(v2, nearby_veh)
                            print(f"    - Vehicle {nearby_veh} (distance: {distance:.2f}m)")
                            # Send message to nearby vehicle
                            encrypted_broadcast = send_secure_message(v2, nearby_veh, plain_message)
                            decrypted_broadcast = receive_secure_message(nearby_veh, v2, encrypted_broadcast)
                            if decrypted_broadcast:
                                print(f"      ✓ Message received and decrypted by {nearby_veh}")
                                traci.vehicle.setColor(nearby_veh, COMM_COLOR)
                    
                    already_communicated.add(pair)

                traci.vehicle.setColor(v1, COMM_COLOR)
                traci.vehicle.setColor(v2, COMM_COLOR)

    # --- V2I (RSU) Communication ---
    for rsu_id in RSU_IDS:
        try:
            vehicles_at_rsu = traci.multientryexit.getLastStepVehicleIDs(rsu_id)
            for veh_id in vehicles_at_rsu:
                print(f"[Step {step}] RSU {rsu_id} communicates with vehicle {veh_id}: 'TRAFFIC INFO'")
                # Optionally, you could add secure message logic here as well
        except Exception as e:
            # If RSU is not present in the current step, just skip
            pass

    step += 1

traci.close()