#include "aurora/riaa.h"
#include <cmath>

namespace aurora {

// RIAA de-emphasis: IEC 60094-8 / RIAA standard
// Poles at 1/(2π·75µs) ≈ 2122 Hz, 1/(2π·318µs) ≈ 500 Hz
// Zero at 1/(2π·3180µs) ≈ 50 Hz
// Digital implementation using bilinear transform (pre-warped)

static void computeRIAAStages(int sr, BiquadCoeffs& s1, BiquadCoeffs& s2) {
  const double fs = static_cast<double>(sr);
  const double pi = 3.14159265358979;

  // Time constants
  const double t1 = 3180e-6;  // 3180 µs
  const double t2 =  318e-6;  //  318 µs
  const double t3 =   75e-6;  //   75 µs

  // Pole/zero frequencies (pre-warped)
  auto prewarp = [&](double t) {
    return 2.0 * fs * std::tan(pi / (fs * t));
  };

  // Stage 1: first-order shelving using the 3180 µs zero and 318 µs pole
  // Shelf: H(s) = (1 + s*t1) / (1 + s*t2), using bilinear transform
  double w1 = prewarp(t1);
  double w2 = prewarp(t2);

  {
    // Bilinear transform: s → 2*fs*(z-1)/(z+1)
    double k  = 2.0 * fs;
    double b0 =  k + w1;
    double b1 = -k + w1;
    double a0 =  k + w2;
    double a1 = -k + w2;
    s1 = {b0/a0, b1/a0, 0.0, a1/a0, 0.0};
  }

  // Stage 2: first-order HP for 75 µs pole (IEC: additional high-freq roll-off)
  double w3 = prewarp(t3);
  {
    double k  = 2.0 * fs;
    double a0 =  k + w3;
    double a1 = -k + w3;
    // Simple 1-pole LP at 75 µs
    double b0 = w3;
    double b1 = w3;
    s2 = {b0/a0, b1/a0, 0.0, a1/a0, 0.0};
  }
}

RIAAFilter::RIAAFilter(int sampleRate) {
  BiquadCoeffs s1, s2;
  computeRIAAStages(sampleRate, s1, s2);
  stage1_.setCoefficients(s1);
  stage2_.setCoefficients(s2);
}

float RIAAFilter::process(float x) {
  return stage2_.process(stage1_.process(x));
}

void RIAAFilter::reset() {
  stage1_.reset();
  stage2_.reset();
}

}  // namespace aurora
