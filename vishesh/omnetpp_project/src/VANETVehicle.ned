package vanet;

import org.car2x.veins.base.modules.*;
import org.car2x.veins.modules.nic.Nic80211p;

module VANETVehicle extends org.car2x.veins.nodes.Car
{
    parameters:
        @display("i=block/wrxtx");
        string appType = default("vanet.VehicleApp");
        
    submodules:
        app: <appType> like org.car2x.veins.base.modules.IBaseApplLayer {
            parameters:
                @display("p=60,50");
        }
        
        nic: Nic80211p {
            parameters:
                @display("p=60,166");
        }
        
        mobility: BaseMobility {
            parameters:
                @display("p=130,172;i=block/cogwheel");
        }
} 