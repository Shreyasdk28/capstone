#ifndef TRAFFICSERVER_H
#define TRAFFICSERVER_H

#include <omnetpp.h>
#include <map>
#include <string>
#include "VANETMessages_m.h"

using namespace omnetpp;

class TrafficServer : public cSimpleModule {
protected:
    // Server configuration
    int serverPort;
    std::map<std::string, std::map<std::string, int>> intersectionData;  // pole_id -> {north_count, south_count, etc.}
    
    // Statistics
    simsignal_t messagesReceivedSignal;
    simsignal_t messagesProcessedSignal;
    
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
    
    // Helper functions
    void processTrafficData(VANETMessage *msg);
    void updateIntersectionData(const std::string& poleId, const std::map<std::string, int>& data);
    void sendControlSignal(const std::string& poleId, int phase);
    
public:
    TrafficServer();
    virtual ~TrafficServer();
};

#endif 