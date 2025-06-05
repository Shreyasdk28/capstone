import traci
import time
import csv
import datetime
import os

# Get the project root directory (assuming controller.py is in the intersection folder)
project_root = os.path.dirname(os.path.abspath(__file__))


# Setup CSV logging with path to traffic folder
log_file_path = os.path.join(project_root, "traffic", "traffic_log.csv")
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
log_file = open(log_file_path, mode='w', newline='')
log_writer = csv.writer(log_file)
log_writer.writerow(["Timestamp", "Traffic Density", "Green Lane", "Green Duration"])

# Mapping of detectors to lane directions
detector_lanes = {
    "W1": "W", "W2": "W", "W3": "W",
    "E1": "E", "E2": "E",
    "N1": "N", "N2": "N", "N3": "N",
    "S1": "S", "S2": "S",
}

# Initialize counts
lane_counts = {
    "W": 0,
    "E": 0,
    "N": 0,
    "S": 0,
}

traffic_light_id = "center"
# Update path to simulation.sumocfg
sumocfg_path = os.path.join(project_root, "simulation.sumocfg")
sumo_cmd = ["sumo-gui", "-c", sumocfg_path]
traci.start(sumo_cmd)

print("Controller running...")
print("Loaded detectors:", traci.inductionloop.getIDList())
print("Available traffic lights:", traci.trafficlight.getIDList())

try:
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()

        # Reset counts
        for lane in lane_counts:
            lane_counts[lane] = 0

        # Update counts from detectors
        for detector_id in detector_lanes:
            count = traci.inductionloop.getLastStepVehicleNumber(detector_id)
            direction = detector_lanes[detector_id]
            lane_counts[direction] += count

        # Tie-breaker logic
        max_density = max(lane_counts.values())
        max_lanes = [lane for lane, count in lane_counts.items() if count == max_density]

        # Prioritize direction if tie
        priority_order = ['N', 'E', 'S', 'W']
        for direction in priority_order:
            if direction in max_lanes:
                green_direction = direction
                break

        # Set phase based on green_direction
        if green_direction == "W":
            traci.trafficlight.setPhase(traffic_light_id, 0)
        elif green_direction == "E":
            traci.trafficlight.setPhase(traffic_light_id, 1)
        elif green_direction == "N":
            traci.trafficlight.setPhase(traffic_light_id, 2)
        elif green_direction == "S":
            traci.trafficlight.setPhase(traffic_light_id, 3)

        # Dynamic green duration (between 5–20 seconds)
        green_duration = max(5, min(20, lane_counts[green_direction] * 2))

        # Log and print
        print(f"Traffic density: {lane_counts}, Green for: {green_direction}, Duration: {green_duration}s")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_writer.writerow([timestamp, dict(lane_counts), green_direction, green_duration])

        time.sleep(green_duration)

finally:
    traci.close()
    log_file.close()
    print("Simulation ended and log saved.")