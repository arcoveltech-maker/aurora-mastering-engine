#include "aurora/psychoacoustic.h"
#include <cmath>
#include <algorithm>
#include <numeric>

namespace aurora {

static constexpr int   kNumBarkBands = 24;
static constexpr float kPi = 3.14159265358979f;

// Bark band upper edges in Hz (ISO 532)
static const float kBarkEdgesHz[kNumBarkBands + 1] = {
     20,  100,  200,  300,  400,  510,  630,  770,
    920, 1080, 1270, 1480, 1720, 2000, 2320, 2700,
   3150, 3700, 4400, 5300, 6400, 7700, 9500, 12000, 15500
};

PsychoacousticEngine::PsychoacousticEngine(int sampleRate, int fftSize)
    : sampleRate_(sampleRate), fftSize_(fftSize), numBins_(fftSize / 2 + 1)
{
  initBarkBoundaries();
}

void PsychoacousticEngine::initBarkBoundaries() {
  barkBoundaries_.resize(kNumBarkBands + 1);
  float binHz = static_cast<float>(sampleRate_) / static_cast<float>(fftSize_);
  for (int b = 0; b <= kNumBarkBands; ++b) {
    barkBoundaries_[b] = static_cast<int>(kBarkEdgesHz[b] / binHz);
    barkBoundaries_[b] = std::min(barkBoundaries_[b], numBins_ - 1);
  }
}

float PsychoacousticEngine::hzToBark(float hz) {
  // Traunmüller (1990) formula
  return (26.81f * hz / (1960.0f + hz)) - 0.53f;
}

float PsychoacousticEngine::spreadingFunction(float dz) const {
  // Simplified spreading function (dB per Bark)
  if (dz < 0.0f)
    return 17.0f * dz - 0.4f * std::max(0.0f, -dz - 1.0f);
  else
    return -17.0f * dz;
}

std::vector<float> PsychoacousticEngine::computeMaskingThreshold(
    const float* spectrum, int numBins) const
{
  int n = std::min(numBins, numBins_);

  // Aggregate power per Bark band
  std::vector<float> barkPower(kNumBarkBands, 0.0f);
  for (int b = 0; b < kNumBarkBands; ++b) {
    int lo = barkBoundaries_[b];
    int hi = std::min(barkBoundaries_[b + 1], n);
    for (int k = lo; k < hi; ++k)
      barkPower[b] += spectrum[k];
  }

  // Compute masking threshold per Bark band (dB)
  std::vector<float> threshold(kNumBarkBands, -80.0f);
  for (int b = 0; b < kNumBarkBands; ++b) {
    if (barkPower[b] <= 0.0f) continue;
    float maskDb = 10.0f * std::log10(barkPower[b] + 1e-12f);
    // Spread masking to neighbouring bands
    for (int m = 0; m < kNumBarkBands; ++m) {
      float dz = static_cast<float>(m - b);
      float spread = maskDb + spreadingFunction(dz);
      threshold[m] = std::max(threshold[m], spread);
    }
  }

  // Apply absolute hearing threshold (ISO 226 approximation)
  float binHz = static_cast<float>(sampleRate_) / static_cast<float>(fftSize_);
  for (int b = 0; b < kNumBarkBands; ++b) {
    float freqHz = kBarkEdgesHz[b] + (kBarkEdgesHz[b + 1] - kBarkEdgesHz[b]) * 0.5f;
    // Simplified absolute threshold in quiet (dB SPL)
    float absThresh = 3.64f * std::pow(freqHz / 1000.0f, -0.8f)
                    - 6.5f  * std::exp(-0.6f * std::pow(freqHz / 1000.0f - 3.3f, 2.0f))
                    + 1e-3f * std::pow(freqHz / 1000.0f, 4.0f);
    threshold[b] = std::max(threshold[b], absThresh - 60.0f);  // relative
  }

  return threshold;
}

float PsychoacousticEngine::computePerceivedLoudness(
    const float* audio, int numFrames) const
{
  if (numFrames <= 0) return 0.0f;

  // Compute RMS level
  float sumSq = 0.0f;
  for (int i = 0; i < numFrames; ++i)
    sumSq += audio[i] * audio[i];
  float rms = std::sqrt(sumSq / static_cast<float>(numFrames));
  if (rms <= 1e-9f) return 0.0f;

  // Convert to dB SPL (assume 0 dBFS = 94 dB SPL)
  float dBSPL = 94.0f + 20.0f * std::log10(rms);

  // ISO 532-1 simplified: at 1 kHz, 1 phon = 1 dB SPL
  // Use equal-loudness correction at broadband (roughly 3.5 kHz weighted)
  float phons = dBSPL;  // simplified

  // Convert phons to sones: N = 2^((phons - 40) / 10) for phons >= 40
  if (phons >= 40.0f)
    return std::pow(2.0f, (phons - 40.0f) / 10.0f);
  else
    return std::pow(phons / 40.0f, 2.642f);
}

float PsychoacousticEngine::computeBarkSpread(
    const float* spectrum, int numBins) const
{
  int n = std::min(numBins, numBins_);
  float totalPower = 0.0f, weightedBark = 0.0f, weightedBark2 = 0.0f;
  float binHz = static_cast<float>(sampleRate_) / static_cast<float>(fftSize_);

  for (int k = 1; k < n; ++k) {
    float freqHz = k * binHz;
    float bark = hzToBark(freqHz);
    float power = spectrum[k];
    totalPower += power;
    weightedBark  += bark * power;
    weightedBark2 += bark * bark * power;
  }
  if (totalPower <= 0.0f) return 0.0f;
  float meanBark  = weightedBark / totalPower;
  float meanBark2 = weightedBark2 / totalPower;
  return std::sqrt(std::max(0.0f, meanBark2 - meanBark * meanBark));
}

}  // namespace aurora
