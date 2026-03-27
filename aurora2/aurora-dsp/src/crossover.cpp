#include "aurora/crossover.h"
#include <cmath>

namespace aurora {

static constexpr double kPi = 3.14159265358979323846;

LR8Crossover::LR8Crossover(int sampleRate, float crossoverHz)
    : sampleRate_(sampleRate), crossoverHz_(crossoverHz) {
  buildCoeffs();
}

void LR8Crossover::reset() {
  for (auto& f : lpL_) f.reset();
  for (auto& f : lpR_) f.reset();
  for (auto& f : hpL_) f.reset();
  for (auto& f : hpR_) f.reset();
}

void LR8Crossover::setCrossoverHz(float hz) {
  crossoverHz_ = hz;
  buildCoeffs();
  reset();
}

void LR8Crossover::buildCoeffs() {
  // Butterworth 2nd-order LP and HP at crossoverHz_
  // LR8 = 4 cascaded BW2 stages
  double w0 = 2.0 * kPi * crossoverHz_ / sampleRate_;
  double cosW = std::cos(w0);
  double sinW = std::sin(w0);
  double q = 0.7071067811865476;  // 1/sqrt(2) for BW2
  double alpha = sinW / (2.0 * q);

  double b0lp = (1.0 - cosW) / 2.0;
  double b1lp = 1.0 - cosW;
  double b2lp = (1.0 - cosW) / 2.0;
  double a0lp = 1.0 + alpha;
  double a1lp = -2.0 * cosW;
  double a2lp = 1.0 - alpha;

  BiquadCoeffs lpCoeffs;
  lpCoeffs.b0 = b0lp / a0lp;
  lpCoeffs.b1 = b1lp / a0lp;
  lpCoeffs.b2 = b2lp / a0lp;
  lpCoeffs.a1 = a1lp / a0lp;
  lpCoeffs.a2 = a2lp / a0lp;

  double b0hp = (1.0 + cosW) / 2.0;
  double b1hp = -(1.0 + cosW);
  double b2hp = (1.0 + cosW) / 2.0;

  BiquadCoeffs hpCoeffs;
  hpCoeffs.b0 = b0hp / a0lp;
  hpCoeffs.b1 = b1hp / a0lp;
  hpCoeffs.b2 = b2hp / a0lp;
  hpCoeffs.a1 = a1lp / a0lp;
  hpCoeffs.a2 = a2lp / a0lp;

  for (auto& f : lpL_) f.setCoefficients(lpCoeffs);
  for (auto& f : lpR_) f.setCoefficients(lpCoeffs);
  for (auto& f : hpL_) f.setCoefficients(hpCoeffs);
  for (auto& f : hpR_) f.setCoefficients(hpCoeffs);
}

void LR8Crossover::processStereo(const float* in2, float* low2, float* high2) {
  float l = in2[0], r = in2[1];

  // Process 4 cascaded LP stages per channel
  for (auto& f : lpL_) l = f.process(l);
  float lR = in2[1];
  for (auto& f : lpR_) lR = f.process(lR);
  low2[0] = l;
  low2[1] = lR;

  float hL = in2[0];
  float hR = in2[1];
  for (auto& f : hpL_) hL = f.process(hL);
  for (auto& f : hpR_) hR = f.process(hR);
  high2[0] = hL;
  high2[1] = hR;
}

}  // namespace aurora
