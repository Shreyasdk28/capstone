//
// Copyright (C) 2020 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.protocolelement.selectivity;

import inet.common.SimpleModule;

simple SendToMacAddress extends SimpleModule
{
    parameters:
        @class(SendToMacAddress);
        string address = default("");
        @display("i=block/tx");
    gates:
        input in;
        output out;
}
