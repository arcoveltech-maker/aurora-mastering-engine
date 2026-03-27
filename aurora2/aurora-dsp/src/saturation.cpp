#include "aurora/saturation.h"
#include <cmath>
#include <algorithm>

namespace aurora {

float Saturation::process(float in) const {
  if (drive_ < 1e-6f && mix_ < 1e-6f) return in;

  float driven = in * (1.0f + drive_ * 8.0f);
  float sat;

  switch (mode_) {
    case SaturationMode::TAPE:
      // Soft-knee tanh saturation
      sat = std::tanh(driven);
      break;
    case SaturationMode::TUBE:
      // Asymmetric soft clipping (tube-like)
      if (driven >= 0.0f)
        sat = 1.0f - std::exp(-driven);
      else
        sat = -1.0f + std::exp(driven * 0.5f);
      break;
    case SaturationMode::CLIP:
      // Hard clip with slight knee
      sat = std::clamp(driven, -0.999f, 0.999f);
      break;
  }

  // Compensate gain for drive
  float compensated = sat / (1.0f + drive_ * 0.5f);
  return in * (1.0f - mix_) + compensated * mix_;
}

}  // namespace aurora
