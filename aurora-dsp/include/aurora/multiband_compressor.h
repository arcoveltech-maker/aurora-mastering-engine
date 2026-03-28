#pragma once
#include "aurora/biquad.h"
#include <array>

namespace aurora {

struct CompressorBand {
  float thresholdDb  = -20.0f;
  float ratio        =   4.0f;
  float attackMs     =  10.0f;
  float releaseMs    = 100.0f;
  float kneeDb       =   6.0f;
  float makeupGainDb =   0.0f;
  bool  sidechainHpf =  false;
};

// 4-band Linkwitz-Riley multiband compressor
// Crossovers at 100 Hz, 1 kHz, 8 kHz
class MultibandCompressor {
 public:
  explicit MultibandCompressor(int sampleRate);
  void setBand(int band, const CompressorBand& params);
  // Process interleaved stereo (or mono if numChannels==1), in-place
  void process(float* buffer, int numFrames, int numChannels);
  void reset();

 private:
  static constexpr int kNumBands = 4;
  int sampleRate_;

  CompressorBand bands_[kNumBands];
  float envelopes_[kNumBands] = {};   // linear gain reduction envelopes

  // LR4 crossover: 2 cascaded biquad pairs per crossover
  // Low: LP@100, Mid-lo: HP@100+LP@1k, Mid-hi: HP@1k+LP@8k, High: HP@8k
  BiquadFilter xoLp1_[2];   // 100 Hz LP (×2 for LR4)
  BiquadFilter xoHp1_[2];   // 100 Hz HP (×2)
  BiquadFilter xoLp2_[2];   // 1 kHz LP (×2)
  BiquadFilter xoHp2_[2];   // 1 kHz HP (×2)
  BiquadFilter xoLp3_[2];   // 8 kHz LP (×2)
  BiquadFilter xoHp3_[2];   // 8 kHz HP (×2)

  void computeLR4Coeffs(float freqHz, BiquadCoeffs& lpOut, BiquadCoeffs& hpOut) const;
  float computeGainReduction(int band, float inputDb) const;
  float dbToLin(float db) const;
  float linToDb(float lin) const;
};

}  // namespace aurora
