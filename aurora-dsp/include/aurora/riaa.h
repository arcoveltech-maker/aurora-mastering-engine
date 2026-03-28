#pragma once
#include "aurora/biquad.h"

namespace aurora {

// RIAA de-emphasis filter for vinyl simulation.
// Three time constants: 75 µs, 318 µs, 3180 µs
// Applied as two cascaded biquad stages.
class RIAAFilter {
 public:
  explicit RIAAFilter(int sampleRate);
  float process(float x);
  void reset();

 private:
  BiquadFilter stage1_;
  BiquadFilter stage2_;
};

}  // namespace aurora
