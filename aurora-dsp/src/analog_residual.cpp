#include "aurora/analog_residual.h"
#include <cmath>
#include <algorithm>
#include <cstdio>

namespace aurora {

// NORMALIZATION_VALIDATED=false — heuristic waveshaper used
static constexpr bool NORMALIZATION_VALIDATED = false;

AnalogResidual::AnalogResidual(int sampleRate) : sampleRate_(sampleRate) {
  // Micro-drift LFO: ~0.2 Hz
  driftRate_ = 2.0f * 3.14159265f * 0.2f / static_cast<float>(sampleRate);
  if (!NORMALIZATION_VALIDATED) {
    std::fprintf(stderr,
      "[aurora] analog_residual: NORMALIZATION_VALIDATED=false, "
      "using heuristic waveshaper\n");
  }
}

void AnalogResidual::setDrive(float drive) {
  drive_ = std::max(0.0f, std::min(1.0f, drive));
}

float AnalogResidual::waveshape(float x, float drive) const {
  // Soft-clip waveshaper: tanh with drive gain
  float gain = 1.0f + drive * 5.0f;
  return std::tanh(x * gain) / std::tanh(gain);
}

void AnalogResidual::process(float* buffer, int numFrames, int numChannels) {
  if (drive_ < 0.001f) return;  // Pass-through when drive is negligible

  for (int i = 0; i < numFrames; ++i) {
    float* frame = buffer + i * numChannels;

    // Micro-drift: very slight pitch/timing instability
    driftPhase_ += driftRate_;
    if (driftPhase_ > 2.0f * 3.14159265f) driftPhase_ -= 2.0f * 3.14159265f;
    float drift = drive_ * 0.0002f * std::sin(driftPhase_);

    for (int ch = 0; ch < numChannels; ++ch) {
      float x = frame[ch];
      // DC-coupled input: remove DC offset accumulated by waveshaper
      float ws = waveshape(x + drift, drive_ * 0.5f);
      // Simple DC-blocking high-pass (1-pole at ~5 Hz)
      float dcCoeff = std::exp(-2.0f * 3.14159265f * 5.0f /
                                static_cast<float>(sampleRate_));
      dcState_[ch] = dcCoeff * dcState_[ch] + (1.0f - dcCoeff) * ws;
      frame[ch] = ws - dcState_[ch];
    }
  }
}

void AnalogResidual::reset() {
  driftPhase_ = 0.0f;
  dcState_[0] = dcState_[1] = 0.0f;
}

}  // namespace aurora
