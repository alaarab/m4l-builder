#pragma once
#include <cmath>
#include <limits>

/* Derived from Cycling '74 genlib_ops.h safemod (2012), with a guard before
 * the original out-of-range integer conversion. Reference copy:
 * https://github.com/DISTRHO/DPF-Max-Gen/blob/535c81cabefb336a27125a9caaadd0950c2ab163/plugins/common/gen_dsp/genlib_ops.h
 * Actual Max 9.0.10 captures verify the arithmetic and epsilon threshold.
 *
 * Copyright (c) 2012 Cycling '74
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
 * of the Software, and to permit persons to whom the Software is furnished to
 * do so, subject to the following conditions:
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
namespace m4l::gen {
inline double remainderImpl(double input,double divisor,double reciprocal,bool constant) noexcept {
    const double magnitude=std::abs(divisor);
    if(!(magnitude>std::numeric_limits<double>::epsilon()))return 0;
    if(input>=magnitude*2 || input<=-magnitude*2){
        const double quotient=constant?input*reciprocal:input/magnitude;
        // Max's reference implementation casts this to signed long. Keep
        // unverified values outside that domain contained without C++ UB.
        if(!std::isfinite(quotient) || quotient>=0x1p63 || quotient<-0x1p63)
            return std::numeric_limits<double>::quiet_NaN();
        // Max's ARM Gen compiler replaces a constant divisor with its
        // reciprocal and fuses the subtraction. The residual can be nonzero
        // even at integer multiples; exact comparisons depend on it. The
        // separate constant/dynamic original-Max captures exercise both paths.
        return (constant?std::fma(input,reciprocal,-std::trunc(quotient)):
                quotient-std::trunc(quotient))*magnitude;
    }
    if(input>=magnitude)return input-magnitude;
    if(input<=-magnitude)return input+magnitude;
    return input;
}
inline double remainder(double input,double divisor) noexcept {
    return remainderImpl(input,divisor,0,false);
}
inline double constantRemainder(double input,double divisor,double reciprocal) noexcept {
    return remainderImpl(input,divisor,reciprocal,true);
}
}
