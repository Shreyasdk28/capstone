// Message definitions for VANET communication
packet VANETMessage {
    int sourceId;  // ID of the sending vehicle
    int destinationId;  // ID of the destination vehicle (-1 for broadcast)
    string messageType;  // Type of message (e.g., "BEACON", "EMERGENCY", "INFO")
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