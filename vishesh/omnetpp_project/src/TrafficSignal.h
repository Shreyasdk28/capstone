#ifndef TRAFFICSIGNAL_H
#define TRAFFICSIGNAL_H

#include <omnetpp.h>
#include "VANETMessages_m.h"

using namespace omnetpp;

class TrafficSignal : public cSimpleModule {
protected:
    // Configuration parameters
    double positionX;
    double positionY;
    double transmissionRange;
    double signalChangeInterval;
    
    // Current signal state
    std::string currentState;  // "RED", "YELLOW", "GREEN"
    
    // Timer for signal changes
    cMessage *signalChangeTimer;
    
    // Statistics
    simsignal_t messagesSentSignal;
    
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
    
    // Helper functions
    void broadcastSignalState();
    void changeSignalState();
    
public:
    TrafficSignal();
    virtual ~TrafficSignal();
};

#endif 