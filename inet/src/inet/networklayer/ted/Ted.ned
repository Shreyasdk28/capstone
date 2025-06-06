//
// Copyright (C) 2005 Vojtech Janota
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//

package inet.networklayer.ted;

import inet.common.SimpleModule;

//
// Traffic Engineering Database. Stores network topology with detailed
// link information, including total and reserved bandwidths.
//
// ~Ted is filled in and kept up-to-date via link state routing protocols,
// like ~LinkStateRouting or (in the future) OSPF-TE.
//
// Ted exposes several public methods for querying the current network state
// and allows ~RsvpTe and individual applications to calculate feasible LSPs
// meeting the chosen bandwidth criteria.
//
simple Ted extends SimpleModule
{
    parameters:
        @class(Ted);
        string interfaceTableModule;   // The path to the InterfaceTable module
        string routingTableModule;  // The path to the RoutingTable module
        @display("i=block/table");
}
