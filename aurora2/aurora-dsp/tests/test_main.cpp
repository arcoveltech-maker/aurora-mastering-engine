#include <gtest/gtest.h>
#include "aurora/engine.h"
#include "aurora/true_peak.h"

TEST(SanityTest, EngineVersion) {
  EXPECT_EQ(aurora::AuroraDSPEngine::getVersion(), "5.0.0");
}

TEST(SanityTest, TruePeakBasic) {
  aurora::TruePeakMeter tp(48000, 2);
  float frame[] = {0.5f, -0.5f};
  tp.processFrame(frame);
  EXPECT_GT(tp.getTruePeakDBTP(), -10.0);
}
