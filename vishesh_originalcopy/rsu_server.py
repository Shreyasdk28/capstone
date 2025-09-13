# rsu_server.py
import socket
import json
import time
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Server Configuration
SERVER_IP = "0.0.0.0"
SERVER_PORT = 9999
PRIORITY_WEIGHTS = {"HIGH": 10, "MEDIUM": 5, "LOW": 3}
CONGESTION_THRESHOLDS = {"HIGH": 8, "MEDIUM": 5, "LOW": 2}

<<<<<<< HEAD
class TrafficAnalyzer:
    def __init__(self):
        self.signal_history = defaultdict(lambda: deque(maxlen=50))
        self.emergency_log = []
        self.traffic_stats = defaultdict(dict)

    def log_emergency_action(self, signal_id, lane_id, urgency, vehicle_count):
        log_entry = {
            'timestamp': datetime.now(),
            'signal_id': signal_id,
            'lane_id': lane_id,
            'urgency': urgency,
            'vehicles_affected': vehicle_count,
            'action': 'PRIORITY_GREEN'
        }
        self.emergency_log.append(log_entry)

        if len(self.emergency_log) > 100:
            self.emergency_log.pop(0)

    def calculate_lane_priority(self, lane_data, has_emergency=False, urgency=None):
        base_score = lane_data['count']

        if has_emergency and urgency:
            emergency_bonus = PRIORITY_WEIGHTS.get(urgency, 1)
            return base_score + emergency_bonus * 10

        congestion_multiplier = {
            'HIGH': 3,
            'MEDIUM': 2,
            'LOW': 1,
            'NONE': 0
        }.get(lane_data.get('congestion_level', 'LOW'), 1)

        return base_score * congestion_multiplier

    def should_prioritize_emergency(self, lane_data):
        if not lane_data.get('has_emergency', False):
            return False

        urgency = lane_data.get('max_urgency')
        if urgency == 'HIGH':
            return True
        elif urgency == 'MEDIUM' and lane_data['count'] > 2:
            return True
        elif urgency == 'LOW' and lane_data['count'] > 5:
            return True

        return False

    def get_traffic_summary(self):
        if not self.emergency_log:
            return "No recent emergency activity"

        recent_emergencies = [log for log in self.emergency_log
                            if log['timestamp'] > datetime.now() - timedelta(minutes=10)]

        if not recent_emergencies:
            return "No emergency activity in last 10 minutes"

        return f"Handled {len(recent_emergencies)} emergency vehicles in last 10 minutes"

class WiMAXServer:
    def __init__(self):
        self.analyzer = TrafficAnalyzer()
        self.active_signals = {}
        self.client_connections = {}
        self.total_messages_processed = 0

    def clear_traffic_for_emergency(self, signal_id, lane_id, urgency, client_addr, client_port, sock, vehicle_count):
        print(f"\n\033[91m🚨 EMERGENCY PRIORITY ACTIVATED 🚨")
        print(f"Signal: {signal_id} | Lane: {lane_id} | Urgency: {urgency}")
        print(f"Clearing path for emergency vehicle | Affected vehicles: {vehicle_count}\033[0m")

        command = f"MAKE_GREEN|{signal_id}|{lane_id}|{urgency}"
        try:
            sock.sendto(command.encode(), (client_addr, client_port))
            self.analyzer.log_emergency_action(signal_id, lane_id, urgency, vehicle_count)
            print(f"\033[92m✓ Priority command sent successfully\033[0m")
        except Exception as e:
            print(f"\033[91m✗ Failed to send priority command: {e}\033[0m")

    def optimize_normal_traffic(self, signal_id, lanes_data, client_addr, client_port, sock):
        if not lanes_data:
            return

        lane_priorities = {}
        for lane_id, lane_data in lanes_data.items():
            priority = self.analyzer.calculate_lane_priority(lane_data)
            lane_priorities[lane_id] = priority

        if lane_priorities:
            best_lane = max(lane_priorities, key=lane_priorities.get)
            if lane_priorities[best_lane] > 0:
                command = f"MAKE_GREEN|{signal_id}|{best_lane}|NORMAL"
                try:
                    sock.sendto(command.encode(), (client_addr, client_port))
                    print(f"\033[94m[TRAFFIC OPTIMIZATION] Signal {signal_id}: GREEN for lane {best_lane} (Priority: {lane_priorities[best_lane]})\033[0m")
                except Exception as e:
                    print(f"\033[91m[ERROR] Failed to send optimization command: {e}\033[0m")

    def display_signal_status(self, signal_id, lanes_data, total_vehicles, emergency_count, rsu_pos):
        timestamp = datetime.now().strftime("%H:%M:%S")

        print(f"\n\033[96m╔══════════════════════════════════════════════════════════════╗")
        print(f"║  📡 RSU Signal: {signal_id:<20} │ Time: {timestamp}     ║")
        print(f"║  📍 Position: ({rsu_pos[0]:.1f}, {rsu_pos[1]:.1f})<" + " " * 27 + "║")
        print(f"║  🚗 Total Vehicles in Range: {total_vehicles:<8} │ 🚨 Emergencies: {emergency_count:<3}   ║")
        print(f"╠══════════════════════════════════════════════════════════════╣\033[0m")

        if not lanes_data:
            print(f"\033[90m║  No lane data available" + " " * 35 + "║")
        else:
            max_lane_len = max(len(lane_id) for lane_id in lanes_data.keys()) if lanes_data else 10

            for lane_id, lane_info in lanes_data.items():
                lane_label = f"Lane {lane_id}".ljust(max_lane_len + 5)
                count = lane_info['count']
                avg_speed = lane_info.get('average_speed', 0)
                congestion = lane_info.get('congestion_level', 'UNKNOWN')

                basic_info = f"{lane_label}: {count:2d} vehicles │ Avg Speed: {avg_speed:4.1f} m/s │ {congestion:6s}"

                if lane_info.get('has_emergency', False):
                    emergency_vehicles = lane_info.get('emergency_vehicles', [])
                    urgency = lane_info.get('max_urgency', 'UNKNOWN')

                    print(f"\033[93m║  🚑 {basic_info} │ EMERGENCY ({urgency})  ║")
                    for emergency in emergency_vehicles[:2]:
                        print(f"\033[91m║    └─ {emergency['type'].upper()} {emergency['id']} [{emergency['urgency']}]" + " " * (30 - len(emergency['id']) - len(emergency['type'])) + "║")
                else:
                    color = "\033[92m" if count <= 3 else "\033[93m" if count <= 6 else "\033[91m"
                    print(f"{color}║  🚗 {basic_info}" + " " * (64 - len(basic_info) - 6) + "║")

        print(f"\033[96m╚══════════════════════════════════════════════════════════════╝\033[0m")

    def handle_rsu_message(self, message_data, client_addr, sock):
        try:
            signal_id = message_data['signal_id']
            lanes_data = message_data['lanes']
            client_port = message_data.get('client_port', 9998)
            total_vehicles = message_data.get('total_vehicles_in_range', 0)
            rsu_pos = message_data.get('rsu_position', [0, 0])

            self.active_signals[signal_id] = {
                'last_update': datetime.now(),
                'total_vehicles': total_vehicles,
                'lanes': lanes_data,
                'client_addr': client_addr,
                'client_port': client_port
            }

            emergency_count = sum(lane.get('emergency_count', 0) for lane in lanes_data.values())

            self.display_signal_status(signal_id, lanes_data, total_vehicles, emergency_count, rsu_pos)

            emergency_handled = False
            for lane_id, lane_data in lanes_data.items():
                if self.analyzer.should_prioritize_emergency(lane_data):
                    urgency = lane_data.get('max_urgency', 'MEDIUM')
                    vehicle_count = lane_data['count']

                    self.clear_traffic_for_emergency(
                        signal_id, lane_id, urgency, client_addr[0],
                        client_port, sock, vehicle_count
                    )
                    emergency_handled = True
                    break

            if not emergency_handled:
                self.optimize_normal_traffic(signal_id, lanes_data, client_addr[0], client_port, sock)

        except Exception as e:
            print(f"\033[91m[ERROR] Failed to process RSU message: {e}\033[0m")

    def display_server_stats(self):
        while True:
            time.sleep(30)

            active_count = len(self.active_signals)
            total_vehicles = sum(signal['total_vehicles'] for signal in self.active_signals.values())
            traffic_summary = self.analyzer.get_traffic_summary()

            print(f"\n\033[95m" + "=" * 80)
            print(f"🖥️  WiMAX SERVER STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📡 Active RSU Signals: {active_count}")
            print(f"🚗 Total Vehicles Being Monitored: {total_vehicles}")
            print(f"📨 Messages Processed: {self.total_messages_processed}")
            print(f"🚨 Emergency Summary: {traffic_summary}")
            print(f"=" * 80 + "\033[0m")

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((SERVER_IP, SERVER_PORT))

        print(f"\n\033[92m🌐 WiMAX RSU Server started successfully!")
        print(f"📡 Listening on {SERVER_IP}:{SERVER_PORT}")
        print(f"🚀 Ready to handle RSU communications...\033[0m")

        stats_thread = threading.Thread(target=self.display_server_stats)
        stats_thread.daemon = True
        stats_thread.start()

        try:
            while True:
                try:
                    data, addr = sock.recvfrom(8192)
                    message = data.decode()

                    try:
                        message_data = json.loads(message)
                        self.total_messages_processed += 1
                        self.handle_rsu_message(message_data, addr, sock)

                    except json.JSONDecodeError:
                        print(f"\033[91m[ERROR] Malformed JSON message from {addr}: {message[:100]}...\033[0m")
                        continue

                except socket.error as e:
                    print(f"\033[91m[ERROR] Socket error: {e}\033[0m")
                    continue

        except KeyboardInterrupt:
            print(f"\n\033[93m[SHUTDOWN] Server stopped by user\033[0m")
        except Exception as e:
            print(f"\033[91m[ERROR] Unexpected server error: {e}\033[0m")
        finally:
            sock.close()
            print(f"\033[92m[DONE] Server shutdown complete\033[0m")

def main():
    server = WiMAXServer()
    server.run()
=======
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
>>>>>>> 5fd1ca31816f8ab0f2231b616e56f8c534ea3c42

if __name__ == "__main__":
    main()
