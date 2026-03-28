#pragma once
#include "aurora/biquad.h"

namespace aurora {

class KWeightingFilter {
 public:
  KWeightingFilter(int sampleRate);
  float process(float x);
  void reset();
 private:
  BiquadFilter stage1a_;
  BiquadFilter stage1b_;
};

class LUFSMeter {
 public:
  LUFSMeter(int sampleRate, int numChannels);
  void processFrame(const float* frame);   // one interleaved frame (numChannels samples)
  void reset();
  double getIntegratedLUFS() const;
  double getMomentaryLUFS() const;
  double getShortTermLUFS() const;
  double getLRA() const;
 private:
  int sampleRate_ = 48000;
  int numChannels_ = 2;
  // K-weighting filters, one per channel
  KWeightingFilter kL_;
  KWeightingFilter kR_;
  // ITU-R BS.1770-4 mean-square accumulators
  double sumSq_ = 0.0;
  long long count_ = 0;
};

}  // namespace aurora
