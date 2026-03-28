#include "aurora/true_peak.h"
#include <cmath>
#include <algorithm>

namespace aurora {

TruePeakMeter::TruePeakMeter(int sampleRate, int numChannels)
    : sampleRate_(sampleRate), numChannels_(numChannels) {
  history_.fill(0.0);
}

void TruePeakMeter::reset() {
  maxLinear_ = 0.0;
  history_.fill(0.0);
}

// Catmull-Rom / cubic Hermite interpolation.
// p0..p3 are four successive samples; t in [0,1] interpolates between p1 and p2.
double TruePeakMeter::hermite(double p0, double p1, double p2, double p3, double t) noexcept {
  const double t2 = t * t;
  const double t3 = t2 * t;
  return 0.5 * ((2.0 * p1) +
                (-p0 + p2) * t +
                (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 +
                (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3);
}

void TruePeakMeter::processFrame(const float* frame) {
  // 4x oversampling: evaluate interpolated values at t = 0.0, 0.25, 0.50, 0.75
  // between the two most recent samples, using 4-point cubic Hermite.
  for (int c = 0; c < numChannels_; ++c) {
    double* h = history_.data() + c * kHistory;
    // Shift history and insert new sample
    h[0] = h[1]; h[1] = h[2]; h[2] = h[3];
    h[3] = static_cast<double>(frame[c]);

    // Check actual sample
    double a = std::fabs(h[3]);
    if (a > maxLinear_) maxLinear_ = a;

    // Evaluate 3 interpolated points between h[2] and h[3]
    for (int k = 1; k <= 3; ++k) {
      double t = k * 0.25;
      double interp = hermite(h[0], h[1], h[2], h[3], t);
      a = std::fabs(interp);
      if (a > maxLinear_) maxLinear_ = a;
    }
  }
}

double TruePeakMeter::getTruePeakDBTP() const {
  if (maxLinear_ <= 0.0) return -100.0;
  return 20.0 * std::log10(maxLinear_);
}

bool TruePeakMeter::exceedsCeiling(double ceilingDBTP) const {
  return getTruePeakDBTP() > ceilingDBTP;
}

}  // namespace aurora
