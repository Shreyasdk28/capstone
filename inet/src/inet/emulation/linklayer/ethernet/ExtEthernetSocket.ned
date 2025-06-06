//
// Copyright (C) 2020 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.emulation.linklayer.ethernet;

import inet.common.SimpleModule;

//
// Provides a bidirectional connection to an Ethernet socket of the
// host computer which is running the simulation. It writes the packets that arrive
// on `upperLayerIn` gate to the specified real socket and sends out packets
// that arrive from the real socket on the `upperLayerOut` gate.
//
// The CAP_NET_RAW privilege is required for using `ExtEthernetSocket`.
//
// The next commands add this privilege to opp_run, so all simulations
// have the CAP_NET_RAW privilege, and all simulations run with this privilege!
// This is dangerous because it enables a thousand other things for all
// running simulations; it becomes a big security hole.
//
// $> sudo setcap cap_net_raw+ep /${your-omnetpp-root}/bin/opp_run_release
// $> sudo setcap cap_net_raw+ep /${your-omnetpp-root}/bin/opp_run_dbg
//
// To remove extra privileges after running the simulation, use the following commands:
//
// $> sudo setcap -r /${your-omnetpp-root}/bin/opp_run_release
// $> sudo setcap -r /${your-omnetpp-root}/bin/opp_run_dbg
//
simple ExtEthernetSocket extends SimpleModule
{
    parameters:
        @class(ExtEthernetSocket);
        string device; // Name of an existing real Ethernet device
        string namespace = default("");
        string packetNameFormat = default("Ext-%p-%t-%n"); // Name of received packets
        @display("i=block/rxtx");
        @signal[packetSentToUpper](type=Packet);
        @signal[packetReceivedFromUpper](type=Packet);
        @signal[packetSent](type=Packet);
        @signal[packetReceived](type=Packet);
        @statistic[packetSentFromUpper](title="packets sent to higher layer"; source=packetSentToUpper; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
        @statistic[packetReceivedFromUpper](title="packets received from higher layer"; source=packetReceivedFromUpper; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
        @statistic[packetSent](title="packets sent"; source=packetSent; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
        @statistic[packetReceived](title="packets received"; source=packetReceived; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
    gates:
        input upperLayerIn;
        output upperLayerOut @loose;
}
