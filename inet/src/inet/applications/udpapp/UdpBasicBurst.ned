//
// Copyright (C) 2006 Alfonso Ariza
// Copyright (C) 2004 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.applications.udpapp;

import inet.common.SimpleModule;
import inet.applications.contract.IApp;

//
// Sends UDP packets to the given IP address(es) in bursts, or acts as a
// packet sink. Compatible with both IPv4 (~Ipv4) and IPv6 (~Ipv6).
//
// <b>Addressing:</b>
//
// The `destAddresses` parameter can contain zero, one, or more destination
// addresses, separated by spaces. If there is no destination address given,
// the module will act as a packet sink. If there are more than one addresses,
// one of them is randomly chosen, either for the whole simulation run,
// or for each burst, or for each packet, depending on the value of the
// `chooseDestAddrMode` parameter. The `destAddrRNG` parameter controls which
// (local) RNG is used for randomized address selection.
// The own addresses will be ignored.
//
// An address may be given in the dotted decimal notation or with the module
// name. (The `L3AddressResolver` class is used to resolve the address.)
// You can use the "Broadcast" string as an address for sending broadcast messages.
//
// INET also defines several NED functions that can be useful:
//    - `moduleListByPath("pattern",...)`:
//          Returns a space-separated list of the module names.
//          All modules whose `getFullPath()` matches one of the pattern parameters will get included.
//          The patterns may contain wildcards in the same syntax as in ini files.
//          See `cTopology::extractByModulePath()` function
//          example: destaddresses = moduleListByPath("**.host[*]", "**.fixhost[*]")
//    - `moduleListByNedType("fully.qualified.ned.type",...)`:
//          Returns a space-separated list of the module names with the given NED type(s).
//          All modules whose `getNedTypeName()` is listed in the given parameters will get included.
//          The NED type name is fully qualified.
//          See `cTopology::extractByNedTypeName()` function
//          example: destaddresses = moduleListByNedType(`inet.node.inet.StandardHost`)
//
// The peer can be `UdpSink` or another `UdpBasicBurst`.
//
// <b>Bursts:</b>
//
// The first burst starts at `startTime`. Bursts start by immediately sending
// a packet; subsequent packets are sent at `sendInterval` intervals. The
// `sendInterval` parameter can be a random value, e.g. exponential(10ms).
// A constant interval with jitter can be specified as 1s + uniform(-0.01s,0.01s)
// or uniform(0.99s,1.01s). The length of the burst is controlled by the
// `burstDuration` parameter. (Note that if `sendInterval` is greater than
// `burstDuration`, the burst will consist of one packet only.) The time between
// burst is the `sleepDuration` parameter; this can be zero (zero is not
// allowed for `sendInterval`.) The zero `burstDuration` is implemented as infinity.
//
// The zero value in `burstDuration` or `sendInterval` parameters generates a runtime error.
// The `sleepDuration` parameter accepts a zero value.
//
// <b>Packets</b>
//
// Packet length is controlled by the `messageLength` parameter.
//
// The module adds two parameters to packets before sending:
//  - `sourceID`: source module ID
//  - `msgId`: incremented by 1 after send any packet.
// When received packet has these parameters, the module checks the order of received packets.
//
// <b>Operation as sink</b>
//
// When `destAddresses` parameter is empty, the module receives packets and makes statistics only.
//
// <b>Statistics</b>
//
// Statistics are collected on outgoing packets:
//  - `packetSent`: packet object
//
// Statistics are collected on incoming packets:
//  - `outOfOrderPk`: statistics of out of order packets.
//        The packet is out of order when it has `msgId` and `sourceId` parameters, and the module
//        received a bigger `msgId` from the same `sourceID`.
//  - `dropPk`: statistics of dropped packets.
//        The packet is dropped when not an out-of-order packet and delay time is larger than
//        the `delayLimit` parameter. The delayLimit = 0 is infinity.
//  - `packetReceived`: statistics of not dropped, not out-of-order packets.
//  - `endToEndDelay`: end to end delay statistics of not dropped, not out-of-order packets.
//
simple UdpBasicBurst extends SimpleModule like IApp
{
    parameters:
        @class(UdpBasicBurst);
        string interfaceTableModule;   // The path to the InterfaceTable module
        string destAddresses; // Space-separated list of destination IP addresses, can be empty;
                              // see module description for possibilities
        bool excludeLocalDestAddresses = default(true);     // Excluding local addresses from destAddresses
        string chooseDestAddrMode @enum("once","perBurst","perSend"); // When to change the destination address
        int destAddrRNG = default(0); // Random generator ID for selecting a destination address
        int localPort = default(-1);  // Local UDP port number (-1: use ephemeral port)
        int destPort; // Remote UDP port number
        double startTime @unit(s) = default(1s); // Application start time (start of the first burst)
        double stopTime @unit(s) = default(-1s); // Application stop time (no packets are sent after this time); a negative or -1 means no limit
        volatile int messageLength @unit(B); // Length of messages to generate, in bytes
        volatile double burstDuration @unit(s); // Burst duration time (zero not allowed)
        volatile double sleepDuration @unit(s); // Time between bursts (zero allowed)
        volatile double sendInterval @unit(s); // Time between messages during bursts; usually a random value, e.g., 0.1s + uniform(-0.001s,0.001s); zero not allowed
        double delayLimit @unit(s) = default(0s); // Maximum accepted delay for a packet; packets with a bigger delay are discarded (dropped), zero value means no limit
        int timeToLive = default(-1); // If not -1, set the TTL (IPv4) or Hop Limit (IPv6) field of sent packets to this value
        bool dontFragment = default(false); // If true, asks IP to not fragment the message during routing
        int dscp = default(-1); // If not -1, set the DSCP field (on IPv4/IPv6) of sent packets to this value
        int tos = default(-1); // If not -1, set the Type Of Service (IPv4) / Traffic Class (IPv6) field of sent packets to this value
        @display("i=block/app");
        @lifecycleSupport;
        double stopOperationExtraTime @unit(s) = default(-1s);    // Extra time after lifecycle stop operation finished
        double stopOperationTimeout @unit(s) = default(2s);    // Timeout value for lifecycle stop operation
        @signal[packetSent](type=inet::Packet);
        @signal[packetReceived](type=inet::Packet);
        @signal[packetDropped](type=inet::Packet);
        @signal[outOfOrderPk](type=inet::Packet);
        @statistic[packetSent](title="packets sent"; source=packetSent; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
        @statistic[packetReceived](title="packets received"; source=packetReceived; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
        @statistic[dropPk](title="packets dropped"; source=packetDropped; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
        @statistic[outOfOrderPk](title="packets received out of order"; source=outOfOrderPk; record=count,"sum(packetBytes)","vector(packetBytes)"; interpolationmode=none);
        @statistic[endToEndDelay](title="delay"; source="dataAge(packetReceived)"; unit=s; record=histogram,vector; interpolationmode=none);
    gates:
        input socketIn @labels(UdpCommand/up);
        output socketOut @labels(UdpCommand/down);
}

