packet AirFrame
{
    simtime_t duration;
    int state = 1;
    int type = 0;
    long id;
    int protocolId;
    int channel;
    int mcs;
}