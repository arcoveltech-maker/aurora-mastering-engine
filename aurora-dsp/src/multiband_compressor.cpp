#include "aurora/multiband_compressor.h"
#include <cmath>
#include <algorithm>

namespace aurora {

static constexpr float kPi = 3.14159265358979f;

MultibandCompressor::MultibandCompressor(int sampleRate) : sampleRate_(sampleRate) {
  BiquadCoeffs lp, hp;
  computeLR4Coeffs(100.0f,  lp, hp);
  for (auto& f : xoLp1_) f.setCoefficients(lp);
  for (auto& f : xoHp1_) f.setCoefficients(hp);

  computeLR4Coeffs(1000.0f, lp, hp);
  for (auto& f : xoLp2_) f.setCoefficients(lp);
  for (auto& f : xoHp2_) f.setCoefficients(hp);

  computeLR4Coeffs(8000.0f, lp, hp);
  for (auto& f : xoLp3_) f.setCoefficients(lp);
  for (auto& f : xoHp3_) f.setCoefficients(hp);
}

void MultibandCompressor::computeLR4Coeffs(float freqHz,
                                            BiquadCoeffs& lpOut,
                                            BiquadCoeffs& hpOut) const {
  // Butterworth 2nd-order LP/HP, then cascade twice for LR4
  float w0 = 2.0f * kPi * freqHz / static_cast<float>(sampleRate_);
  float cos_w0 = std::cos(w0);
  float sin_w0 = std::sin(w0);
  float alpha = sin_w0 * 0.70710678118f;  // Q = 1/sqrt(2)

  // Low-pass
  float b0 =  (1.0f - cos_w0) / 2.0f;
  float b1 =   1.0f - cos_w0;
  float b2 =  (1.0f - cos_w0) / 2.0f;
  float a0 =   1.0f + alpha;
  float a1 =  -2.0f * cos_w0;
  float a2 =   1.0f - alpha;
  lpOut = {b0/a0, b1/a0, b2/a0, a1/a0, a2/a0};

  // High-pass
  b0 =  (1.0f + cos_w0) / 2.0f;
  b1 = -(1.0f + cos_w0);
  b2 =  (1.0f + cos_w0) / 2.0f;
  hpOut = {b0/a0, b1/a0, b2/a0, a1/a0, a2/a0};
}

void MultibandCompressor::setBand(int band, const CompressorBand& params) {
  if (band >= 0 && band < kNumBands) bands_[band] = params;
}

float MultibandCompressor::dbToLin(float db) const {
  return std::pow(10.0f, db / 20.0f);
}

float MultibandCompressor::linToDb(float lin) const {
  return 20.0f * std::log10(std::max(1e-9f, lin));
}

float MultibandCompressor::computeGainReduction(int band, float inputDb) const {
  const auto& b = bands_[band];
  float knee2 = b.kneeDb / 2.0f;
  float gr = 0.0f;

  if (inputDb < b.thresholdDb - knee2) {
    gr = 0.0f;
  } else if (inputDb > b.thresholdDb + knee2) {
    gr = (b.thresholdDb - inputDb) * (1.0f - 1.0f / b.ratio);
  } else {
    // Soft knee
    float diff = inputDb - b.thresholdDb + knee2;
    gr = (diff * diff) / (2.0f * b.kneeDb) * (1.0f - 1.0f / b.ratio);
    gr = -gr;
  }
  return gr;  // negative dB (gain reduction)
}

void MultibandCompressor::process(float* buffer, int numFrames, int numChannels) {
  float attackCoeff[kNumBands], releaseCoeff[kNumBands];
  for (int b = 0; b < kNumBands; ++b) {
    float attackSamples  = bands_[b].attackMs  * 0.001f * static_cast<float>(sampleRate_);
    float releaseSamples = bands_[b].releaseMs * 0.001f * static_cast<float>(sampleRate_);
    attackCoeff[b]  = std::exp(-1.0f / (attackSamples  + 1e-6f));
    releaseCoeff[b] = std::exp(-1.0f / (releaseSamples + 1e-6f));
  }

  for (int i = 0; i < numFrames; ++i) {
    float* frame = buffer + i * numChannels;
    float mono = frame[0];
    if (numChannels > 1) mono = (mono + frame[1]) * 0.5f;

    // Split into 4 bands via LR4 crossovers
    // Band 0: LP@100
    float b0sig = xoLp1_[1].process(xoLp1_[0].process(mono));
    // Band 1: HP@100, LP@1k
    float tmp1  = xoHp1_[1].process(xoHp1_[0].process(mono));
    float b1sig = xoLp2_[1].process(xoLp2_[0].process(tmp1));
    // Band 2: HP@1k, LP@8k
    float tmp2  = xoHp2_[1].process(xoHp2_[0].process(tmp1));
    float b2sig = xoLp3_[1].process(xoLp3_[0].process(tmp2));
    // Band 3: HP@8k
    float b3sig = xoHp3_[1].process(xoHp3_[0].process(tmp2));

    float bandSig[kNumBands] = {b0sig, b1sig, b2sig, b3sig};
    float output = 0.0f;

    for (int b = 0; b < kNumBands; ++b) {
      float sig  = bandSig[b];
      float envDb = linToDb(std::abs(sig) + 1e-9f);
      float grDb  = computeGainReduction(b, envDb);
      float target = dbToLin(grDb + bands_[b].makeupGainDb);

      // Envelope smoothing
      float coeff = (target < envelopes_[b]) ? attackCoeff[b] : releaseCoeff[b];
      envelopes_[b] = coeff * envelopes_[b] + (1.0f - coeff) * target;
      output += sig * envelopes_[b];
    }

    for (int ch = 0; ch < numChannels; ++ch)
      frame[ch] = output;
  }
}

void MultibandCompressor::reset() {
  for (auto& e : envelopes_) e = 1.0f;
  for (auto& f : xoLp1_) f.reset();
  for (auto& f : xoHp1_) f.reset();
  for (auto& f : xoLp2_) f.reset();
  for (auto& f : xoHp2_) f.reset();
  for (auto& f : xoLp3_) f.reset();
  for (auto& f : xoHp3_) f.reset();
}

}  // namespace aurora
