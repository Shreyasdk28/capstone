//
// Copyright (C) 2012 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.networklayer.configurator.ipv4;

import inet.common.SimpleModule;
import inet.networklayer.configurator.contract.IIpv4NodeConfigurator;

//
// Configures the containing network node using information provided by
// the network's global configurator modue  ~Ipv4NetworkConfigurator.
//
// ~Ipv4NetworkConfigurator only computes and remembers configuration data
// (assigned IP addresses, static routes, etc), but doesn't configure the nodes'
// routing tables and interfaces accordingly. The actual configuration is
// carried out by this module, at network initialization time and also when
// the node restarts (i.e. after a shutdown or a crash.)
//
// This module is needed because of failure/restart scenarios:
// ~Ipv4NetworkConfigurator would not be able to configure the node after
// a restart, because being a global module, it doesn't know about node
// lifecycle events.
//
simple Ipv4NodeConfigurator extends SimpleModule like IIpv4NodeConfigurator
{
    parameters:
        @class(Ipv4NodeConfigurator);
        string interfaceTableModule;   // The path to the InterfaceTable module
        string routingTableModule;
        // TODO eventually rename to networkConfigurator
        string networkConfiguratorModule = default("configurator"); // The absolute path to the Ipv4NetworkConfigurator; use "" if there is no configurator
        bool configureRoutingTable = default(true);     // Add routing entries to the routing table (uses the configurator module)
        @display("i=block/cogwheel");
}

