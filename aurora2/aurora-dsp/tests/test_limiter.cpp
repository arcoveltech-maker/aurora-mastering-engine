#include <gtest/gtest.h>
#include "aurora/limiter.h"
#include <cmath>
#include <algorithm>

namespace aurora {

TEST(SAILLimiterTest, NeverExceedsCeiling) {
  SAILLimiter limiter(48000, 2);
  limiter.setCeilingDBTP(-1.0f);

  float ceilingLin = std::pow(10.0f, -1.0f / 20.0f);
  const int N = 48000;

  for (int i = 0; i < N; ++i) {
    // Loud transients
    float s = (i % 100 == 0) ? 2.0f : 0.1f;
    float frame[2] = {s, s};
    limiter.processFrame(frame);
    EXPECT_LE(std::fabs(frame[0]), ceilingLin * 1.001f);
    EXPECT_LE(std::fabs(frame[1]), ceilingLin * 1.001f);
  }
}

TEST(SAILLimiterTest, ReportsGainReduction) {
  SAILLimiter limiter(48000, 2);
  limiter.setCeilingDBTP(-1.0f);
  float frame[2] = {2.0f, 2.0f};
  for (int i = 0; i < 500; ++i) limiter.processFrame(frame);
  EXPECT_LT(limiter.getGainReductionDB(), -0.5f);
}

}  // namespace aurora
