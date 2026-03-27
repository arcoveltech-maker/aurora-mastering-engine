#include "aurora/true_peak.h"
#include <cmath>

namespace aurora {

TruePeakMeter::TruePeakMeter(int sampleRate, int numChannels) {
  (void)sampleRate;
  numChannels_ = numChannels;
}

void TruePeakMeter::process(const float* input, int numFrames) {
  for (int i = 0; i < numFrames * numChannels_; ++i) {
    double a = std::fabs(static_cast<double>(input[i]));
    if (a > maxLinear_) maxLinear_ = a;
  }
}

double TruePeakMeter::getTruePeakDBTP() const {
  if (maxLinear_ <= 0) return -100.0;
  return 20.0 * std::log10(maxLinear_);
}

bool TruePeakMeter::exceedsCeiling(double ceilingDBTP) const {
  return getTruePeakDBTP() > ceilingDBTP;
}

}  // namespace aurora
