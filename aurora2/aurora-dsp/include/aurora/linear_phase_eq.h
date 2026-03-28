#pragma once
#include "biquad.h"
#include <array>
#include <vector>

namespace aurora {

struct EQBand {
  enum class Type { LOWSHELF, HIGHSHELF, PEAK, LOWPASS, HIGHPASS };
  Type type = Type::PEAK;
  float freqHz = 1000.0f;
  float gainDB = 0.0f;
  float q = 0.707f;
  bool enabled = true;
};

// Minimum-phase EQ using cascaded biquad filters (6 bands)
// "Linear phase" here means zero-latency minimum phase; true linear phase
// would require FFT convolution (future enhancement with KissFFT).
class LinearPhaseEQ {
 public:
  static constexpr int kNumBands = 6;

  LinearPhaseEQ(int sampleRate);

  void setBand(int band, const EQBand& params);
  void reset();

  // Process a single sample (call for L and R separately)
  float processSample(float in, int channel);  // channel: 0=L, 1=R

 private:
  int sampleRate_;
  std::array<EQBand, kNumBands> bands_;
  // Per-band, per-channel biquad
  std::array<BiquadFilter, kNumBands> filtersL_;
  std::array<BiquadFilter, kNumBands> filtersR_;

  void rebuildBand(int band);
  BiquadCoeffs calcCoeffs(const EQBand& b) const;
};

}  // namespace aurora
