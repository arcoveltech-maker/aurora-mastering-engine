#pragma once
#include <vector>
#include <array>

namespace aurora {

// HRTF-based binaural renderer.
// For v5.0: uses a simple analytical HRTF model (spherical-head approximation).
// Full implementation would use MIT KEMAR or SADIE II HRTF datasets.
class BinauralRenderer {
 public:
  static constexpr int kHRTFLength = 128;

  explicit BinauralRenderer(int sampleRate);

  // Update listener head-related parameters
  void setAzimuth(float degrees);    // 0 = front, 90 = right
  void setElevation(float degrees);  // 0 = horizontal, +90 = above

  // Process mono → stereo binaural (left and right outputs)
  void process(const float* input, float* outL, float* outR, int numFrames);
  void reset();

 private:
  int   sampleRate_;
  float azimuth_   = 0.0f;
  float elevation_ = 0.0f;

  // FIR HRTF impulse responses (left, right)
  std::array<float, kHRTFLength> hrtfL_{};
  std::array<float, kHRTFLength> hrtfR_{};

  // Overlap-save convolution state
  std::vector<float> histL_;
  std::vector<float> histR_;

  void updateHRTF();
  float sphericalHeadITD(float azRad) const;
  void convolveFIR(const float* input, const float* ir, float* history,
                   float* output, int numFrames) const;
};

}  // namespace aurora
