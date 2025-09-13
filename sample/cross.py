import traci
import sys
import os
import pygame   # 🔊 For siren sound


class SirenManager:
    """Handles ambulance siren sound"""
    def __init__(self, sound_file="siren.wav"):
        pygame.mixer.init()
        self.siren = pygame.mixer.Sound(sound_file)

    def play(self):
        if not pygame.mixer.get_busy():
            self.siren.play(-1)  # loop forever

    def stop(self):
        self.siren.stop()


class AmbulancePriorityController:
    def __init__(self, junction_id, siren_manager):
        self.junction_id = junction_id
        self.normal_program = "0"
        self.emergency_active = False
        self.active_lane = None
        self.siren_manager = siren_manager

    def detect_ambulance(self):
        """Detect if ambulance is on approach lanes"""
        lanes = ["N2J_0", "S2J_0", "E2J_0", "W2J_0"]
        approaching_ambulances = []

        for lane in lanes:
            try:
                vehicles = traci.lane.getLastStepVehicleIDs(lane)
                for vehicle in vehicles:
                    if traci.vehicle.getTypeID(vehicle) == "ambulance":
                        pos = traci.vehicle.getLanePosition(vehicle)
                        lane_length = traci.lane.getLength(lane)
                        distance_to_junction = lane_length - pos

                        if 0 <= distance_to_junction < 50:
                            approaching_ambulances.append({
                                'id': vehicle,
                                'lane': lane,
                                'distance': distance_to_junction
                            })
            except Exception as e:
                print(f"Warning in lane {lane}: {e}")
                continue

        return approaching_ambulances

    def get_required_phase_for_ambulance(self, lane):
        """Map lane to correct TL phase"""
        phase_mapping = {
            "N2J_0": 0,
            "S2J_0": 0,
            "E2J_0": 2,
            "W2J_0": 2
        }
        return phase_mapping.get(lane, 0)

    def activate_emergency_priority(self, required_phase, lane, vehicle_id):
        """Switch to green corridor & log details"""
        if not self.emergency_active:
            print(f"🚨 EMERGENCY: Turning GREEN for {lane} (phase {required_phase})")
            self.emergency_active = True
            self.active_lane = lane
             

        traci.trafficlight.setPhase(self.junction_id, required_phase)
        traci.trafficlight.setPhaseDuration(self.junction_id, 5)

        # Log ambulance speed and distance
        speed = traci.vehicle.getSpeed(vehicle_id)
        dist = traci.vehicle.getDistance(vehicle_id)
        print(f"🚑 Ambulance {vehicle_id} | Speed: {speed:.2f} m/s | Distance: {dist:.2f} m")

    def deactivate_emergency_priority(self):
        """Restore normal lights after ambulance passes"""
        if self.emergency_active:
            print("✅ Ambulance passed. Restoring normal lights.")
            traci.trafficlight.setProgram(self.junction_id, self.normal_program)
            self.emergency_active = False
            self.active_lane = None
            self.siren_manager.stop()

    def step(self):
        ambulances = self.detect_ambulance()

        if ambulances:
            closest = min(ambulances, key=lambda x: x['distance'])
            lane = closest['lane']
            phase = self.get_required_phase_for_ambulance(lane)
            self.activate_emergency_priority(phase, lane, closest['id'])
        else:
            if self.emergency_active:
                self.deactivate_emergency_priority()


def run_simulation():
    traci.start(["sumo-gui", "-c", "simulation.sumocfg"])
    siren_manager = SirenManager("siren.wav")
    controller = AmbulancePriorityController("J0", siren_manager)

    step = 0
    while step < 3600:
        traci.simulationStep()
        controller.step()
        step += 1

    traci.close()


if __name__ == "__main__":
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("Please declare environment variable 'SUMO_HOME'")

    run_simulation()


