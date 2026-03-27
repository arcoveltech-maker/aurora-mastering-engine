#include <gtest/gtest.h>
#include "aurora/lufs.h"
#include <cmath>

TEST(LUFSTest, SilenceIsLow) {
  aurora::LUFSMeter meter(48000, 2);
  float frame[] = {0.0f, 0.0f};
  for (int i = 0; i < 4800; ++i) meter.processFrame(frame);
  EXPECT_LT(meter.getIntegratedLUFS(), -60.0);
}

TEST(LUFSTest, LoudSignalAboveThreshold) {
  aurora::LUFSMeter meter(48000, 2);
  for (int i = 0; i < 48000; ++i) {
    float s = 0.5f * std::sin(2.0f * 3.14159f * 440.0f * i / 48000.0f);
    float frame[] = {s, s};
    meter.processFrame(frame);
  }
  double lufs = meter.getIntegratedLUFS();
  EXPECT_GT(lufs, -30.0);
  EXPECT_LT(lufs, 0.0);
}

TEST(LUFSTest, ResetClearsAccumulator) {
  aurora::LUFSMeter meter(48000, 2);
  float loud[] = {0.9f, 0.9f};
  for (int i = 0; i < 4800; ++i) meter.processFrame(loud);
  meter.reset();
  float silent[] = {0.0f, 0.0f};
  for (int i = 0; i < 100; ++i) meter.processFrame(silent);
  EXPECT_LT(meter.getIntegratedLUFS(), -60.0);
}

TEST(KWeightingTest, ProcessesSample) {
  aurora::KWeightingFilter f(48000);
  float out = f.process(1.0f);
  EXPECT_NE(out, 0.0f);  // impulse response is non-zero
}
