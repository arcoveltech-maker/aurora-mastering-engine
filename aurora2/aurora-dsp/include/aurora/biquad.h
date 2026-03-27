#pragma once

namespace aurora {

struct BiquadCoeffs {
  double b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0;
};

class BiquadFilter {
 public:
  void setCoefficients(const BiquadCoeffs& c);
  // Bulk double-precision processing
  void process(const double* input, double* output, int numSamples);
  // Single-sample float processing (for per-frame DSP chains)
  float process(float x);
  void reset();
 private:
  BiquadCoeffs coeffs_;
  double s1_ = 0, s2_ = 0;
};

}  // namespace aurora
