//
// Copyright (C) 2020 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.applications.ieee8022;

import inet.common.SimpleModule;

//
// Provides IEEE 802.2 LLC socket handling for generic applications.
//
simple Ieee8022LlcSocketIo extends SimpleModule
{
    parameters:
        @class(Ieee8022LlcSocketIo);
        string interfaceTableModule;
        string interface = default("");
        string localAddress = default("");
        string remoteAddress = default("");
        int localSap = default(-1);
        int remoteSap = default(-1);
        double stopOperationExtraTime @unit(s) = default(-1s);    // Extra time after lifecycle stop operation finishes
        double stopOperationTimeout @unit(s) = default(2s);    // Timeout value for lifecycle stop operation
        @lifecycleSupport();
        @display("i=block/socket");
        @signal[packetSent](type=inet::Packet);
        @signal[packetReceived](type=inet::Packet);
        @statistic[packetSent](title="packets sent"; source=packetSent; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
        @statistic[packetReceived](title="packets received"; source=packetReceived; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
    gates:
        input trafficIn;
        output trafficOut;
        input socketIn;
        output socketOut;
}
