#pragma once

namespace aurora {

class LUFSMeter {
 public:
  LUFSMeter(int sampleRate, int numChannels);
  void process(const float* input, int numFrames);
  double getIntegratedLUFS() const;
  double getMomentaryLUFS() const;
  double getShortTermLUFS() const;
  double getLRA() const;
 private:
  int sampleRate_ = 48000;
  int numChannels_ = 2;
  double integratedLUFS_ = -70.0;
};

#include "aurora/biquad.h"

class KWeightingFilter {
 public:
  KWeightingFilter(int sampleRate);
  void process(const float* input, float* output, int numFrames);
 private:
  BiquadFilter stage1a_;
  BiquadFilter stage1b_;
};

}  // namespace aurora
