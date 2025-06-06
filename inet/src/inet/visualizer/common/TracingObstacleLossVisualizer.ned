//
// Copyright (C) 2020 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.visualizer.common;

import inet.visualizer.contract.ITracingObstacleLossVisualizer;

//
// Integrates canvas and osg obstacle loss visualizers into a single module.
//
// @see ~TracingObstacleLossCanvasVisualizer, ~TracingObstacleLossOsgVisualizer, ~TracingObstacleLossVisualizerBase, ~ITracingObstacleLossVisualizer
//
module TracingObstacleLossVisualizer like ITracingObstacleLossVisualizer
{
    parameters:
        @display("i=block/app");
        string visualizationTargetModule = default("^");
        string visualizationSubjectModule = default("^");
        *.visualizationTargetModule = default(absPath(this.visualizationTargetModule));
        *.visualizationSubjectModule = default(absPath(this.visualizationSubjectModule));
    submodules:
        canvasVisualizer: <default(firstAvailableOrEmpty("TracingObstacleLossCanvasVisualizer"))> like ITracingObstacleLossVisualizer if typename != "" {
            parameters:
                @display("p=100,100");
        }
        osgVisualizer: <default(firstAvailableOrEmpty("TracingObstacleLossOsgVisualizer"))> like ITracingObstacleLossVisualizer if typename != "" {
            parameters:
                @display("p=100,200");
        }
}

