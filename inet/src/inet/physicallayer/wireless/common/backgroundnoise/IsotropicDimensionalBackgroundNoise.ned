//
// Copyright (C) 2013 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.physicallayer.wireless.common.backgroundnoise;

import inet.common.Module;
import inet.physicallayer.wireless.common.contract.packetlevel.IBackgroundNoise;

//
// This background noise model describes noise that does not change over space,
// time and frequency. It produces dimensional noise signals that can be further
// used in dimensional computations.
//
module IsotropicDimensionalBackgroundNoise extends Module like IBackgroundNoise
{
    parameters:
        double powerSpectralDensity @unit(dBmWpMHz) = default(nan dBmWpMHz); // When specified, the power and bandwidth parameters are not used
        double power @unit(dBm) = default(nan dBm); // When specified, the bandwidth can be determined automatically by matching the signal's bandwidth
        double bandwidth @unit(Hz) = default(nan Hz); // Determined automatically if the value is NaN, otherwise must match the signal's bandwidth
        @class(IsotropicDimensionalBackgroundNoise);
        @display("i=block/mac");
}

