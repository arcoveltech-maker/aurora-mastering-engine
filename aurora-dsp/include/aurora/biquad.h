#pragma once

namespace aurora {

struct BiquadCoeffs {
  double b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0;
};

class BiquadFilter {
 public:
  void setCoefficients(const BiquadCoeffs& c);
  // Process a single sample and return the output
  float process(float x);
  // Process a block (double precision)
  void process(const double* input, double* output, int numSamples);
  void reset();
 private:
  BiquadCoeffs coeffs_;
  double s1_ = 0, s2_ = 0;
};

}  // namespace aurora
