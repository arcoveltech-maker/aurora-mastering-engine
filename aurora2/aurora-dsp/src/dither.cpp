#include "aurora/dither.h"

namespace aurora {

float Dither::rand01() {
  // Xorshift32
  rng_ ^= rng_ << 13;
  rng_ ^= rng_ >> 17;
  rng_ ^= rng_ << 5;
  return static_cast<float>(rng_) / static_cast<float>(0xFFFFFFFFu);
}

float Dither::process(float in) {
  switch (type_) {
    case DitherType::NONE:
      return in;
    case DitherType::RPDF:
      return in + (rand01() - 0.5f) * amplitude_;
    case DitherType::TPDF:
      // Triangular PDF = sum of two rectangular PDFs
      return in + (rand01() - rand01()) * amplitude_;
  }
  return in;
}

}  // namespace aurora
