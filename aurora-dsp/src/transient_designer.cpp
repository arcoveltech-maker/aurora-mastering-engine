#include "aurora/transient_designer.h"
#include <cmath>
#include <algorithm>

namespace aurora {

static float makeCoeff(float ms, int sr) {
  return std::exp(-1.0f / (ms * 0.001f * static_cast<float>(sr) + 1e-6f));
}

TransientDesigner::TransientDesigner(int sampleRate) : sampleRate_(sampleRate) {
  fastAttCoeff_ = makeCoeff(1.0f,   sampleRate);
  fastRelCoeff_ = makeCoeff(50.0f,  sampleRate);
  slowAttCoeff_ = makeCoeff(100.0f, sampleRate);
  slowRelCoeff_ = makeCoeff(400.0f, sampleRate);
}

void TransientDesigner::setParams(float attackGainDb, float sustainGainDb) {
  attackGainDb_  = std::max(-12.0f, std::min(12.0f, attackGainDb));
  sustainGainDb_ = std::max(-12.0f, std::min(12.0f, sustainGainDb));
}

void TransientDesigner::process(float* buffer, int numFrames, int numChannels) {
  float attackGain  = std::pow(10.0f, attackGainDb_  / 20.0f);
  float sustainGain = std::pow(10.0f, sustainGainDb_ / 20.0f);

  for (int i = 0; i < numFrames; ++i) {
    float* frame = buffer + i * numChannels;

    // Mono level detection
    float level = std::abs(frame[0]);
    if (numChannels > 1) level = std::max(level, std::abs(frame[1]));

    // Fast envelope
    float fastCoeff = (level > envFast_) ? fastAttCoeff_ : fastRelCoeff_;
    envFast_ = fastCoeff * envFast_ + (1.0f - fastCoeff) * level;

    // Slow envelope
    float slowCoeff = (level > envSlow_) ? slowAttCoeff_ : slowRelCoeff_;
    envSlow_ = slowCoeff * envSlow_ + (1.0f - slowCoeff) * level;

    // Transient = fast > slow (transient region)
    float transientRatio = (envSlow_ > 1e-9f) ? (envFast_ / envSlow_) : 1.0f;
    transientRatio = std::max(0.0f, std::min(2.0f, transientRatio));

    // Blend: high transientRatio → apply attackGain, low → sustainGain
    float blend = std::min(1.0f, std::max(0.0f, transientRatio - 1.0f));
    float gain = sustainGain * (1.0f - blend) + attackGain * blend;

    for (int ch = 0; ch < numChannels; ++ch)
      frame[ch] *= gain;
  }
}

void TransientDesigner::reset() {
  envFast_ = 0.0f;
  envSlow_ = 0.0f;
}

}  // namespace aurora
