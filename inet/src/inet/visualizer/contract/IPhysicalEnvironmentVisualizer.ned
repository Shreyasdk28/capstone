//
// Copyright (C) 2020 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.visualizer.contract;

//
// Interface allows configuring different
// ~IPhysicalEnvironmentVisualizer submodules from INI files. Such a visualizer
// displays the physical objects present in the physical environment.
//
// @see ~PhysicalEnvironmentCanvasVisualizer, ~PhysicalEnvironmentOsgVisualizer, ~PhysicalEnvironmentVisualizer, ~PhysicalEnvironmentVisualizerBase
//
moduleinterface IPhysicalEnvironmentVisualizer extends IVisualizer
{
    parameters:
        @display("i=block/app");
}

