import traci
import os
import math
import time
from kyber_py.ml_kem import ML_KEM_512 as Kyber
from dilithium_py.dilithium import Dilithium2 as Dilithium
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
# Add this at the top of your file if using system randomness:
import os
from dilithium.ase256_ctr_drbg import AES256_CTR_DRBG
# If you want to use system randomness instead:
os.urandom = lambda n: AES256_CTR_DRBG().generate(n)
# ------------------------ 
# Simulation Configuration
# ------------------------
SUMO_CMD = ["sumo-gui", "-c", "simple.sumocfg"]
COMM_COLOR = (0, 255, 0, 255)    # Green for secure communication
DEFAULT_COLOR = (255, 0, 0, 255)  # Red for default
BROADCAST_RADIUS = 50  # meters
SIMULATION_END_TIME = 100  # seconds

# ------------------------
# Post-Quantum Crypto Setup
# ------------------------
vehicle_keys = {}

def initialize_vehicle_keys(vehicle_id):
    if vehicle_id not in vehicle_keys:
        # Generate Kyber512 key pair
        kyber_ek, kyber_dk = Kyber.keygen()
        
        # Generate Dilithium2 key pair
        dilithium_pk, dilithium_sk = Dilithium.keygen()
        
        vehicle_keys[vehicle_id] = {
            'kyber_ek': kyber_ek,
            'kyber_dk': kyber_dk,
            'dilithium_pk': dilithium_pk,
            'dilithium_sk': dilithium_sk
        }

# ------------------------
# Secure Communication Functions
# ------------------------
def send_secure_message(sender, receiver, message):
    initialize_vehicle_keys(receiver)
    
    # Kyber Key Encapsulation
    shared_key, kyber_ct = Kyber.encaps(
        vehicle_keys[receiver]['kyber_ek']
    )
    
    # AES-GCM Encryption
    cipher = AESGCM(shared_key)
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(nonce, message.encode(), None)
    
    # Dilithium Signature
    signature = Dilithium.sign(
        vehicle_keys[sender]['dilithium_sk'], 
        ciphertext
    )
    
    return {
        'kyber_ct': kyber_ct,
        'ciphertext': ciphertext,
        'nonce': nonce,
        'signature': signature
    }

def receive_secure_message(receiver, sender, encrypted_data):
    try:
        initialize_vehicle_keys(sender)
        
        # Kyber Key Decapsulation
        shared_key = Kyber.decaps(
            vehicle_keys[receiver]['kyber_dk'],
            encrypted_data['kyber_ct']
        )
        
        # AES-GCM Decryption
        cipher = AESGCM(shared_key)
        plaintext = cipher.decrypt(
            encrypted_data['nonce'],
            encrypted_data['ciphertext'],
            None
        )
        
        # Dilithium Verification
        if not Dilithium.verify(
            vehicle_keys[sender]['dilithium_pk'],
            encrypted_data['ciphertext'],
            encrypted_data['signature']
        ):
            print(f"⚠️ Signature verification failed for {sender}")
            return None
            
        return plaintext.decode()
    
    except Exception as e:
        print(f"❌ Decryption error: {e}")
        return None

# ------------------------
# Simulation Helpers
# ------------------------
def calculate_distance(pos1, pos2):
    return math.sqrt((pos1[0]-pos2[0])**2 + (pos1[1]-pos2[1])**2)

def get_vehicles_in_radius(position, radius):
    return [veh_id for veh_id in traci.vehicle.getIDList() 
            if calculate_distance(position, traci.vehicle.getPosition(veh_id)) <= radius]

def get_stopped_vehicles_near_tls(tls_id):
    return [vid for lane in traci.trafficlight.getControlledLanes(tls_id)
            for vid in traci.lane.getLastStepVehicleIDs(lane)
            if traci.vehicle.getSpeed(vid) < 0.1]

# ------------------------
# Main Simulation Logic
# ------------------------
def run_simulation():
    try:
        traci.start(SUMO_CMD)
        step = 0
        communicated_pairs = set()
        
        print("\n🚗 VANET Simulation with Post-Quantum Cryptography")
        print("🔐 Using Kyber512 + Dilithium2 + AES-GCM")

        while traci.simulation.getTime() < SIMULATION_END_TIME:
            traci.simulationStep()
            
            # Reset vehicle colors
            for veh_id in traci.vehicle.getIDList():
                traci.vehicle.setColor(veh_id, DEFAULT_COLOR)

            # Vehicle-to-Vehicle Communication
            stopped_vehicles = get_stopped_vehicles_near_tls("n1")
            if len(stopped_vehicles) >= 2:
                v1, v2 = stopped_vehicles[:2]
                
                if (v1, v2) not in communicated_pairs:
                    # Secure message exchange
                    encrypted = send_secure_message(v2, v1, "EMERGENCY STOP")
                    decrypted = receive_secure_message(v1, v2, encrypted)
                    
                    if decrypted:
                        print(f"\n🔒 Secure V2V Communication ({traci.simulation.getTime():.1f}s):")
                        print(f"  {v2} → {v1}: {decrypted}")
                        
                        # Broadcast to nearby vehicles
                        nearby = get_vehicles_in_radius(traci.vehicle.getPosition(v2), BROADCAST_RADIUS)
                        for veh in nearby:
                            if veh not in [v1, v2]:
                                send_secure_message(v2, veh, "FORWARDED ALERT")
                                traci.vehicle.setColor(veh, COMM_COLOR)
                                
                        communicated_pairs.add((v1, v2))
                        traci.vehicle.setColor(v1, COMM_COLOR)
                        traci.vehicle.setColor(v2, COMM_COLOR)

            step += 1
            time.sleep(0.1)

    except Exception as e:
        print(f"❌ Simulation error: {e}")
    finally:
        traci.close()
        print(f"\n📊 Simulation ended at {traci.simulation.getTime():.1f}s")
        print(f"  Total secure exchanges: {len(communicated_pairs)}")

# ------------------------
# Entry Point
# ------------------------
if __name__ == "__main__":
    run_simulation()
