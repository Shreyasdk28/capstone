
// A basic MAC (Media Access Control) packet format definition
// 
// subclass if you want to create your own MAC layer packet class
//
// The basic MAC packet only provides source and destination address
//
// @author Daniel Willkomm
packet MacPkt
{
    LAddress::L2Type destAddr; // destination mac address
    LAddress::L2Type srcAddr;  // source mac address
    long             sequenceId; // Sequence Number to detect duplicate messages
}
