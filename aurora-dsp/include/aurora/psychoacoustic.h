#pragma once
#include <vector>

namespace aurora {

// Psychoacoustic engine: Bark-scale analysis, masking thresholds, ISO 532-1 loudness
class PsychoacousticEngine {
 public:
  explicit PsychoacousticEngine(int sampleRate, int fftSize = 2048);

  // Compute simultaneous masking threshold for a power spectrum.
  // spectrum: linear power per FFT bin (size = fftSize/2+1)
  // Returns: masking threshold in dB per Bark band (24 bands)
  std::vector<float> computeMaskingThreshold(const float* spectrum, int numBins) const;

  // Compute perceived loudness in phons using ISO 532-1 (Zwicker) approximation.
  // audio: mono audio samples
  float computePerceivedLoudness(const float* audio, int numFrames) const;

  // Convert Hz → Bark (Traunmüller formula)
  static float hzToBark(float hz);

  // Compute spectral spread in Bark (perceptual bandwidth)
  float computeBarkSpread(const float* spectrum, int numBins) const;

 private:
  int sampleRate_;
  int fftSize_;
  int numBins_;

  // Precomputed Bark-band boundaries (bin indices)
  std::vector<int> barkBoundaries_;

  void initBarkBoundaries();
  float spreadingFunction(float dz) const;  // dz = distance in Bark
};

}  // namespace aurora
