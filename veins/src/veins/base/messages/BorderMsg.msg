
packet BorderMsg
{
    int policy;    // border policy to use for the host
    Coord startPos; // new start position of the host
    Coord direction; // new direction of the host
}