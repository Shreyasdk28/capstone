#include "TrafficServer.h"

Define_Module(TrafficServer);

TrafficServer::TrafficServer() {
}

TrafficServer::~TrafficServer() {
}

void TrafficServer::initialize() {
    serverPort = par("serverPort");
    
    // Register statistics
    messagesReceivedSignal = registerSignal("messagesReceived");
    messagesProcessedSignal = registerSignal("messagesProcessed");
    
    EV << "TrafficServer initialized on port " << serverPort << endl;
}

void TrafficServer::handleMessage(cMessage *msg) {
    if (VANETMessage *vanetMsg = dynamic_cast<VANETMessage *>(msg)) {
        processTrafficData(vanetMsg);
        emit(messagesReceivedSignal, 1);
    }
    delete msg;
}

void TrafficServer::processTrafficData(VANETMessage *msg) {
    std::string poleId = msg->getSourceId();
    std::map<std::string, int> data;
    
    // Extract traffic data from message
    data["north_count"] = msg->getNorthCount();
    data["south_count"] = msg->getSouthCount();
    data["east_count"] = msg->getEastCount();
    data["west_count"] = msg->getWestCount();
    
    // Update intersection data
    updateIntersectionData(poleId, data);
    
    // Calculate optimal phase based on traffic data
    int optimalPhase = calculateOptimalPhase(data);
    
    // Send control signal back to the intersection
    sendControlSignal(poleId, optimalPhase);
    
    emit(messagesProcessedSignal, 1);
}

void TrafficServer::updateIntersectionData(const std::string& poleId, const std::map<std::string, int>& data) {
    intersectionData[poleId] = data;
}

void TrafficServer::sendControlSignal(const std::string& poleId, int phase) {
    VANETMessage *controlMsg = new VANETMessage("control");
    controlMsg->setSourceId(getId());
    controlMsg->setDestinationId(poleId);
    controlMsg->setMessageType("CONTROL");
    controlMsg->setPhase(phase);
    
    // Send to the specific intersection
    send(controlMsg, "gate$o");
}

int TrafficServer::calculateOptimalPhase(const std::map<std::string, int>& data) {
    // Implement the same logic as in your Python edge_template.py
    int north_count = data.at("north_count");
    int south_count = data.at("south_count");
    int east_count = data.at("east_count");
    int west_count = data.at("west_count");
    
    int max_vehicles_ns = std::max(north_count, south_count);
    int max_vehicles_ew = std::max(east_count, west_count);
    
    if (max_vehicles_ns > max_vehicles_ew) {
        return 0;  // N-S green
    } else if (max_vehicles_ew > max_vehicles_ns) {
        return 2;  // E-W green
    } else {
        return 0;  // Default to N-S green
    }
}

void TrafficServer::finish() {
    recordScalar("messagesReceived", messagesReceivedSignal);
    recordScalar("messagesProcessed", messagesProcessedSignal);
} 