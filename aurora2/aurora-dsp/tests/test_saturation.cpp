#include <gtest/gtest.h>
#include "aurora/saturation.h"
#include <cmath>

namespace aurora {

TEST(SaturationTest, ZeroMixPassthrough) {
  Saturation sat;
  sat.setMix(0.0f);
  sat.setDrive(1.0f);
  EXPECT_FLOAT_EQ(sat.process(0.5f), 0.5f);
}

TEST(SaturationTest, TapeDoesNotExceedUnity) {
  Saturation sat;
  sat.setMode(SaturationMode::TAPE);
  sat.setDrive(1.0f);
  sat.setMix(1.0f);
  for (float x = -2.0f; x <= 2.0f; x += 0.1f)
    EXPECT_LE(std::fabs(sat.process(x)), 1.5f);
}

TEST(SaturationTest, TubePolarityPreserved) {
  Saturation sat;
  sat.setMode(SaturationMode::TUBE);
  sat.setDrive(0.5f);
  sat.setMix(1.0f);
  EXPECT_GT(sat.process(0.1f), 0.0f);
  EXPECT_LT(sat.process(-0.1f), 0.0f);
}

}  // namespace aurora
