//
// Copyright (C) 2005 Christian Dankbar, Irene Ruengeler, Michael Tuexen
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.linklayer.contract;

//
// Interface for external network interfaces.
//
moduleinterface IExternalInterface extends INetworkInterface
{
    parameters:
        @display("i=block/ifcard");
}

