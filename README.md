# 🚦 SUMO Scenario: 
## 🔗 File Flow (How They Connect)

```text
osm_bbox.osm.xml.gz  --->  [netconvert + osm.netccfg]   --->  osm.net.xml.gz
osm_bbox.osm.xml.gz  --->  [polyconvert + osm.polycfg]  --->  osm.poly.xml.gz

osm.passenger.trips.xml  ----\
osm.bus.trips.xml         ----+--> used inside osm.sumocfg
osm.bicycle.trips.xml     ----/

osm.net.xml.gz + trips + polygons  --->  osm.sumocfg  --->  sumo / sumo-gui

#Running the Simulation
```
sumo-gui -c osm.sumocfg 