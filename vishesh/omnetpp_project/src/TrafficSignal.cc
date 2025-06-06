#include "TrafficSignal.h"
#include "TraCIManager.h"

Define_Module(TrafficSignal);

TrafficSignal::TrafficSignal() {
    updateTimer = nullptr;
    phaseTimer = nullptr;
    mobility = nullptr;
}

TrafficSignal::~TrafficSignal() {
    cancelAndDelete(updateTimer);
    cancelAndDelete(phaseTimer);
}

void TrafficSignal::initialize() {
    // Initialize TraCI mobility
    mobility = dynamic_cast<TraCIMobility*>(getModuleByPath(".mobility"));
    if (!mobility) {
        throw cRuntimeError("Could not find TraCIMobility module");
    }
    
    // Initialize parameters
    transmissionRange = par("transmissionRange");
    signalChangeInterval = par("signalChangeInterval");
    updateInterval = par("updateInterval");
    poleId = par("poleId").stringValue();
    
    // Initialize state
    currentPhase = 0;
    
    // Initialize statistics
    messagesSentSignal = registerSignal("messagesSent");
    messagesReceivedSignal = registerSignal("messagesReceived");
    
    // Schedule timers
    updateTimer = new cMessage("updateTimer");
    scheduleAt(simTime() + updateInterval, updateTimer);
    
    phaseTimer = new cMessage("phaseTimer");
    scheduleAt(simTime() + signalChangeInterval, phaseTimer);
    
    EV << "TrafficSignal " << poleId << " initialized" << endl;
}

void TrafficSignal::handleMessage(cMessage *msg) {
    if (msg == updateTimer) {
        updateTrafficData();
        sendTrafficData();
        scheduleAt(simTime() + updateInterval, updateTimer);
    } else if (msg == phaseTimer) {
        // Phase timer expired, can change phase if needed
        scheduleAt(simTime() + signalChangeInterval, phaseTimer);
    } else if (TrafficControlMessage *controlMsg = dynamic_cast<TrafficControlMessage *>(msg)) {
        processControlMessage(controlMsg);
        delete msg;
    }
}

void TrafficSignal::updateTrafficData() {
    auto* traci = dynamic_cast<TraCIManager*>(getModuleByPath("^.manager"))->getTraCI();
    
    // Get vehicle counts from SUMO detectors
    approachCounts["north"] = traci->lanearea.getLastStepVehicleNumber("area_north_approach_0_350");
    approachCounts["south"] = traci->lanearea.getLastStepVehicleNumber("area_south_approach_0_350");
    approachCounts["east"] = traci->lanearea.getLastStepVehicleNumber("area_east_approach_0_350");
    approachCounts["west"] = traci->lanearea.getLastStepVehicleNumber("area_west_approach_0_350");
}

void TrafficSignal::sendTrafficData() {
    TrafficDataMessage *dataMsg = new TrafficDataMessage("trafficData");
    dataMsg->setSourceId(getId());
    dataMsg->setDestinationId(-1);  // Broadcast
    dataMsg->setMessageType("TRAFFIC_DATA");
    dataMsg->setNorthCount(approachCounts["north"]);
    dataMsg->setSouthCount(approachCounts["south"]);
    dataMsg->setEastCount(approachCounts["east"]);
    dataMsg->setWestCount(approachCounts["west"]);
    dataMsg->setCurrentPhase(currentPhase);
    
    send(dataMsg, "gate$o");
    emit(messagesSentSignal, 1);
}

void TrafficSignal::processControlMessage(TrafficControlMessage *msg) {
    if (msg->getPhase() != currentPhase) {
        setTrafficLightPhase(msg->getPhase());
    }
    emit(messagesReceivedSignal, 1);
}

void TrafficSignal::setTrafficLightPhase(int phase) {
    auto* traci = dynamic_cast<TraCIManager*>(getModuleByPath("^.manager"))->getTraCI();
    traci->trafficlight.setPhase("center", phase);
    currentPhase = phase;
}

void TrafficSignal::finish() {
    recordScalar("messagesSent", messagesSentSignal);
    recordScalar("messagesReceived", messagesReceivedSignal);
} 