import time
import traci

class TrafficLightController:
    def __init__(self, tl_id, config):
        self.tl_id = tl_id
        self.emergency_states = config["emergency_states"]
        self.busy_phase_mapping = config["busy_phase_mapping"]
        self.idle_rotate_interval = config.get("idle_rotate_interval", 10)
        self.emergency_green_time = config.get("emergency_green_time", 30)

        self.reset_state()
        self.build_lane_index_map()

    def reset_state(self):
        self.idle_counter = 0
        self.emergency_mode = False
        self.emergency_end_time = 0.0
        self.saved_program_id = traci.trafficlight.getProgram(self.tl_id)
        self.saved_phase = traci.trafficlight.getPhase(self.tl_id)
        self.current_amb_id = None

    def build_lane_index_map(self):
        self.lane_index_map = {}
        link_groups = traci.trafficlight.getControlledLinks(self.tl_id)
        for i, link_group in enumerate(link_groups):
            for link in link_group:
                self.lane_index_map[link[0]] = i
        print(f"🔗 {self.tl_id}: Lane index map -> {self.lane_index_map}")

    def handle_emergency(self, sim_time, ambulance_map):
        tl_state = traci.trafficlight.getRedYellowGreenState(self.tl_id)
        amb_lane = None
        amb_id = None

        for vid, lane_id in ambulance_map.items():
            if lane_id in self.emergency_states:
                amb_lane = lane_id
                amb_id = vid
                break

        if amb_lane:
            if not self.emergency_mode:
                self.enter_emergency_mode(sim_time, amb_id)

            desired_state = self.emergency_states[amb_lane]
            if tl_state != desired_state:
                traci.trafficlight.setRedYellowGreenState(self.tl_id, desired_state)
                print(f"🚨 {self.tl_id}: Forced emergency state for {amb_id} on {amb_lane}")

        elif self.emergency_mode and sim_time >= self.emergency_end_time:
            self.exit_emergency_mode()

    def enter_emergency_mode(self, sim_time, amb_id):
        self.emergency_mode = True
        self.current_amb_id = amb_id
        self.saved_phase = traci.trafficlight.getPhase(self.tl_id)
        self.saved_program_id = traci.trafficlight.getProgram(self.tl_id)
        self.emergency_end_time = sim_time + self.emergency_green_time
        print(f"🚑 {self.tl_id}: EMERGENCY activated for {amb_id}")

    def exit_emergency_mode(self):
        traci.trafficlight.setProgram(self.tl_id, self.saved_program_id)
        logic = traci.trafficlight.getAllProgramLogics(self.tl_id)[0]
        phase_count = len(logic.phases)
        new_phase = min(self.saved_phase, phase_count - 1)
        traci.trafficlight.setPhase(self.tl_id, new_phase)
        print(f"🟢 {self.tl_id}: Emergency cleared - restored program {self.saved_program_id}, phase {new_phase}")
        self.emergency_mode = False
        self.current_amb_id = None

    def adaptive_control(self, sim_time):
        if self.emergency_mode:
            return

        lane_counts = {
            lane: traci.lane.getLastStepVehicleNumber(lane)
            for lane in self.emergency_states.keys()
        }
        total_vehicles = sum(lane_counts.values())

        if total_vehicles > 0:
            busiest_lane = max(lane_counts, key=lane_counts.get)
            target_phase = self.busy_phase_mapping.get(busiest_lane)

            if target_phase is not None:
                current_phase = traci.trafficlight.getPhase(self.tl_id)
                if target_phase != current_phase:
                    traci.trafficlight.setPhase(self.tl_id, target_phase)
                    print(f"🚦 {self.tl_id}: Set phase {target_phase} for {busiest_lane} (count={lane_counts[busiest_lane]})")
                self.idle_counter = 0
        else:
            self.idle_counter += 1
            if self.idle_counter >= self.idle_rotate_interval:
                logic = traci.trafficlight.getAllProgramLogics(self.tl_id)[0]
                phase_count = len(logic.phases)
                current_phase = traci.trafficlight.getPhase(self.tl_id)
                next_phase = (current_phase + 1) % phase_count
                traci.trafficlight.setPhase(self.tl_id, next_phase)
                print(f"🔄 {self.tl_id}: Idle rotation to phase {next_phase}")
                self.idle_counter = 0

def auto_generate_config(tl_ids):
    config = {}
    for tl_id in tl_ids:
        controlled_links = traci.trafficlight.getControlledLinks(tl_id)
        emergency_states = {}
        busy_phase_mapping = {}

        logic = traci.trafficlight.getAllProgramLogics(tl_id)[0]
        num_phases = len(logic.phases)
        num_signal_groups = len(logic.phases[0].state)

        # Find green phases for each signal group
        green_phases = {}
        for signal_idx in range(num_signal_groups):
            green_phases[signal_idx] = []
            for phase_idx, phase in enumerate(logic.phases):
                if phase.state[signal_idx] in ['G', 'g']:
                    green_phases[signal_idx].append(phase_idx)

        # Create mapping for each lane
        processed_lanes = set()
        for link_group_idx, link_group in enumerate(controlled_links):
            for link in link_group:
                lane_id = link[0]
                if lane_id in processed_lanes:
                    continue
                    
                processed_lanes.add(lane_id)
                
                # Find a green phase for this signal group
                if link_group_idx in green_phases and green_phases[link_group_idx]:
                    target_phase = green_phases[link_group_idx][0]
                else:
                    target_phase = 0
                    
                busy_phase_mapping[lane_id] = target_phase

                # Build emergency state
                state = ["r"] * num_signal_groups
                state[link_group_idx] = "G"
                emergency_states[lane_id] = "".join(state)

        config[tl_id] = {
            "emergency_states": emergency_states,
            "busy_phase_mapping": busy_phase_mapping,
            "idle_rotate_interval": 10,
            "emergency_green_time": 30
        }

        print(f"🛠️ Auto-generated config for TL: {tl_id}")
        print(f"   - Lanes: {list(emergency_states.keys())}")
        print(f"   - Phase mappings: {busy_phase_mapping}")
    return config

def main():
    traci.start(["sumo-gui", "-c", "myConfig.sumocfg", "--step-length", "0.5"])
    print("✅ Connected to SUMO via TraCI")

    all_tl_ids = traci.trafficlight.getIDList()
    print(f"🚥 Found traffic lights: {all_tl_ids}")

    TL_CONFIG = auto_generate_config(all_tl_ids)

    controllers = {}
    for tl_id in all_tl_ids:
        if tl_id in TL_CONFIG:
            controllers[tl_id] = TrafficLightController(tl_id, TL_CONFIG[tl_id])
            print(f"⚙️  Initialized controller for {tl_id}")
        else:
            print(f"⚠️  No configuration for {tl_id} - using default SUMO control")

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        sim_time = traci.simulation.getTime()

        ambulance_map = {}
        for vid in traci.vehicle.getIDList():
            if traci.vehicle.getTypeID(vid) == "emergency":
                try:
                    ambulance_map[vid] = traci.vehicle.getLaneID(vid)
                except traci.TraCIException:
                    continue  # Skip if vehicle no longer exists

        tracked_ambulance = None
        for controller in controllers.values():
            controller.handle_emergency(sim_time, ambulance_map)
            controller.adaptive_control(sim_time)
            if controller.current_amb_id and not tracked_ambulance:
                tracked_ambulance = controller.current_amb_id

        if tracked_ambulance:
            try:
                traci.gui.trackVehicle("View #0", tracked_ambulance)
                traci.gui.setZoom("View #0", 1000)
            except traci.TraCIException:
                pass  # Skip if vehicle no longer exists

        time.sleep(0.05)

    print("✅ Simulation finished")
    traci.close()

if __name__ == "__main__":
    main()