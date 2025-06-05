#include "TraCIManager.h"

Define_Module(TraCIManager);

TraCIManager::TraCIManager() {
    traci = nullptr;
}

TraCIManager::~TraCIManager() {
    delete traci;
}

void TraCIManager::initialize(int stage) {
    TraCIScenarioManager::initialize(stage);
    
    if (stage == 0) {
        // Initialize TraCI connection
        traci = new TraCICommandInterface(this, *connection, false);
        
        // Register statistics
        vehiclesCreatedSignal = registerSignal("vehiclesCreated");
        vehiclesRemovedSignal = registerSignal("vehiclesRemoved");
    }
}

void TraCIManager::handleMessage(cMessage *msg) {
    if (msg->isSelfMessage()) {
        handleSelfMsg(msg);
    } else {
        handleTraCIMsg(msg);
    }
}

void TraCIManager::handleSelfMsg(cMessage *msg) {
    TraCIScenarioManager::handleSelfMsg(msg);
}

void TraCIManager::handleTraCIMsg(cMessage *msg) {
    // Handle TraCI specific messages
    if (std::string(msg->getName()) == "vehicleAdd") {
        // New vehicle added in SUMO
        emit(vehiclesCreatedSignal, 1);
    } else if (std::string(msg->getName()) == "vehicleRemove") {
        // Vehicle removed from SUMO
        emit(vehiclesRemovedSignal, 1);
    }
    delete msg;
}

void TraCIManager::finish() {
    TraCIScenarioManager::finish();
} 