//
// Copyright (C) 2020 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.visualizer.common;

import inet.visualizer.contract.IDataLinkVisualizer;

//
// Integrates canvas and osg data link visualizers into a single module.
//
// @see ~DataLinkCanvasVisualizer, ~DataLinkOsgVisualizer, ~LinkVisualizerBase, ~IDataLinkVisualizer
//
module DataLinkVisualizer like IDataLinkVisualizer
{
    parameters:
        @display("i=block/app");
        string visualizationTargetModule = default("^");
        string visualizationSubjectModule = default("^");
        *.visualizationTargetModule = default(absPath(this.visualizationTargetModule));
        *.visualizationSubjectModule = default(absPath(this.visualizationSubjectModule));
    submodules:
        canvasVisualizer: <default(firstAvailableOrEmpty("DataLinkCanvasVisualizer"))> like IDataLinkVisualizer if typename != "" {
            parameters:
                @display("p=100,100");
        }
        osgVisualizer: <default(firstAvailableOrEmpty("DataLinkOsgVisualizer"))> like IDataLinkVisualizer if typename != "" {
            parameters:
                @display("p=100,200");
        }
}

