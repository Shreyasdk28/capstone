//
// Copyright (C) 2017 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.linklayer.lmac;

import inet.linklayer.common.WirelessInterface;

//
// Implements a wireless network interface using the L-MAC protocol.
//
module LMacInterface extends WirelessInterface
{
    parameters:
        radio.typename = default("ApskRadio");
        mac.typename = "LMac";
        queue.typename = default("DropTailQueue");
        queue.packetCapacity = default(10);
}

