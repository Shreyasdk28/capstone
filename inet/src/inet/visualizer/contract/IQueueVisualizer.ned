//
// Copyright (C) 2020 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.visualizer.contract;

//
// Interface allows configuring different ~IQueueVisualizer
// submodules from INI files. Such a visualizer displays queues.
//
// @see ~QueueCanvasVisualizer, ~QueueOsgVisualizer, ~QueueVisualizer, ~QueueVisualizerBase
//
moduleinterface IQueueVisualizer extends IVisualizer
{
    parameters:
        @display("i=block/app");
}

