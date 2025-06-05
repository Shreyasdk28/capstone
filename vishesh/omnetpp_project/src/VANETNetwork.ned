package vanet;

import org.car2x.veins.nodes.Car;
import org.car2x.veins.nodes.RSU;
import org.car2x.veins.base.connectionManager.ConnectionManager;
import org.car2x.veins.base.modules.BaseWorldUtility;
import org.car2x.veins.modules.mobility.traci.TraCIScenarioManager;
import org.car2x.veins.modules.obstacle.ObstacleControl;
import org.car2x.veins.modules.world.annotations.AnnotationManager;

network VANETNetwork
{
    parameters:
        double playgroundSizeX @unit(m) = default(2500m);
        double playgroundSizeY @unit(m) = default(2500m);
        double playgroundSizeZ @unit(m) = default(50m);
        @display("bgb=$playgroundSizeX,$playgroundSizeY");
        
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
                playgroundSizeX = parent.playgroundSizeX;
                playgroundSizeY = parent.playgroundSizeY;
                playgroundSizeZ = parent.playgroundSizeZ;
                @display("p=30,0;i=misc/globe");
        }
        manager: TraCIScenarioManager {
            parameters:
                @display("p=512,128");
        }
        
    connections allowunconnected:
}

simple Vehicle
{
    parameters:
        @display("i=block/circle");
        double beaconInterval @unit(s) = default(1s);
        double transmissionRange @unit(m) = default(300m);
        
    gates:
        input radioIn @directIn;
        inout gate[];
}

simple TrafficSignal
{
    parameters:
        @display("i=block/traffic");
        double transmissionRange @unit(m) = default(500m);
        double signalChangeInterval @unit(s) = default(30s);
        
    gates:
        input radioIn @directIn;
        inout gate[];
} 