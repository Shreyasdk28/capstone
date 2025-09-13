import traci
import time
import subprocess
import sys

def run_simulation():
    # Start SUMO with TraCI
    sumo_binary = "sumo-gui" if "-gui" in sys.argv else "sumo"
    
    sumo_cmd = [
        sumo_binary,
        "-c", "highway.sumocfg",
        "--tripinfo-output", "tripinfo.xml",
        "--waiting-time-memory", "1000"
    ]
    
    traci.start(sumo_cmd)
    
    # Traffic light phases
    phases = [
        traci.trafficlight.Phase(30, "GGGrrrGGGrrr"),  # Green for main road
        traci.trafficlight.Phase(3,  "yyyrrryyyrrr"),  # Yellow for main road
        traci.trafficlight.Phase(30, "rrrGGGrrrGGG"),  # Green for main road (opposite)
        traci.trafficlight.Phase(3,  "rrryyyrrryyy")   # Yellow for main road (opposite)
    ]
    
    # Set traffic light programs for both junctions
    tl_logic_j1 = traci.trafficlight.Logic("0", 0, 0, phases)
    tl_logic_j2 = traci.trafficlight.Logic("0", 0, 0, phases)
    
    traci.trafficlight.setCompleteRedYellowGreenDefinition("J1", tl_logic_j1)
    traci.trafficlight.setCompleteRedYellowGreenDefinition("J2", tl_logic_j2)
    
    print("Simulation started with 2 traffic signals on the highway")
    print("J1 and J2 are traffic light junctions")
    
    # Main simulation loop
    step = 0
    while step < 3600:  # Run for 1 hour simulation time
        traci.simulationStep()
        step += 1
        
        # Print traffic light states every 30 seconds
        if step % 300 == 0:
            print(f"\nTime: {step}s")
            print(f"J1 state: {traci.trafficlight.getRedYellowGreenState('J1')}")
            print(f"J2 state: {traci.trafficlight.getRedYellowGreenState('J2')}")
            
            # Get vehicle counts
            vehicles_j1 = traci.edge.getLastStepVehicleNumber("highway_0")
            vehicles_j2 = traci.edge.getLastStepVehicleNumber("highway_1")
            print(f"Vehicles approaching J1: {vehicles_j1}")
            print(f"Vehicles approaching J2: {vehicles_j2}")
        
        # Optional: Dynamic traffic light control based on traffic
        if step % 600 == 0:  # Every 10 minutes
            adjust_traffic_lights_based_on_traffic()
    
    traci.close()
    print("Simulation completed")

def adjust_traffic_lights_based_on_traffic():
    """Adjust traffic light timing based on current traffic conditions"""
    # Get vehicle counts on approaches
    vehicles_j1 = traci.edge.getLastStepVehicleNumber("highway_0")
    vehicles_j2 = traci.edge.getLastStepVehicleNumber("highway_1")
    
    # Simple adaptive control: extend green time if many vehicles
    if vehicles_j1 > 20:
        # Get current program and modify phase duration
        current_phase_j1 = traci.trafficlight.getPhase("J1")
        if current_phase_j1 == 0:  # If in green phase for main road
            traci.trafficlight.setPhaseDuration("J1", 40)  # Extend green time
    
    if vehicles_j2 > 20:
        current_phase_j2 = traci.trafficlight.getPhase("J2")
        if current_phase_j2 == 0:
            traci.trafficlight.setPhaseDuration("J2", 40)

def create_three_signal_variant():
    """Alternative function for 3 traffic signals"""
    # This would require modifying the network to have 3 signalized junctions
    pass

if __name__ == "__main__":
    try:
        run_simulation()
    except traci.exceptions.FatalTraCIError:
        print("TraCI connection closed")
    except Exception as e:
        print(f"Error: {e}")