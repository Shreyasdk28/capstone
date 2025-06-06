//
// Copyright (C) 2014 OpenSim Ltd.
//
// SPDX-License-Identifier: LGPL-3.0-or-later
//


package inet.physicallayer.wireless.common.radio.bitlevel;

import inet.common.Module;
import inet.physicallayer.wireless.common.contract.bitlevel.IFecCoder;

//
// Implements convolutional coding, a type of error-correcting code that
// generates parity symbols via the sliding application of a boolean polynomial
// function to a data stream.
//
// <b>Transfer function (octal) matrix</b>
//
// transferFunctionMatrix = "133 171" means a simple vector with two elements:
// [133, 171]. We use the standard octal representation of the industry-standard
// generators of the 1/2 convolutional encoder. You also have to define your own
// polynomials in the octal number system!
// transferFunctionMatrix = "3 1 3; 1 2 2" means a k-by-n matrix:
// <pre>
// | 3 1 3 |
// | 1 2 2 |
// </pre>
// which is a very simple 2/3 encoder.
//
// <b>Puncturing (bool) matrix and `punctureK`, `punctureN` parameters</b>
//
// The same rule applies to the puncturing matrix representation.
// A puncturing matrix only consists of boolean values represented with
// 0 or 1.
// By default, we set it to
// <pre>
// | 1 |
// | 1 |
// </pre>
// This simple puncturing matrix, in the 1/2 case, means no puncturing applies.
// You also have to set the new code rate parameters: a new
// <pre>
// | 1 1 |
// | 1 0 |
// </pre>
// puncturing matrix together with the default settings define a 2/3 encoder,
// so the correct values for `punctureK` and `punctureN` are 2 and 3.
//
// <b>Constraint length (integer) vector</b>
//
// The constraint length is a 1-by-k vector that specifies the delay for the
// encoder's k input bit streams.
//
// The default settings define the standard 1/2 convolutional encoder used by
// IEEE802.11 PHY.
//
// <b>Encoding/decoding mode</b>
//
// There are two modes:
//  - "truncated" : The trellis graph traceback path always starts in the all-zeros state
//                  and ends with the best metric.
//  - "terminated": The trellis graph traceback path always starts and ends in the all-zeros
//                  state.
// The encoding process works in accordance with the industry standards and starts
// in the all-zeros state.
//
module ConvolutionalCoder extends Module like IFecCoder
{
    parameters:
        string transferFunctionMatrix = default("133 171");
        string mode = default("truncated");
        string puncturingMatrix = default("1;1");
        int punctureK = default(1);
        int punctureN = default(2);
        string constraintLengthVector = default("7");
        @display("i=block/segm");
        @class(ConvolutionalCoderModule);
}

