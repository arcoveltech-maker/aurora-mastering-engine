#include <gtest/gtest.h>
#include "aurora/true_peak.h"
#include <cmath>

namespace aurora {

TEST(TruePeakTest, SilenceIsMinusInfinity) {
  TruePeakMeter meter(48000, 2);
  float frame[2] = {0.0f, 0.0f};
  for (int i = 0; i < 4800; ++i) meter.processFrame(frame);
  EXPECT_LT(meter.getTruePeakDBTP(), -100.0);
}

TEST(TruePeakTest, FullScaleSineApproachesZeroDBTP) {
  TruePeakMeter meter(48000, 2);
  for (int i = 0; i < 48000; ++i) {
    float s = std::sin(2.0f * 3.14159f * 1000.0f * i / 48000.0f);
    float frame[2] = {s, s};
    meter.processFrame(frame);
  }
  double tp = meter.getTruePeakDBTP();
  EXPECT_GE(tp, -3.0);
  EXPECT_LE(tp,  1.0);  // True peak can exceed 0 dBFS slightly
}

TEST(TruePeakTest, ExceedsCeiling) {
  TruePeakMeter meter(48000, 2);
  float frame[2] = {0.95f, 0.95f};
  for (int i = 0; i < 100; ++i) meter.processFrame(frame);
  EXPECT_TRUE(meter.exceedsCeiling(-1.0));
  EXPECT_FALSE(meter.exceedsCeiling(0.0));
}

}  // namespace aurora
