import os
import sys
import traci
import socket
import time
import random
import threading
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Set

if 'SUMO_HOME' not in os.environ:
    sys.exit("Please declare environment variable 'SUMO_HOME'")
tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
sys.path.append(tools)

@dataclass
class RSUConfig:
    rsu_id: str
    position: tuple
    range: int
    client_port: int
    controlled_signals: List[str]

BASE_CLIENT_PORT = 9998
SERVER_IP = "127.0.0.1"
SERVER_PORT = 9999
RSU_RANGE = 120
EMERGENCY_SPAWN_RATE = 0.03
V2V_RANGE = 60

class MultiRSUManager:
    def __init__(self):
        self.rsu_configs = {}
        self.emergency_vehicles = {}
        self.shared_vehicle_data = {}
        self.running = True
        self.command_sockets = {}

    def discover_and_setup_rsus(self):
        traffic_lights = traci.trafficlight.getIDList()

        for i, tl_id in enumerate(traffic_lights):
            try:
                lanes = traci.trafficlight.getControlledLanes(tl_id)
                if lanes:
                    lane_shape = traci.lane.getShape(lanes[0])
                    position = lane_shape[0] if lane_shape else (0, 0)

                    rsu_config = RSUConfig(
                        rsu_id=f"RSU_{tl_id}",
                        position=position,
                        range=RSU_RANGE,
                        client_port=BASE_CLIENT_PORT + i,
                        controlled_signals=[tl_id]
                    )

                    self.rsu_configs[tl_id] = rsu_config

                    print(f"\033[96m[RSU SETUP] {rsu_config.rsu_id} configured for signal {tl_id} at position {position} on port {rsu_config.client_port}\033[0m")

            except Exception as e:
                print(f"\033[91m[ERROR] Failed to setup RSU for {tl_id}: {e}\033[0m")

        return len(self.rsu_configs)

    def setup_command_listeners(self):
        for tl_id, config in self.rsu_configs.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(('', config.client_port))
                sock.settimeout(0.5)
                self.command_sockets[tl_id] = sock

                listener_thread = threading.Thread(
                    target=self.command_listener_worker,
                    args=(tl_id, sock),
                    daemon=True
                )
                listener_thread.start()

            except Exception as e:
                print(f"\033[91m[ERROR] Failed to setup command listener for {tl_id}: {e}\033[0m")

    def command_listener_worker(self, tl_id, sock):
        print(f"\033[92m[LISTENER] RSU {tl_id} command listener started on port {self.rsu_configs[tl_id].client_port}\033[0m")

        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                command = data.decode()

                if command.startswith("MAKE_GREEN"):
                    parts = command.split("|")
                    if len(parts) >= 3:
                        signal_id = parts[1]
                        lane_id = parts[2]
                        urgency = parts[3] if len(parts) > 3 else "NORMAL"

                        if signal_id == tl_id:
                            print(f"\033[92m[COMMAND] RSU {tl_id} executing GREEN command for lane {lane_id} | Urgency: {urgency}\033[0m")
                            self.execute_green_command(signal_id, lane_id)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"\033[91m[ERROR] Command listener {tl_id} error: {e}\033[0m")

    def execute_green_command(self, signal_id, lane_id):
        try:
            links = traci.trafficlight.getControlledLinks(signal_id)
            current_state = list(traci.trafficlight.getRedYellowGreenState(signal_id))

            found = False
            for i, link_group in enumerate(links):
                for link in link_group:
                    if link[0] == lane_id:
                        current_state[i] = 'G'
                        found = True
                        break
                if found:
                    break

            if found:
                new_state = ''.join(current_state)
                traci.trafficlight.setRedYellowGreenState(signal_id, new_state)
                print(f"\033[92m[SIGNAL CONTROL] {signal_id} state: {new_state} (GREEN: {lane_id})\033[0m")
            else:
                print(f"\033[93m[WARNING] Lane {lane_id} not found in signal {signal_id}\033[0m")

        except Exception as e:
            print(f"\033[91m[ERROR] Failed to execute green command for {signal_id}: {e}\033[0m")

    def update_vehicle_data(self):
        self.shared_vehicle_data.clear()

        for vid in traci.vehicle.getIDList():
            try:
                pos = traci.vehicle.getPosition(vid)
                lane_id = traci.vehicle.getLaneID(vid)
                speed = traci.vehicle.getSpeed(vid)

                self.shared_vehicle_data[vid] = {
                    'position': pos,
                    'lane_id': lane_id,
                    'speed': speed,
                    'is_emergency': vid in self.emergency_vehicles
                }

            except Exception:
                continue

    def spawn_emergency_vehicles(self):
        current_vehicles = set(traci.vehicle.getIDList())
        new_vehicles = current_vehicles - set(self.emergency_vehicles.keys())

        for vid in new_vehicles:
            if random.random() < EMERGENCY_SPAWN_RATE:
                emergency_type = random.choice(['ambulance', 'fire', 'police'])
                urgency = random.choice(['HIGH', 'MEDIUM', 'LOW'])

                try:
                    colors = {'ambulance': (255, 255, 255), 'fire': (255, 0, 0), 'police': (0, 0, 255)}
                    traci.vehicle.setColor(vid, colors[emergency_type])

                    self.emergency_vehicles[vid] = {
                        'type': emergency_type,
                        'urgency': urgency,
                        'spawn_time': time.time(),
                        'route': traci.vehicle.getRouteID(vid)
                    }

                    print(f"\033[91m🚨 [EMERGENCY SPAWN] {emergency_type.upper()} {vid} | Urgency: {urgency} | Route: {self.emergency_vehicles[vid]['route']} 🚨\033[0m")

                except Exception as e:
                    print(f"\033[91m[ERROR] Failed to spawn emergency vehicle {vid}: {e}\033[0m")

        active_vehicles = set(traci.vehicle.getIDList())
        self.emergency_vehicles = {vid: data for vid, data in self.emergency_vehicles.items() if vid in active_vehicles}

    def analyze_rsu_traffic(self, rsu_config):
        traffic_data = {}

        for signal_id in rsu_config.controlled_signals:
            try:
                controlled_lanes = traci.trafficlight.getControlledLanes(signal_id)
                unique_lanes = list(set([lane for lane in controlled_lanes if not lane.startswith(":")]))

                lane_analysis = {}
                total_vehicles_in_range = 0

                for lane_id in unique_lanes:
                    lane_analysis[lane_id] = {
                        'count': 0,
                        'emergency_count': 0,
                        'emergency_vehicles': [],
                        'has_emergency': False,
                        'max_urgency': None,
                        'average_speed': 0,
                        'congestion_level': 'NONE'
                    }

                for vid, vehicle_data in self.shared_vehicle_data.items():
                    pos = vehicle_data['position']
                    distance = ((pos[0] - rsu_config.position[0]) ** 2 + (pos[1] - rsu_config.position[1]) ** 2) ** 0.5

                    if distance <= rsu_config.range:
                        total_vehicles_in_range += 1
                        lane_id = vehicle_data['lane_id']

                        if lane_id in lane_analysis:
                            lane_analysis[lane_id]['count'] += 1

                            if vehicle_data['is_emergency'] and vid in self.emergency_vehicles:
                                emergency_info = self.emergency_vehicles[vid]
                                lane_analysis[lane_id]['emergency_count'] += 1
                                lane_analysis[lane_id]['has_emergency'] = True
                                lane_analysis[lane_id]['emergency_vehicles'].append({
                                    'id': vid,
                                    'type': emergency_info['type'],
                                    'urgency': emergency_info['urgency']
                                })

                                current_urgency = emergency_info['urgency']
                                if (lane_analysis[lane_id]['max_urgency'] is None or
                                    ['HIGH', 'MEDIUM', 'LOW'].index(current_urgency) <
                                    ['HIGH', 'MEDIUM', 'LOW'].index(lane_analysis[lane_id]['max_urgency'])):
                                    lane_analysis[lane_id]['max_urgency'] = current_urgency

                for lane_id in lane_analysis:
                    try:
                        vehicles_on_lane = [vid for vid, data in self.shared_vehicle_data.items()
                                          if data['lane_id'] == lane_id]

                        if vehicles_on_lane:
                            avg_speed = sum(self.shared_vehicle_data[vid]['speed']
                                          for vid in vehicles_on_lane) / len(vehicles_on_lane)
                            lane_analysis[lane_id]['average_speed'] = round(avg_speed, 2)

                            vehicle_count = lane_analysis[lane_id]['count']
                            if vehicle_count == 0:
                                lane_analysis[lane_id]['congestion_level'] = 'NONE'
                            elif vehicle_count <= 3 and avg_speed > 8:
                                lane_analysis[lane_id]['congestion_level'] = 'LOW'
                            elif vehicle_count <= 6 or avg_speed > 4:
                                lane_analysis[lane_id]['congestion_level'] = 'MEDIUM'
                            else:
                                lane_analysis[lane_id]['congestion_level'] = 'HIGH'
                    except:
                        pass

                traffic_data[signal_id] = {
                    'lanes': lane_analysis,
                    'total_vehicles_in_range': total_vehicles_in_range,
                    'rsu_id': rsu_config.rsu_id,
                    'rsu_position': rsu_config.position
                }

            except Exception as e:
                print(f"\033[91m[ERROR] Failed to analyze traffic for RSU {rsu_config.rsu_id}: {e}\033[0m")

        return traffic_data

    def send_rsu_data_to_server(self, rsu_config, traffic_data, server_socket):
        for signal_id, data in traffic_data.items():
            message = {
                'signal_id': signal_id,
                'rsu_id': data['rsu_id'],
                'timestamp': datetime.now().isoformat(),
                'total_vehicles_in_range': data['total_vehicles_in_range'],
                'lanes': data['lanes'],
                'client_port': rsu_config.client_port,
                'rsu_position': data['rsu_position']
            }

            try:
                server_socket.sendto(json.dumps(message).encode(), (SERVER_IP, SERVER_PORT))
            except Exception as e:
                print(f"\033[91m[ERROR] Failed to send data from {rsu_config.rsu_id}: {e}\033[0m")

    def display_multi_rsu_status(self):
        total_emergency = len(self.emergency_vehicles)
        total_vehicles = len(self.shared_vehicle_data)
        active_rsus = len(self.rsu_configs)

        print(f"\n\033[95m{'=' * 80}")
        print(f"🏢 MULTI-RSU VANET SYSTEM STATUS | {datetime.now().strftime('%H:%M:%S')}")
        print(f"📡 Active RSUs: {active_rsus} | 🚗 Total Vehicles: {total_vehicles} | 🚨 Emergency: {total_emergency}")
        print(f"{'=' * 80}\033[0m")

        for tl_id, config in list(self.rsu_configs.items())[:3]:
            vehicles_in_range = sum(1 for vid, data in self.shared_vehicle_data.items()
                                  if ((data['position'][0] - config.position[0]) ** 2 +
                                     (data['position'][1] - config.position[1]) ** 2) ** 0.5 <= config.range)

            print(f"\033[96m  📡 {config.rsu_id}: {vehicles_in_range} vehicles in range | Port: {config.client_port} | Position: ({config.position[0]:.1f}, {config.position[1]:.1f})\033[0m")

    def run_simulation(self):
        sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
        sumo_cmd = [sumo_binary, "-c", "config/simulation.sumocfg", "--start"]

        try:
            traci.start(sumo_cmd)
            print(f"\033[92m[INIT] SUMO simulation started successfully\033[0m")
        except Exception as e:
            print(f"\033[91m[ERROR] Failed to start SUMO: {e}\033[0m")
            return

        rsu_count = self.discover_and_setup_rsus()
        if rsu_count == 0:
            print(f"\033[91m[ERROR] No RSUs configured. Exiting.\033[0m")
            return

        self.setup_command_listeners()

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        print(f"\033[92m[READY] Multi-RSU system ready with {rsu_count} RSUs\033[0m")

        step_count = 0
        last_status_display = 0

        try:
            while traci.simulation.getMinExpectedNumber() > 0:
                current_time = time.time()
                traci.simulationStep()
                step_count += 1

                self.update_vehicle_data()

                if step_count % 200 == 0:
                    self.spawn_emergency_vehicles()

                for rsu_config in self.rsu_configs.values():
                    traffic_data = self.analyze_rsu_traffic(rsu_config)
                    self.send_rsu_data_to_server(rsu_config, traffic_data, server_socket)

                if current_time - last_status_display >= 10:
                    self.display_multi_rsu_status()
                    last_status_display = current_time

                time.sleep(0.1)

        except KeyboardInterrupt:
            print(f"\n\033[93m[SHUTDOWN] Multi-RSU simulation interrupted by user\033[0m")
        except Exception as e:
            print(f"\033[91m[ERROR] Simulation error: {e}\033[0m")
        finally:
            self.cleanup()

    def cleanup(self):
        print(f"\033[93m[CLEANUP] Shutting down Multi-RSU system...\033[0m")

        self.running = False

        for sock in self.command_sockets.values():
            try:
                sock.close()
            except:
                pass

        try:
            traci.close()
        except:
            pass

        print(f"\033[92m[DONE] Multi-RSU simulation ended successfully\033[0m")

def main():
    print(f"\033[94m" + "=" * 80)
    print(f"🚀 VANET Multi-RSU Simulation System")
    print(f"📡 Initializing multiple RSU clients...")
    print(f"=" * 80 + "\033[0m")

    manager = MultiRSUManager()
    manager.run_simulation()

if __name__ == "__main__":
    main()
