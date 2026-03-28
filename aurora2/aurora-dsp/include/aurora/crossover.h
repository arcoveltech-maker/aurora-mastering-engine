#pragma once
#include "biquad.h"
#include <array>

namespace aurora {

// Linkwitz-Riley 8th-order crossover (LR8 = two cascaded LR4 = four cascaded BW2)
// Produces sum-to-unity within ±0.01 dB
class LR8Crossover {
 public:
  LR8Crossover(int sampleRate, float crossoverHz);
  void reset();
  // Process one stereo frame; splits into low and high bands
  void processStereo(const float* in2, float* low2, float* high2);
  void setCrossoverHz(float hz);

 private:
  int sampleRate_;
  float crossoverHz_;
  // 4 biquad stages per channel per band (LP and HP), 2 channels
  // LR8: cascade 4x BW2 LP stages and 4x BW2 HP stages
  std::array<BiquadFilter, 8> lpL_, lpR_;  // 4 LP stages each channel
  std::array<BiquadFilter, 8> hpL_, hpR_;  // 4 HP stages each channel
  void buildCoeffs();
};

}  // namespace aurora
