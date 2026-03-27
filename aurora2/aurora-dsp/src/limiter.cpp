#include "aurora/limiter.h"
#include <cmath>
#include <algorithm>

namespace aurora {

SAILLimiter::SAILLimiter(int sampleRate, int numChannels)
    : sampleRate_(sampleRate), numChannels_(numChannels) {
  setLookaheadMs(5.0f);
  setReleaseMs(100.0f);
  // Pre-fill lookahead buffer with silence
  for (int i = 0; i < lookaheadSamples_; ++i)
    lookaheadBuf_.push_back(std::vector<float>(numChannels_, 0.0f));
}

void SAILLimiter::setCeilingDBTP(float ceilingDBTP) {
  ceilingLin_ = std::pow(10.0f, ceilingDBTP / 20.0f);
}

void SAILLimiter::setLookaheadMs(float ms) {
  lookaheadSamples_ = static_cast<int>(ms * sampleRate_ / 1000.0f);
  while (static_cast<int>(lookaheadBuf_.size()) < lookaheadSamples_)
    lookaheadBuf_.push_front(std::vector<float>(numChannels_, 0.0f));
  while (static_cast<int>(lookaheadBuf_.size()) > lookaheadSamples_)
    lookaheadBuf_.pop_front();
}

void SAILLimiter::setReleaseMs(float ms) {
  releaseCoeff_ = std::exp(-1.0f / (ms * sampleRate_ / 1000.0f));
}

void SAILLimiter::reset() {
  lookaheadBuf_.clear();
  for (int i = 0; i < lookaheadSamples_; ++i)
    lookaheadBuf_.push_back(std::vector<float>(numChannels_, 0.0f));
  gainEnv_ = 1.0f;
  gainReductionDB_ = 0.0f;
}

bool SAILLimiter::processFrame(float* frame) {
  // Push incoming frame into lookahead
  std::vector<float> incoming(frame, frame + numChannels_);
  lookaheadBuf_.push_back(incoming);

  // Detect peak across channels in incoming frame
  float peak = 0.0f;
  for (int c = 0; c < numChannels_; ++c)
    peak = std::max(peak, std::fabs(frame[c]));

  // Compute required gain to stay at ceiling
  float targetGain = (peak > ceilingLin_) ? ceilingLin_ / peak : 1.0f;

  // Attack: instant attack (look-ahead covers transient)
  if (targetGain < gainEnv_)
    gainEnv_ = targetGain;
  else
    gainEnv_ = 1.0f - releaseCoeff_ * (1.0f - gainEnv_);

  gainEnv_ = std::min(gainEnv_, 1.0f);

  // Output delayed frame (front of lookahead)
  auto& delayed = lookaheadBuf_.front();
  bool limited = false;
  for (int c = 0; c < numChannels_; ++c) {
    frame[c] = delayed[c] * gainEnv_;
    if (gainEnv_ < 0.9999f) limited = true;
  }
  lookaheadBuf_.pop_front();

  gainReductionDB_ = 20.0f * std::log10(std::max(gainEnv_, 1e-9f));
  return limited;
}

}  // namespace aurora
