import traci

# Start SUMO GUI
sumoCmd = ["sumo-gui", "-c", "simple.sumocfg"]
traci.start(sumoCmd)

COMM_COLOR = (0, 255, 0, 255)    # Green for communicating
DEFAULT_COLOR = (255, 0, 0, 255)  # Original red

def get_stopped_vehicles_near_tls(tls_id):
    lane_ids = traci.trafficlight.getControlledLanes(tls_id)
    stopped_vehicles = []
    for lane in lane_ids:
        veh_ids = traci.lane.getLastStepVehicleIDs(lane)
        for vid in veh_ids:
            speed = traci.vehicle.getSpeed(vid)
            if speed < 0.1:  # Vehicle is considered stopped
                stopped_vehicles.append(vid)
    return stopped_vehicles

step = 0
already_communicated = set()

while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep()
    
    # Reset colors each step
    for veh_id in traci.vehicle.getIDList():
        traci.vehicle.setColor(veh_id, DEFAULT_COLOR)

    tls_state = traci.trafficlight.getRedYellowGreenState("n1")

    if 'r' in tls_state:  # Check if any red light active
        stopped_vehicles = get_stopped_vehicles_near_tls("n1")
        if len(stopped_vehicles) >= 2:
            v1, v2 = stopped_vehicles[:2]
            pair = tuple(sorted((v1, v2)))
            if pair not in already_communicated:
                print(f"[Step {step}] Communication Triggered:")
                print(f"  🚗 {v1} received message: 'RED LIGHT ALERT' from {v2}")
                already_communicated.add(pair)

            traci.vehicle.setColor(v1, COMM_COLOR)
            traci.vehicle.setColor(v2, COMM_COLOR)

    step += 1

traci.close()
