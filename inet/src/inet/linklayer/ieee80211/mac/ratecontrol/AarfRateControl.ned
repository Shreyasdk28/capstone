//
// Copyright (C) 2016 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.linklayer.ieee80211.mac.ratecontrol;

import inet.common.SimpleModule;
import inet.linklayer.ieee80211.mac.contract.IRateControl;

//
// Implements the Adaptive ARF (AARF) rate control mechanism, which was
// initially described in IEEE 802.11 Rate Adaptation: A Practical Approach,
// by M. Lacage, M.H. Manshaei, and T. Turletti, 2004.
//
simple AarfRateControl extends SimpleModule like IRateControl
{
    parameters:
        @class(AarfRateControl);
        double initialRate @unit(bps) = default(-1bps); // -1 means the fastest mandatory rate
        double interval @unit(s) = default(50ms); // The rate (unconditionally) increases after each time interval.
        int increaseThreshold = default(10); // Number of successful transmissions needed to increase the rate
        int decreaseThreshold = default(2); // Number of consecutive unsuccessful transmissions (in the sense that the ACK does not arrive within the timeout)
                                            // needed to increase the rate
        double increaseThresholdFactor = default(2); // When the transmission of the probing packet fails, increaseThreshold is multiplied by increaseThresholdFactor.
        int maxIncreaseThreshold = default(50); // Upper bound for increaseThreshold.
        @display("i=block/cogwheel");
        @signal[datarateChanged];
        @statistic[datarateChanged](title="datarate"; record=vector; interpolationmode=sample-hold);
}

