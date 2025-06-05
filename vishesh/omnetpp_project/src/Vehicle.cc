#include "Vehicle.h"
#include "TraCIManager.h"

Define_Module(Vehicle);

Vehicle::Vehicle() {
    beaconTimer = nullptr;
    updateTimer = nullptr;
    mobility = nullptr;
}

Vehicle::~Vehicle() {
    cancelAndDelete(beaconTimer);
    cancelAndDelete(updateTimer);
}

void Vehicle::initialize() {
    // Initialize TraCI mobility
    mobility = dynamic_cast<TraCIMobility*>(getModuleByPath(".mobility"));
    if (!mobility) {
        throw cRuntimeError("Could not find TraCIMobility module");
    }
    
    // Initialize parameters
    beaconInterval = par("beaconInterval");
    transmissionRange = par("transmissionRange");
    
    // Get initial position from SUMO
    auto pos = mobility->getPositionAt(simTime());
    positionX = pos.x;
    positionY = pos.y;
    speed = mobility->getSpeed();
    
    // Initialize statistics
    messagesSentSignal = registerSignal("messagesSent");
    messagesReceivedSignal = registerSignal("messagesReceived");
    distanceTraveledSignal = registerSignal("distanceTraveled");
    
    // Schedule timers
    beaconTimer = new cMessage("beaconTimer");
    scheduleAt(simTime() + beaconInterval, beaconTimer);
    
    updateTimer = new cMessage("updateTimer");
    scheduleAt(simTime() + 0.1, updateTimer);  // Update position every 100ms
}

void Vehicle::handleMessage(cMessage *msg) {
    if (msg == beaconTimer) {
        sendBeacon();
        scheduleAt(simTime() + beaconInterval, beaconTimer);
    } else if (msg == updateTimer) {
        updatePosition();
        scheduleAt(simTime() + 0.1, updateTimer);
    } else {
        VANETMessage *vanetMsg = check_and_cast<VANETMessage *>(msg);
        if (isInRange(vanetMsg->getPositionX(), vanetMsg->getPositionY())) {
            processVANETMessage(vanetMsg);
        }
        delete msg;
    }
}

void Vehicle::updatePosition() {
    auto oldX = positionX;
    auto oldY = positionY;
    
    // Update position and speed from SUMO
    auto pos = mobility->getPositionAt(simTime());
    positionX = pos.x;
    positionY = pos.y;
    speed = mobility->getSpeed();
    
    // Calculate distance traveled
    double distance = sqrt(pow(positionX - oldX, 2) + pow(positionY - oldY, 2));
    emit(distanceTraveledSignal, distance);
}

void Vehicle::sendBeacon() {
    BeaconMessage *beacon = new BeaconMessage("beacon");
    beacon->setSourceId(getId());
    beacon->setDestinationId(-1);  // Broadcast
    beacon->setMessageType("BEACON");
    beacon->setPositionX(positionX);
    beacon->setPositionY(positionY);
    beacon->setSpeed(speed);
    beacon->setTimestamp(simTime().dbl());
    
    send(beacon, "gate$o");
    emit(messagesSentSignal, 1);
}

void Vehicle::processVANETMessage(VANETMessage *msg) {
    EV << "Vehicle " << getSumoId() << " received message from Vehicle " << msg->getSourceId() << endl;
    emit(messagesReceivedSignal, 1);
    
    if (strcmp(msg->getMessageType(), "EMERGENCY") == 0) {
        EmergencyMessage *emergencyMsg = check_and_cast<EmergencyMessage *>(msg);
        EV << "Emergency message received: " << emergencyMsg->getEmergencyType() << endl;
        
        // React to emergency (e.g., slow down, change lane)
        auto* traci = dynamic_cast<TraCIManager*>(getModuleByPath("^.manager"))->getTraCI();
        std::string sumoId = mobility->getExternalId();
        TraCICommandInterface::Vehicle vehicle = traci->vehicle(sumoId);
        vehicle.setSpeed(vehicle.getSpeed() * 0.5);  // Slow down to 50% of current speed
    }
}

bool Vehicle::isInRange(double senderX, double senderY) {
    double distance = sqrt(pow(positionX - senderX, 2) + pow(positionY - senderY, 2));
    return distance <= transmissionRange;
}

void Vehicle::finish() {
    recordScalar("messagesSent", messagesSentSignal);
    recordScalar("messagesReceived", messagesReceivedSignal);
    recordScalar("distanceTraveled", distanceTraveledSignal);
} 