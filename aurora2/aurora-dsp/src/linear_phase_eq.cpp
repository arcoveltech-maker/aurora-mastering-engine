#include "aurora/linear_phase_eq.h"
#include <cmath>

namespace aurora {

static constexpr double kPi = 3.14159265358979323846;

LinearPhaseEQ::LinearPhaseEQ(int sampleRate) : sampleRate_(sampleRate) {
  for (int i = 0; i < kNumBands; ++i) rebuildBand(i);
}

void LinearPhaseEQ::setBand(int band, const EQBand& params) {
  if (band < 0 || band >= kNumBands) return;
  bands_[band] = params;
  rebuildBand(band);
}

void LinearPhaseEQ::reset() {
  for (auto& f : filtersL_) f.reset();
  for (auto& f : filtersR_) f.reset();
}

float LinearPhaseEQ::processSample(float in, int channel) {
  float out = in;
  auto& filters = (channel == 0) ? filtersL_ : filtersR_;
  for (int i = 0; i < kNumBands; ++i) {
    if (bands_[i].enabled) out = filters[i].process(out);
  }
  return out;
}

BiquadCoeffs LinearPhaseEQ::calcCoeffs(const EQBand& b) const {
  double w0 = 2.0 * kPi * b.freqHz / sampleRate_;
  double cosW = std::cos(w0);
  double sinW = std::sin(w0);
  double A = std::pow(10.0, b.gainDB / 40.0);
  double alpha = sinW / (2.0 * b.q);
  double alphaA = sinW / 2.0 * std::sqrt((A + 1.0 / A) * (1.0 / 0.9 - 1.0) + 2.0);

  BiquadCoeffs c{};
  double a0 = 1.0;

  switch (b.type) {
    case EQBand::Type::PEAK: {
      double aAlpha = alpha / A;
      double bAlpha = alpha * A;
      a0 = 1.0 + aAlpha;
      c.b0 = (1.0 + bAlpha) / a0;
      c.b1 = (-2.0 * cosW) / a0;
      c.b2 = (1.0 - bAlpha) / a0;
      c.a1 = (-2.0 * cosW) / a0;
      c.a2 = (1.0 - aAlpha) / a0;
      break;
    }
    case EQBand::Type::LOWSHELF: {
      alphaA = sinW / 2.0 * std::sqrt((A + 1.0 / A) * (1.0 / 0.9 - 1.0) + 2.0);
      a0 = (A + 1.0) + (A - 1.0) * cosW + 2.0 * std::sqrt(A) * alphaA;
      c.b0 = A * ((A + 1.0) - (A - 1.0) * cosW + 2.0 * std::sqrt(A) * alphaA) / a0;
      c.b1 = 2.0 * A * ((A - 1.0) - (A + 1.0) * cosW) / a0;
      c.b2 = A * ((A + 1.0) - (A - 1.0) * cosW - 2.0 * std::sqrt(A) * alphaA) / a0;
      c.a1 = -2.0 * ((A - 1.0) + (A + 1.0) * cosW) / a0;
      c.a2 = ((A + 1.0) + (A - 1.0) * cosW - 2.0 * std::sqrt(A) * alphaA) / a0;
      break;
    }
    case EQBand::Type::HIGHSHELF: {
      alphaA = sinW / 2.0 * std::sqrt((A + 1.0 / A) * (1.0 / 0.9 - 1.0) + 2.0);
      a0 = (A + 1.0) - (A - 1.0) * cosW + 2.0 * std::sqrt(A) * alphaA;
      c.b0 = A * ((A + 1.0) + (A - 1.0) * cosW + 2.0 * std::sqrt(A) * alphaA) / a0;
      c.b1 = -2.0 * A * ((A - 1.0) + (A + 1.0) * cosW) / a0;
      c.b2 = A * ((A + 1.0) + (A - 1.0) * cosW - 2.0 * std::sqrt(A) * alphaA) / a0;
      c.a1 = 2.0 * ((A - 1.0) - (A + 1.0) * cosW) / a0;
      c.a2 = ((A + 1.0) - (A - 1.0) * cosW - 2.0 * std::sqrt(A) * alphaA) / a0;
      break;
    }
    case EQBand::Type::LOWPASS: {
      a0 = 1.0 + alpha;
      c.b0 = (1.0 - cosW) / 2.0 / a0;
      c.b1 = (1.0 - cosW) / a0;
      c.b2 = (1.0 - cosW) / 2.0 / a0;
      c.a1 = -2.0 * cosW / a0;
      c.a2 = (1.0 - alpha) / a0;
      break;
    }
    case EQBand::Type::HIGHPASS: {
      a0 = 1.0 + alpha;
      c.b0 = (1.0 + cosW) / 2.0 / a0;
      c.b1 = -(1.0 + cosW) / a0;
      c.b2 = (1.0 + cosW) / 2.0 / a0;
      c.a1 = -2.0 * cosW / a0;
      c.a2 = (1.0 - alpha) / a0;
      break;
    }
  }
  return c;
}

void LinearPhaseEQ::rebuildBand(int band) {
  BiquadCoeffs c = calcCoeffs(bands_[band]);
  filtersL_[band].setCoefficients(c);
  filtersR_[band].setCoefficients(c);
}

}  // namespace aurora
