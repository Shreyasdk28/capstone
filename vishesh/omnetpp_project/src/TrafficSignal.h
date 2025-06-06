#ifndef TRAFFICSIGNAL_H
#define TRAFFICSIGNAL_H

#include <omnetpp.h>
#include "VANETMessages_m.h"
#include "veins/modules/mobility/traci/TraCIMobility.h"
#include "veins/modules/mobility/traci/TraCICommandInterface.h"

using namespace omnetpp;
using namespace veins;

class TrafficSignal : public cSimpleModule {
protected:
    // TraCI mobility
    TraCIMobility* mobility;
    std::string sumoId;
    
    // Configuration parameters
    double transmissionRange;
    double signalChangeInterval;
    double updateInterval;
    std::string poleId;
    
    // Current state
    int currentPhase;
    std::map<std::string, int> approachCounts;
    
    // Statistics
    simsignal_t messagesSentSignal;
    simsignal_t messagesReceivedSignal;
    
    // Timers
    cMessage *updateTimer;
    cMessage *phaseTimer;
    
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
    
    // Helper functions
    void updateTrafficData();
    void sendTrafficData();
    void processControlMessage(TrafficControlMessage *msg);
    void setTrafficLightPhase(int phase);
    
public:
    TrafficSignal();
    virtual ~TrafficSignal();
    
    // TraCI utility functions
    void setSumoId(const std::string& id) { sumoId = id; }
    const std::string& getSumoId() const { return sumoId; }
};

#endif 