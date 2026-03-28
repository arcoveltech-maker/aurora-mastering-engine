#include "aurora/binaural.h"
#include <cmath>
#include <algorithm>

namespace aurora {

static constexpr float kPi = 3.14159265358979f;

BinauralRenderer::BinauralRenderer(int sampleRate)
    : sampleRate_(sampleRate)
{
  histL_.assign(kHRTFLength, 0.0f);
  histR_.assign(kHRTFLength, 0.0f);
  updateHRTF();
}

float BinauralRenderer::sphericalHeadITD(float azRad) const {
  // Woodworth-Schlosberg spherical head model
  // Head radius ~8.75 cm
  const float headRadius = 0.0875f;
  const float speedOfSound = 343.0f;
  float itd = (headRadius / speedOfSound) * (azRad + std::sin(azRad));
  return itd;  // seconds
}

void BinauralRenderer::updateHRTF() {
  float azRad  = azimuth_   * (kPi / 180.0f);
  float elRad  = elevation_ * (kPi / 180.0f);
  float itd    = sphericalHeadITD(azRad);  // seconds
  int   itdSamples = static_cast<int>(itd * static_cast<float>(sampleRate_));

  // Generate analytical HRTF using minimum-phase approximation
  // Left ear: attenuated/delayed when source is to the right
  // Right ear: boosted/earlier when source is to the right

  // Inter-aural level difference (dB) — simplified pinna model
  float ild = 8.5f * std::sin(azRad) * std::cos(elRad);  // dB

  float gainL = std::pow(10.0f, -ild / 20.0f);
  float gainR = std::pow(10.0f,  ild / 20.0f);

  // Simple windowed sinc FIR impulse response
  for (int i = 0; i < kHRTFLength; ++i) {
    float t = static_cast<float>(i) / static_cast<float>(sampleRate_);
    // Hanning window
    float window = 0.5f * (1.0f - std::cos(2.0f * kPi * i / (kHRTFLength - 1)));
    // Delta + comb for early reflections
    hrtfL_[i] = (i == std::max(0, itdSamples)  ? gainL : 0.0f) * window;
    hrtfR_[i] = (i == std::max(0, -itdSamples) ? gainR : 0.0f) * window;
  }
  hrtfL_[0] += (itdSamples >= 0) ? 0.0f : gainL;
  hrtfR_[0] += (itdSamples <= 0) ? 0.0f : gainR;
}

void BinauralRenderer::setAzimuth(float degrees) {
  azimuth_ = degrees;
  updateHRTF();
}

void BinauralRenderer::setElevation(float degrees) {
  elevation_ = degrees;
  updateHRTF();
}

void BinauralRenderer::convolveFIR(const float* input, const float* ir, float* history,
                                    float* output, int numFrames) const {
  for (int i = 0; i < numFrames; ++i) {
    // Shift history
    for (int k = kHRTFLength - 1; k > 0; --k)
      history[k] = history[k - 1];
    history[0] = input[i];

    // Convolve
    float out = 0.0f;
    for (int k = 0; k < kHRTFLength; ++k)
      out += history[k] * ir[k];
    output[i] = out;
  }
}

void BinauralRenderer::process(const float* input, float* outL, float* outR, int numFrames) {
  convolveFIR(input, hrtfL_.data(), histL_.data(), outL, numFrames);
  convolveFIR(input, hrtfR_.data(), histR_.data(), outR, numFrames);
}

void BinauralRenderer::reset() {
  std::fill(histL_.begin(), histL_.end(), 0.0f);
  std::fill(histR_.begin(), histR_.end(), 0.0f);
}

}  // namespace aurora
