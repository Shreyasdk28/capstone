#ifndef __VANET_VEHICLEAPP_H_
#define __VANET_VEHICLEAPP_H_

#include <omnetpp.h>
#include "veins/modules/application/ieee80211p/DemoBaseApplLayer.h"
#include "veins/modules/mobility/traci/TraCIMobility.h"
#include "veins/modules/mobility/traci/TraCICommandInterface.h"
#include "veins/modules/mac/ieee80211p/Mac1609_4.h"

using namespace omnetpp;
using namespace veins;

class VehicleApp : public DemoBaseApplLayer {
public:
    void initialize(int stage) override;
    void finish() override;

protected:
    // Metrics collection
    simtime_t lastSentMessage;
    long packetsReceived;
    long packetsDropped;
    std::map<long, simtime_t> messageTimestamps;
    
    // Handlers for messages
    void handleSelfMsg(cMessage* msg) override;
    void handlePositionUpdate(cObject* obj) override;
    void onWSM(BaseFrame1609_4* wsm) override;
    void onWSA(DemoServiceAdvertisment* wsa) override;
    void onBSM(DemoSafetyMessage* bsm) override;

    // Custom methods for V2V communication
    void sendV2VMessage();
    void processReceivedMessage(BaseFrame1609_4* wsm);
    void updateMetrics(BaseFrame1609_4* wsm);

    // TraCI mobility
    TraCIMobility* mobility;
    TraCICommandInterface* traci;
    TraCICommandInterface::Vehicle* traciVehicle;

    // Configuration parameters
    bool sentMessage;
    static const simsignal_t packetDropSignal;
    static const simsignal_t latencySignal;
    static const simsignal_t rttSignal;

    int currentSubscribedServiceId;
    
    // Required by Veins
    int numInitStages() const override { return std::max(DemoBaseApplLayer::numInitStages(), 2); }
};

#endif
