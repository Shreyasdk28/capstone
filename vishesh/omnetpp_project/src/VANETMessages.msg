// Message definitions for VANET communication
packet VANETMessage {
    int sourceId;  // ID of the sending vehicle/intersection
    int destinationId;  // ID of the destination (-1 for broadcast)
    string messageType;  // Type of message (e.g., "BEACON", "EMERGENCY", "INFO", "TRAFFIC_DATA", "CONTROL")
    double positionX;  // X coordinate of sender
    double positionY;  // Y coordinate of sender
    double speed;  // Current speed of sender
    double timestamp;  // Time when message was sent
}

packet BeaconMessage extends VANETMessage {
    // Periodic beacon messages for vehicle presence
}

packet EmergencyMessage extends VANETMessage {
    string emergencyType;  // Type of emergency
    int priority;  // Priority level of emergency
}

packet TrafficDataMessage extends VANETMessage {
    int northCount;  // Number of vehicles in north approach
    int southCount;  // Number of vehicles in south approach
    int eastCount;   // Number of vehicles in east approach
    int westCount;   // Number of vehicles in west approach
    int currentPhase;  // Current traffic light phase
}

packet TrafficControlMessage extends VANETMessage {
    int phase;  // Phase to set (0: N-S green, 2: E-W green)
    double duration;  // Duration of the phase
} 