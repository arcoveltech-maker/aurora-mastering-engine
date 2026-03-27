#include "aurora/true_peak.h"
#include <cmath>

namespace aurora {

TruePeakMeter::TruePeakMeter(int sampleRate, int numChannels) {
  (void)sampleRate;
  numChannels_ = numChannels;
}

void TruePeakMeter::reset() {
  maxLinear_ = 0.0;
}

void TruePeakMeter::processFrame(const float* frame) {
  for (int c = 0; c < numChannels_; ++c) {
    double a = std::fabs(static_cast<double>(frame[c]));
    if (a > maxLinear_) maxLinear_ = a;
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
