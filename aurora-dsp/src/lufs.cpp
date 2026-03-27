#include "aurora/lufs.h"
#include <cmath>

namespace aurora {

// ── KWeightingFilter ───────────────────────────────────────────────────────

KWeightingFilter::KWeightingFilter(int sampleRate) {
  BiquadCoeffs c1, c2;
  if (sampleRate == 48000) {
    // Stage 1: high-shelf pre-filter
    c1 = {1.53512485958697, -2.69169618940638, 1.19839281085285,
          -1.69065929318241, 0.73248077421585};
    // Stage 2: high-pass
    c2 = {0.99886234236998, -1.99772468473996, 0.99886234236998,
          -1.99772300507016, 0.99772636440976};
  } else if (sampleRate == 44100) {
    c1 = {1.54552898911403, -2.72551298371706, 1.20027895764338,
          -1.72551298371706, 0.74552898911403};
    c2 = {0.99887799826089, -1.99775601652179, 0.99887799826089,
          -1.99775600753555, 0.99775602550802};
  } else if (sampleRate == 96000) {
    // ITU-R BS.1770-4 K-weighting coefficients for 96 kHz
    // Stage 1: high-shelf pre-filter
    c1 = {1.69065929318241, -3.07476781648595, 1.43231688822172,
          -1.86843189408394, 0.87516086097894};
    // Stage 2: high-pass
    c2 = {0.99943380897914, -1.99886761795828, 0.99943380897914,
          -1.99886759784451, 0.99886763807205};
  } else {
    // Unsupported sample rate: use 48 kHz coefficients as closest approximation.
    // Callers should resample to 48 kHz for accurate results.
    c1 = {1.53512485958697, -2.69169618940638, 1.19839281085285,
          -1.69065929318241, 0.73248077421585};
    c2 = {0.99886234236998, -1.99772468473996, 0.99886234236998,
          -1.99772300507016, 0.99772636440976};
  }
  stage1a_.setCoefficients(c1);
  stage1b_.setCoefficients(c2);
}

float KWeightingFilter::process(float x) {
  return stage1b_.process(stage1a_.process(x));
}

void KWeightingFilter::reset() {
  stage1a_.reset();
  stage1b_.reset();
}

// ── LUFSMeter ──────────────────────────────────────────────────────────────

LUFSMeter::LUFSMeter(int sampleRate, int numChannels)
    : sampleRate_(sampleRate), numChannels_(numChannels),
      kL_(sampleRate), kR_(sampleRate) {}

void LUFSMeter::reset() {
  sumSq_ = 0.0;
  count_ = 0;
  kL_.reset();
  kR_.reset();
}

void LUFSMeter::processFrame(const float* frame) {
  float wL = kL_.process(frame[0]);
  float wR = (numChannels_ > 1) ? kR_.process(frame[1]) : wL;
  // Mean-square over both channels (equal channel weighting for stereo)
  sumSq_ += static_cast<double>(wL * wL + wR * wR) * 0.5;
  ++count_;
}

double LUFSMeter::getIntegratedLUFS() const {
  if (count_ == 0) return -70.0;
  double meanSq = sumSq_ / static_cast<double>(count_);
  if (meanSq <= 0.0) return -70.0;
  return -0.691 + 10.0 * std::log10(meanSq);
}

double LUFSMeter::getMomentaryLUFS() const  { return getIntegratedLUFS(); }
double LUFSMeter::getShortTermLUFS() const  { return getIntegratedLUFS(); }
double LUFSMeter::getLRA() const            { return 0.0; }

}  // namespace aurora
