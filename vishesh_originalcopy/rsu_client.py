import traci
import time

# Mapping each lane to a specific traffic light phase
def get_phase_for_lane(lane_id):
    phase_map = {
        '-133117360_0': 2,
        '1311716614#2_0': 1,
        '-1311716614#3_0': 0
    }
    return phase_map.get(lane_id, 0)

def main():
    tl_id = '1836940136'  # Traffic light ID - adjust if needed
    idle_counter = 0
    idle_rotate_interval = 10
    current_phase = -1

    try:
        traci.start(["sumo-gui", "-c", "myConfig.sumocfg"])
        print("✅ Connected to SUMO via TraCI")

        # Print traffic light and lane info for debugging
        print("🔍 Available traffic lights:", traci.trafficlight.getIDList())
        print("🔍 Available lanes:", traci.lane.getIDList())

        # Print traffic light phases and their states
        logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
        print(f"🛑 Traffic light '{tl_id}' program has {len(logic.phases)} phases:")
        for i, phase in enumerate(logic.phases):
            print(f"  Phase {i}: duration={phase.duration}, state='{phase.state}'")

        lane_ids = ['-133117360_0', '1311716614#2_0', '-1311716614#3_0']

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()

            # Count vehicles per lane
            lane_density = {lane: traci.lane.getLastStepVehicleNumber(lane) for lane in lane_ids}
            total_vehicles = sum(lane_density.values())

            # Detect ambulances and vehicle types
            ambulance_detected = False
            ambulance_lane = None
            ambulance_ids = []

            print("🔍 Checking vehicles and types:")
            for veh_id in traci.vehicle.getIDList():
                veh_type = traci.vehicle.getTypeID(veh_id)
                print(f"  Vehicle '{veh_id}' type: '{veh_type}'")
                if veh_type == "emergency":  # Update this string if your ambulance type differs
                    lane = traci.vehicle.getLaneID(veh_id)
                    ambulance_detected = True
                    ambulance_lane = lane
                    ambulance_ids.append((veh_id, lane))
                    # We break on first ambulance, remove break if multiple ambulances must be tracked
                    break

            print("📤 Traffic Status:")
            print("   Vehicles Total:", total_vehicles)
            print("   Lane Density:", lane_density)
            print("   Ambulance(s):", ambulance_ids)

            current_tl_phase = traci.trafficlight.getPhase(tl_id)
            print(f"ℹ️ Current traffic light phase: {current_tl_phase}")

            if ambulance_detected:
                # Zoom and track ambulance in GUI
                traci.gui.setZoom("View #0", 500)
                traci.gui.trackVehicle("View #0", ambulance_ids[0][0])

                if ambulance_lane not in lane_density:
                    print(f"⚠️ Ambulance detected in unknown lane: {ambulance_lane}")
                    continue

                new_phase = get_phase_for_lane(ambulance_lane)
                print(f"🚨 Ambulance detected on lane '{ambulance_lane}', setting green phase {new_phase}")

                if new_phase != current_phase:
                    # You can either set phase index (simpler) or force exact signal state (more precise)
                    traci.trafficlight.setPhase(tl_id, new_phase)
                    # OR (uncomment below to force exact signal state string)
                    # new_state = logic.phases[new_phase].state
                    # traci.trafficlight.setRedYellowGreenState(tl_id, new_state)

                    current_phase = new_phase
                    print(f"✅ Phase changed to {new_phase} for ambulance lane")
                else:
                    print(f"✅ Already green for ambulance lane {ambulance_lane}")

            elif total_vehicles == 0:
                idle_counter += 1
                if idle_counter % idle_rotate_interval == 0:
                    next_phase = (current_tl_phase + 1) % len(logic.phases)
                    traci.trafficlight.setPhase(tl_id, next_phase)
                    current_phase = next_phase
                    print(f"🔄 No vehicles → rotated phase to {next_phase}")
                else:
                    print(f"⏳ No traffic → waiting to rotate (idle count: {idle_counter})")

            else:
                idle_counter = 0
                max_lane = max(lane_density, key=lane_density.get)
                new_phase = get_phase_for_lane(max_lane)
                print(f"🚥 Normal traffic detected. Max lane '{max_lane}' with {lane_density[max_lane]} vehicles.")

                if new_phase != current_phase:
                    traci.trafficlight.setPhase(tl_id, new_phase)
                    current_phase = new_phase
                    print(f"✅ Phase changed to {new_phase} for lane with highest traffic")
                else:
                    print(f"ℹ️ Already green for most dense lane {max_lane}")

            time.sleep(1)

        print("✅ Simulation ended. Closing TraCI.")
        traci.close()

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        traci.close()

if __name__ == "__main__":
    main()
