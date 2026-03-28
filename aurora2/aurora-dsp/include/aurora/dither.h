#pragma once
#include <cstdint>

namespace aurora {

enum class DitherType { NONE, RPDF, TPDF };

// TPDF dither for final output quantization
class Dither {
 public:
  Dither() = default;
  void setType(DitherType type) { type_ = type; }
  void setBitDepth(int bits) { amplitude_ = 1.0f / (1 << (bits - 1)); }

  float process(float in);

 private:
  DitherType type_ = DitherType::TPDF;
  float amplitude_ = 1.0f / 32768.0f;  // 16-bit default
  uint32_t rng_ = 0x12345678u;

  float rand01();  // [0, 1)
};

}  // namespace aurora
