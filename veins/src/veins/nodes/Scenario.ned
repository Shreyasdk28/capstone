//
// Copyright (C) 2008 Christoph Sommer <christoph.sommer@informatik.uni-erlangen.de>
// SPDX-License-Identifier: GPL-2.0-or-later
//

package veins.nodes;

import veins.base.connectionManager.ConnectionManager;
import veins.base.modules.BaseWorldUtility;
import veins.modules.mobility.traci.TraCIScenarioManager*;
import veins.modules.obstacle.ObstacleControl;
import veins.modules.world.annotations.AnnotationManager;
import veins.nodes.Car;
import veins.visualizer.roads.RoadsCanvasVisualizer;

network Scenario
{
    parameters:
        double playgroundSizeX @unit(m); // x size of the area the nodes are in (in meters)
        double playgroundSizeY @unit(m); // y size of the area the nodes are in (in meters)
        double playgroundSizeZ @unit(m); // z size of the area the nodes are in (in meters)
        @display("bgb=dropUnit($playgroundSizeX),dropUnit($playgroundSizeY)");
    submodules:
        obstacles: ObstacleControl {
            @display("p=240,50");
        }
        annotations: AnnotationManager {
            @display("p=260,50");
        }
        connectionManager: ConnectionManager {
            parameters:
                @display("p=150,0;i=abstract/multicast");
        }
        world: BaseWorldUtility {
            parameters:
                playgroundSizeX = veins_eval_by_version(veins_omnetpp_buildnum(), "playgroundSizeX", 1525, "parent.playgroundSizeX");
                playgroundSizeY = veins_eval_by_version(veins_omnetpp_buildnum(), "playgroundSizeY", 1525, "parent.playgroundSizeY");
                playgroundSizeZ = veins_eval_by_version(veins_omnetpp_buildnum(), "playgroundSizeZ", 1525, "parent.playgroundSizeZ");
                @display("p=30,0;i=misc/globe");
        }
        manager: TraCIScenarioManagerLaunchd {
            parameters:
                @display("p=512,128");
        }
        roadsCanvasVisualizer: RoadsCanvasVisualizer {
            @display("p=300,0");
        }
        node[0]: Car {
        }

    connections allowunconnected:
}