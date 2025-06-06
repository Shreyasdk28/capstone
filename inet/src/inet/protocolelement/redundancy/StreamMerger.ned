//
// Copyright (C) 2020 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.protocolelement.redundancy;

import inet.queueing.base.PacketFilterBase;
import inet.queueing.contract.IPacketFilter;

//
// Merges the packets of the same stream by removing duplicates. In
// addition, it also replaces the stream name on the packet based on the mapping
// parameter. For merging, it maintains a separate finite buffer per stream with
// the last seen sequence numbers.
//
simple StreamMerger extends PacketFilterBase like IPacketFilter
{
    parameters:
        object mapping @mutable = default({}); // Map of input streams to output streams. An empty string means no stream. For example, {s0: "s1", ...}
        int bufferSize = default(10); // Window size for sequence numbers per stream.
        @class(StreamMerger);
        @display("i=block/join");
}
