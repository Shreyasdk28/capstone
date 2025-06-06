//
// Copyright (C) 2004 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.networklayer.ipv4;

import inet.common.SimpleModule;

//
// Module interface for IPv4 protocol implementations. Defines gates and
// parameters for modules that provide IPv4 protocol functionality. The IPv4
// protocol provides datagram routing, fragmentation, and addressing between
// network interfaces and transport layer protocols.
//
moduleinterface IIpv4
{
    parameters:
        @display("i=block/routing");
    gates:
        input transportIn @labels(Ipv4ControlInfo/down,TcpHeader,UdpHeader,SctpHeader);
        output transportOut @labels(Ipv4ControlInfo/up,TcpHeader,UdpHeader,SctpHeader);
        input queueIn @labels(Ipv4Header,ArpPacket,Ieee802Ctrl);
        output queueOut @labels(Ipv4Header,ArpPacket,Ieee802Ctrl);
}

//
// Implements the IPv4 protocol. The protocol header is represented
// by the ~Ipv4Header message class.
//
// <b>Interfacing with higher layer protocols</b>
//
// To send a packet over IPv4 from a higher layer protocol, the module should
// fill in an ~L3AddressReq object, attach it to the packet with the Packet's
// `addTag()` method, then send the packet to the ~Ipv4 module.
//
// When ~Ipv4 sends up a packet to a higher layer protocol, it will also attach
// an ~L3AddressInd to the packet, with the source and destination IPv4 addresses
// of the IPv4 datagram in which the packet arrived.
//
// ~Ipv4 can serve several higher-layer protocols. The higher layer protocols
// should call `registerProtocol()` with their gate towards the ~Ipv4 module,
// to fill up the protocol-to-gateindex map. When delivering packets to them,
// the output gate is determined from the Protocol in the IPv4 header.
//
// <b>Routing and interfacing with lower layers</b>
//
// The routing table is stored in the module ~Ipv4RoutingTable. When a datagram
// needs to be routed, ~Ipv4 queries ~Ipv4RoutingTable for the output interface
// (or "port") and next hop address of the packet. This is done by directly
// calling C++ methods (such as `findBestMatchingRoute(destAddress)`) of ~Ipv4RoutingTable.
// No message exchange with ~Ipv4RoutingTable takes place.
//
// A routed datagram will be sent to the `queueOut`, which is expected to be
// connected to ~INetworkInterface modules.
//
// Routing protocol implementations (e.g. OSPF and ISIS) can also query
// and manipulate the route table by calling ~Ipv4RoutingTable's methods in C++.
//
// <b>Working with ARP</b>
//
// Ipv4 module subscribes to `arpResolutionCompleted` and `arpResolutionFailed` signals on Arp module.
// The ~Arp module accessed via `arpOut` gate should not insert any module between ~Ipv4 and ~Arp.
// Before Ipv4 module sends down a packet to the lower layer, it asks for the `MacAddress` of the next hop from Arp via
// a method call. If the `MacAddress` is unspecified, then start address resolution via an Arp method call and
// insert the packet to a queue specified by the next hop address.
// When it receives an `arpResolutionCompleted` signal, it sends the packets from the queue of the next hop address.
// When it receives an `arpResolutionFailed` signal, it drops the packets from the queue of the next hop address.
// When the Ipv4 module receives an ARP packet from the lower layer on some `queueIn` gate,
// it sends out this packet on the `arpOut` gate. When it receives a packet on the `arpIn` gate,
// it sends out this packet on the specified `queueOut` gate.
//
// <b>Performance model, QoS</b>
//
// In its current form, ~Ipv4 contains a FIFO which queues up Ipv4 datagrams;
// datagrams are processed in order. The processing time is determined by the
// `procDelay` module parameter.
//
// The current performance model comes from the `QueueBase` C++ base class.
// If you need a more sophisticated performance model, you may change the
// module implementation (the Ipv4 class), and: (1) override the `startService()`
// method which determines the processing time for a packet, or (2) use a
// different base class.
//
// @see ~Ipv4RoutingTable, ~Arp
//
simple Ipv4 extends SimpleModule like IIpv4
{
    parameters:
        @class(Ipv4);
        string interfaceTableModule;   // The path to the InterfaceTable module
        string routingTableModule;
        string arpModule;
        string icmpModule;
        string checksumMode @enum("declared", "computed") = default("declared");
        int timeToLive = default(32);
        int multicastTimeToLive = default(32);
        double fragmentTimeout @unit(s) = default(60s);
        bool limitedBroadcast = default(false); // Send out limited broadcast packets coming from the higher layer
        string directBroadcastInterfaces = default("");   // List of interfaces where direct broadcast is enabled (by default direct broadcast is disabled on all interfaces)
        bool enableLocalOutMulticastRouting = default(false); // Enable using the multicast routing table for determining outgoing interfaces for local out packets
        bool enableTimestampOption = default(false); // When enabled, IP inserts a timestamp option into the IP header
        double maxLifetime @unit(s) = default(-1s); // Packets older than the limit are discarded
        @display("i=block/routing");
        @signal[packetSentToUpper](type=cPacket);
        @signal[packetReceivedFromUpper](type=cPacket);
        @signal[packetSentToLower](type=cPacket);
        @signal[packetReceivedFromLower](type=cPacket);
        @signal[packetDropped](type=cPacket);
        @signal[ipv4NewMulticast](type=inet::Ipv4Header);
        @signal[ipv4DataOnNonrpf](type=inet::Ipv4Header);
        @signal[ipv4DataOnRpf](type=inet::Ipv4Header);
        @signal[ipv4MdataRegister](type=inet::Packet);
        @statistic[packetDropAddressResolutionFailed](title="packet drop: address resolution failed"; source=packetDropReasonIsAddressResolutionFailed(packetDropped); record=count,sum(packetBytes),vector(packetBytes); interpolationmode=none);
        @statistic[packetDropHopLimitReached](title="packet drop: hop limit reached"; source=packetDropReasonIsHopLimitReached(packetDropped); record=count,sum(packetBytes),vector(packetBytes); interpolationmode=none);
        @statistic[packetDropForwardingDisabled](title="packet drop: forwarding disabled"; source=packetDropReasonIsForwardingDisabled(packetDropped); record=count,sum(packetBytes),vector(packetBytes); interpolationmode=none);
        @statistic[packetDropLifetimeExpired](title="packet drop: lifetime expired"; source=packetDropReasonIsLifetimeExpired(packetDropped); record=count,sum(packetBytes),vector(packetBytes); interpolationmode=none);
        @statistic[packetDropNoInterfaceFound](title="packet drop: no interface found"; source=packetDropReasonIsNoInterfaceFound(packetDropped); record=count,sum(packetBytes),vector(packetBytes); interpolationmode=none);
        @statistic[packetDropNoRouteFound](title="packet drop: no route found"; source=packetDropReasonIsNoRouteFound(packetDropped); record=count,sum(packetBytes),vector(packetBytes); interpolationmode=none);
        @statistic[packetDropUndefined](title="packet drop: undefined"; source=packetDropReasonIsUndefined(packetDropped); record=count,sum(packetBytes),vector(packetBytes); interpolationmode=none);
    gates:
        input transportIn @labels(Ipv4ControlInfo/down,TcpHeader,UdpHeader,SctpHeader);
        output transportOut @labels(Ipv4ControlInfo/up,TcpHeader,UdpHeader,SctpHeader);
        input queueIn @labels(Ipv4Header,ArpPacket,Ieee802Ctrl);
        output queueOut @labels(Ipv4Header,ArpPacket,Ieee802Ctrl);
}

