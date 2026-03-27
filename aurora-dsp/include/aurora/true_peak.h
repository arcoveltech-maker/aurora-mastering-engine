#pragma once
#include <array>

namespace aurora {

// TruePeakMeter measures inter-sample peaks per ITU-R BS.1770-4 / AES-17.
// Uses 4x oversampling via cubic Hermite interpolation to detect peaks that
// lie between sample points (which can exceed the digital full scale by up
// to ~3 dBTP on worst-case signals).
class TruePeakMeter {
 public:
  TruePeakMeter(int sampleRate, int numChannels);
  void processFrame(const float* frame);   // one interleaved frame
  void reset();
  double getTruePeakDBTP() const;
  bool exceedsCeiling(double ceilingDBTP) const;
 private:
  int sampleRate_ = 48000;
  int numChannels_ = 2;
  double maxLinear_ = 0.0;
  // History buffer: last 4 samples per channel for cubic Hermite interpolation
  static constexpr int kHistory = 4;
  std::array<double, 2 * kHistory> history_{};  // [ch0 x4, ch1 x4]

  // Evaluate a cubic Hermite spline at fractional position t in [0,1]
  // using four consecutive samples p0..p3 (p1 and p2 straddle the interval).
  static double hermite(double p0, double p1, double p2, double p3, double t) noexcept;
};

}  // namespace aurora
