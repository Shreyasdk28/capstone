#ifndef TRACIMANAGER_H
#define TRACIMANAGER_H

#include <omnetpp.h>
#include "veins/modules/mobility/traci/TraCIScenarioManager.h"
#include "veins/modules/mobility/traci/TraCICommandInterface.h"

using namespace omnetpp;
using namespace veins;

class TraCIManager : public TraCIScenarioManager {
protected:
    // TraCI connection
    TraCICommandInterface *traci;
    
    // Statistics
    simsignal_t vehiclesCreatedSignal;
    simsignal_t vehiclesRemovedSignal;
    
    virtual void initialize(int stage) override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
    
    // TraCI event handlers
    virtual void handleSelfMsg(cMessage *msg) override;
    virtual void handleTraCIMsg(cMessage *msg);
    
public:
    TraCIManager();
    virtual ~TraCIManager();
    
    // Utility functions
    TraCICommandInterface* getTraCI() { return traci; }
    
    virtual int numInitStages() const override { return 2; }
};

#endif 