#include "aurora/biquad.h"

namespace aurora {

void BiquadFilter::setCoefficients(const BiquadCoeffs& c) { coeffs_ = c; }

void BiquadFilter::process(const double* input, double* output, int numSamples) {
  for (int i = 0; i < numSamples; ++i) {
    double x = input[i];
    double y = coeffs_.b0 * x + s1_;
    s1_ = coeffs_.b1 * x - coeffs_.a1 * y + s2_;
    s2_ = coeffs_.b2 * x - coeffs_.a2 * y;
    output[i] = y;
  }
}

void BiquadFilter::reset() { s1_ = s2_ = 0; }

}  // namespace aurora
