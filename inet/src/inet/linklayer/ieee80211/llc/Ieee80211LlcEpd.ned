//
// Copyright (C) 2018 Raphael Riebl, TH Ingolstadt
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//

package inet.linklayer.ieee80211.llc;

import inet.common.SimpleModule;

//
// An LLC implementation that encapsulates packets with the IEEE 802 `EtherType`
// Protocol Discrimination (EPD) header, as defined in section 9.2 `EtherTypes`
// of the IEEE Std 802-2014 standard. See ~Ieee802EpdHeader.
//
simple Ieee80211LlcEpd extends SimpleModule like IIeee80211Llc
{
    parameters:
        @class(Ieee80211LlcEpd);
        @display("i=block/layer");
        @signal[packetDropped](type=Packet);
    gates:
        input upperLayerIn;
        output upperLayerOut;
        input lowerLayerIn;
        output lowerLayerOut;
}
