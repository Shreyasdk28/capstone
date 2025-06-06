//
// Copyright (C) 2004 OpenSim Ltd.
// Copyright (C) 2000 Institut fuer Telematik, Universitaet Karlsruhe
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//

package inet.applications.udpapp;

import inet.common.SimpleModule;
import inet.applications.contract.IApp;

//
// Consumes and prints packets received from the ~Udp module.
//
simple UdpSink extends SimpleModule like IApp
{
    parameters:
        @class(UdpSink);
        string interfaceTableModule;   // The path to the InterfaceTable module
        double startTime @unit(s) = default(0s); // Application start time
        double stopTime @unit(s) = default(-1s);  // Time of finishing receiving
        int localPort; // Local port
        bool receiveBroadcast = default(false); // If true, makes the socket receive broadcast packets
        string multicastGroup = default(""); // If non-empty, makes the socket receive multicast packets sent to that group
        string multicastSources = default(""); // If non-empty, then the socket receives multicast packets from those sources only

        @display("i=block/sink");
        @lifecycleSupport;
        double stopOperationExtraTime @unit(s) = default(-1s);    // Extra time after lifecycle stop operation finished
        double stopOperationTimeout @unit(s) = default(2s);    // Timeout value for lifecycle stop operation
        @signal[packetReceived](type=inet::Packet);
        @statistic[packetReceived](title="packets received"; source=packetReceived; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
        @statistic[throughput](title="throughput"; unit=bps; source="throughput(packetReceived)"; record=vector);
        @statistic[endToEndDelay](title="end-to-end delay"; source="dataAge(packetReceived)"; unit=s; record=histogram,vector; interpolationmode=none);
        @statistic[rcvdPkSeqNo](title="received packet sequence number"; source="appPkSeqNo(packetReceived)"; record=vector; interpolationmode=none);

    gates:
        input socketIn @labels(UdpCommand/up);
        output socketOut @labels(UdpCommand/down);
}

