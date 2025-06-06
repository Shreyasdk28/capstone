import socket
import ast

SERVER_IP = "0.0.0.0"
SERVER_PORT = 9999

def clear_traffic(signal_id, lane_id):
    # Simulate traffic light clearance
    print(f"*** CLEARING TRAFFIC at signal {signal_id} for lane {lane_id} due to incoming ambulance! ***")

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((SERVER_IP, SERVER_PORT))
    print(f"RSU Server listening on {SERVER_IP}:{SERVER_PORT}")

    try:
        while True:
            data, addr = s.recvfrom(4096)
            msg = data.decode()
            try:
                msg_dict = ast.literal_eval(msg)
            except Exception:
                print("Malformed message:", msg)
                continue

            print(f"Signal {msg_dict['signal_id']} sees {msg_dict['vehicle_count']} vehicles.")
            if msg_dict.get("ambulance"):
                print(f"  AMBULANCE detected! Urgency: {msg_dict.get('urgency')}")
                lane = msg_dict.get("ambulance_lane")
                if lane:
                    clear_traffic(msg_dict['signal_id'], lane)
    except KeyboardInterrupt:
        print("Server stopped.")
    finally:
        s.close()

if __name__ == "__main__":
    main()