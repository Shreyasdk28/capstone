//
// Copyright (C) 2020 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.visualizer.contract;

//
// Interface allows configuring different ~IFailureProtectionConfigurationVisualizer
// submodules from INI files. Such a visualizer displays the TSN configuration
// in a network.
//
// @see ~FailureProtectionConfigurationCanvasVisualizer
//
moduleinterface IFailureProtectionConfigurationVisualizer extends IVisualizer
{
    parameters:
        @display("i=block/app");
}

