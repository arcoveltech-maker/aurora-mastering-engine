#include "aurora/ms_processing.h"
#include <cmath>

namespace aurora {

float MSProcessor::dbToLin(float db) {
  return std::pow(10.0f, db / 20.0f);
}

void MSProcessor::encode(float l, float r, float& mid, float& side) {
  mid  = (l + r) * 0.70710678118f;  // / sqrt(2)
  side = (l - r) * 0.70710678118f;
}

void MSProcessor::decode(float mid, float side, float& l, float& r) {
  l = (mid + side) * 0.70710678118f;
  r = (mid - side) * 0.70710678118f;
}

void MSProcessor::processStereoFrame(float& l, float& r) const {
  float mid, side;
  encode(l, r, mid, side);

  mid  *= midGainLin_;
  side *= sideGainLin_ * width_;

  decode(mid, side, l, r);
}

}  // namespace aurora
