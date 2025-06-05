#ifndef VEHICLE_H
#define VEHICLE_H

#include <omnetpp.h>
#include "VANETMessages_m.h"
#include "veins/modules/mobility/traci/TraCIMobility.h"
#include "veins/modules/mobility/traci/TraCICommandInterface.h"

using namespace omnetpp;
using namespace veins;

class Vehicle : public cSimpleModule {
protected:
    // TraCI mobility
    TraCIMobility* mobility;
    std::string sumoId;
    
    // Configuration parameters
    double beaconInterval;
    double transmissionRange;
    double speed;
    double positionX;
    double positionY;
    
    // Statistics
    simsignal_t messagesSentSignal;
    simsignal_t messagesReceivedSignal;
    simsignal_t distanceTraveledSignal;
    
    // Timers
    cMessage *beaconTimer;
    cMessage *updateTimer;
    
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
    
    // Helper functions
    void sendBeacon();
    void processVANETMessage(VANETMessage *msg);
    bool isInRange(double senderX, double senderY);
    void updatePosition();
    
public:
    Vehicle();
    virtual ~Vehicle();
    
    // TraCI utility functions
    void setSumoId(const std::string& id) { sumoId = id; }
    const std::string& getSumoId() const { return sumoId; }
};

#endif 