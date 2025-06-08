# rsu_server.py
import socket
import ast

SERVER_IP = "0.0.0.0"
SERVER_PORT = 9999

def decide_green_lane(msg_dict):
    if msg_dict.get("ambulance"):
        print(f"🚑 Ambulance detected in lane {msg_dict['ambulance_lane']}")
        return msg_dict['ambulance_lane']
    lane_density = msg_dict.get("lane_density", {})
    if lane_density:
        # Choose lane with max density
        return max(lane_density.items(), key=lambda x: x[1])[0]
    return None

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((SERVER_IP, SERVER_PORT))
    print(f"📡 RSU Server listening on {SERVER_IP}:{SERVER_PORT}")

    try:
        while True:
            data, addr = s.recvfrom(4096)
            msg = data.decode()
            try:
                msg_dict = ast.literal_eval(msg)
            except Exception:
                print("⚠️ Malformed message:", msg)
                continue

            signal_id = msg_dict.get('signal_id')
            lane_density = msg_dict.get('lane_density')
            print(f"📥 Received from {signal_id}, densities: {lane_density}")
            
            green_lane = decide_green_lane(msg_dict)
            if green_lane:
                reply = {"green_lane": green_lane}
                s.sendto(str(reply).encode(), addr)
                print(f"📤 Sent GREEN to lane: {green_lane}")
    except KeyboardInterrupt:
        print("🛑 Server stopped.")
    finally:
        s.close()

if __name__ == "__main__":
    main()
