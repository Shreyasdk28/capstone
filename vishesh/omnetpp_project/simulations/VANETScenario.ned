package vanet.simulations;

import org.car2x.veins.nodes.RSU;
import org.car2x.veins.nodes.Scenario;
import vanet.VANETVehicle;

network VANETScenario extends Scenario
{
    submodules:
        rsu[1]: RSU {
            @display("p=150,140;i=veins/sign/yellowdiamond;is=vs");
        }
}
