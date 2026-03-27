#pragma once

namespace aurora {

class TruePeakMeter {
 public:
  TruePeakMeter(int sampleRate, int numChannels);
  void process(const float* input, int numFrames);
  double getTruePeakDBTP() const;
  bool exceedsCeiling(double ceilingDBTP) const;
 private:
  int numChannels_ = 2;
  double maxLinear_ = 0.0;
};

}  // namespace aurora
