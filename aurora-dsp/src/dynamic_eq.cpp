#include "aurora/dynamic_eq.h"
#include <cmath>
#include <algorithm>

namespace aurora {

static constexpr float kPi = 3.14159265358979f;

DynamicEQ::DynamicEQ(int sampleRate) : sampleRate_(sampleRate) {}

void DynamicEQ::computePeakCoeffs(float freqHz, float qFactor, float gainDb,
                                   BiquadCoeffs& out) const {
  float A  = std::pow(10.0f, gainDb / 40.0f);
  float w0 = 2.0f * kPi * freqHz / static_cast<float>(sampleRate_);
  float cos_w0 = std::cos(w0);
  float sin_w0 = std::sin(w0);
  float alpha = sin_w0 / (2.0f * qFactor);

  float b0 =  1.0f + alpha * A;
  float b1 = -2.0f * cos_w0;
  float b2 =  1.0f - alpha * A;
  float a0 =  1.0f + alpha / A;
  float a1 = -2.0f * cos_w0;
  float a2 =  1.0f - alpha / A;

  out = {b0/a0, b1/a0, b2/a0, a1/a0, a2/a0};
}

void DynamicEQ::setBand(int band, const DynamicEQBand& params) {
  if (band < 0 || band >= kMaxBands) return;
  bands_[band] = params;
  numBands_ = std::max(numBands_, band + 1);
  // Initialize static gain filter
  BiquadCoeffs c;
  computePeakCoeffs(params.freqHz, params.qFactor, params.staticGainDb, c);
  peakFilters_[band].setCoefficients(c);
}

void DynamicEQ::process(float* buffer, int numFrames, int numChannels) {
  for (int i = 0; i < numFrames; ++i) {
    float* frame = buffer + i * numChannels;

    for (int b = 0; b < numBands_; ++b) {
      const auto& band = bands_[b];
      float mono = frame[0];
      if (numChannels > 1) mono = (mono + frame[1]) * 0.5f;

      // Level detection (RMS-ish via envelope follower)
      float level = std::abs(mono);
      float levelDb = 20.0f * std::log10(level + 1e-9f);

      // Compute desired gain modulation
      float drive = 0.0f;
      if (levelDb > band.thresholdDb) {
        drive = (levelDb - band.thresholdDb) / band.ratio;
        drive = std::min(drive, band.dynamicGainDb);
      }
      if (band.expand) drive = -drive;  // negative = cut when loud

      // Smooth envelope
      float attackSamples  = band.attackMs  * 0.001f * static_cast<float>(sampleRate_);
      float releaseSamples = band.releaseMs * 0.001f * static_cast<float>(sampleRate_);
      float atkCoeff = std::exp(-1.0f / (attackSamples  + 1e-6f));
      float relCoeff = std::exp(-1.0f / (releaseSamples + 1e-6f));
      float coeff = (drive > envelopes_[b]) ? atkCoeff : relCoeff;
      envelopes_[b] = coeff * envelopes_[b] + (1.0f - coeff) * drive;

      // Recompute biquad with total gain
      float totalGain = band.staticGainDb + envelopes_[b];
      BiquadCoeffs c;
      computePeakCoeffs(band.freqHz, band.qFactor, totalGain, c);
      peakFilters_[b].setCoefficients(c);

      // Apply to all channels
      for (int ch = 0; ch < numChannels; ++ch)
        frame[ch] = peakFilters_[b].process(frame[ch]);
    }
  }
}

void DynamicEQ::reset() {
  for (int b = 0; b < kMaxBands; ++b) {
    envelopes_[b] = 0.0f;
    peakFilters_[b].reset();
  }
}

}  // namespace aurora
