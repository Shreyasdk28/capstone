#include "VehicleApp.h"
#include "veins/modules/messages/BaseFrame1609_4_m.h"
#include "veins/modules/application/traci/TraCIDemo11pMessage_m.h"
#include "veins/modules/mac/ieee80211p/Mac1609_4.h"
#include "veins/base/utils/FindModule.h"
#include "veins/modules/utility/Consts80211p.h"

Define_Module(VehicleApp);

const simsignal_t VehicleApp::packetDropSignal = registerSignal("packetDrop");
const simsignal_t VehicleApp::latencySignal = registerSignal("latency");
const simsignal_t VehicleApp::rttSignal = registerSignal("rtt");

void VehicleApp::initialize(int stage) {
    DemoBaseApplLayer::initialize(stage);
    if (stage == 0) {
        // Initialize metrics
        packetsReceived = 0;
        packetsDropped = 0;
        sentMessage = false;
        currentSubscribedServiceId = -1;
        
        // Get TraCI interfaces
        mobility = TraCIMobilityAccess().get(getParentModule());
        traci = mobility->getCommandInterface();
        traciVehicle = mobility->getVehicleCommandInterface();
        
        // Schedule periodic message sending
        scheduleAt(simTime() + 2 + uniform(0.01, 0.2), new cMessage("sendV2V"));
    }
}

void VehicleApp::finish() {
    DemoBaseApplLayer::finish();
    
    // Record final statistics
    recordScalar("packetsReceived", packetsReceived);
    recordScalar("packetsDropped", packetsDropped);
}

void VehicleApp::handleSelfMsg(cMessage* msg) {
    if (msg->isName("sendV2V")) {
        sendV2VMessage();
        scheduleAt(simTime() + 1, msg);
    }
    else {
        DemoBaseApplLayer::handleSelfMsg(msg);
    }
}

void VehicleApp::sendV2VMessage() {
    BaseFrame1609_4* wsm = new BaseFrame1609_4("V2V");
    populateWSM(wsm);
    
    // Add message specific data
    wsm->setChannelNumber(static_cast<int>(Channel::cch));  // Using Channel::cch for CCH in Veins 5.3.1
    wsm->setPsid(0);
    
    // Set user priority using header field
    auto userPriority = 3;  // Priority level (0-7)
    wsm->setUserPriority(userPriority);
    
    // Set timestamp and recipient
    wsm->setTimestamp(simTime());
    wsm->setRecipientAddress(LAddress::L2BROADCAST());
    
    // Store timestamp for RTT calculation
    messageTimestamps[wsm->getId()] = simTime();
    lastSentMessage = simTime();
    
    // Send down to lower layer
    sendDown(wsm);
}

void VehicleApp::onWSM(BaseFrame1609_4* wsm) {
    // Process received message
    processReceivedMessage(wsm);
    updateMetrics(wsm);
}

void VehicleApp::processReceivedMessage(BaseFrame1609_4* wsm) {
    // Update received packets counter
    packetsReceived++;
    
    // Calculate latency
    simtime_t latency = simTime() - wsm->getTimestamp();
    emit(latencySignal, latency);
    
    // Calculate RTT if this is a response to our message
    auto it = messageTimestamps.find(wsm->getId());
    if (it != messageTimestamps.end()) {
        simtime_t rtt = simTime() - it->second;
        emit(rttSignal, rtt);
        messageTimestamps.erase(it);
    }
}

void VehicleApp::updateMetrics(BaseFrame1609_4* wsm) {
    // Check for packet drops (simplified)
    if (uniform(0, 1) < 0.1) { // 10% packet drop rate for simulation
        packetsDropped++;
        emit(packetDropSignal, 1);
    }
}

void VehicleApp::handlePositionUpdate(cObject* obj) {
    DemoBaseApplLayer::handlePositionUpdate(obj);
    
    // Update position-based logic here if needed
}

void VehicleApp::onWSA(DemoServiceAdvertisment* wsa) {
    // Handle service advertisements if needed
}

void VehicleApp::onBSM(DemoSafetyMessage* bsm) {
    // Handle received beacon safety messages
    // You can implement your VANET logic here
}
