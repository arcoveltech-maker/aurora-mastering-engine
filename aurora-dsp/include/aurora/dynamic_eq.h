#pragma once
#include "aurora/biquad.h"
#include <array>

namespace aurora {

struct DynamicEQBand {
  float freqHz      = 1000.0f;
  float qFactor     =    1.0f;
  float staticGainDb =  0.0f;   // always-on static gain
  float dynamicGainDb = 6.0f;  // max additional gain when fully active
  float thresholdDb = -20.0f;
  float ratio       =   2.0f;
  float attackMs    =  10.0f;
  float releaseMs   = 100.0f;
  bool  expand      =  false;   // false = compress/cut, true = expand/boost
};

// Per-band dynamic EQ — up to 6 bands
class DynamicEQ {
 public:
  static constexpr int kMaxBands = 6;

  explicit DynamicEQ(int sampleRate);
  void setBand(int band, const DynamicEQBand& params);
  // Process interleaved stereo/mono, in-place
  void process(float* buffer, int numFrames, int numChannels);
  void reset();

 private:
  int sampleRate_;
  DynamicEQBand bands_[kMaxBands];
  int numBands_ = 0;
  BiquadFilter peakFilters_[kMaxBands];
  float envelopes_[kMaxBands] = {};

  void computePeakCoeffs(float freqHz, float qFactor, float gainDb, BiquadCoeffs& out) const;
};

}  // namespace aurora
