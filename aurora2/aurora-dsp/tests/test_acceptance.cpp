#include <gtest/gtest.h>
#include "aurora/engine.h"
#include <cmath>
#include <vector>

namespace aurora {

TEST(EngineAcceptanceTest, VersionIsCorrect) {
  EXPECT_EQ(AuroraDSPEngine::getVersion(), "5.0.0");
}

TEST(EngineAcceptanceTest, RenderTargetsLUFS) {
  AuroraDSPEngine engine(48000, 2);
  engine.setSessionParams(
    R"({"target_lufs": -14.0, "ceiling_dbtp": -1.0, "warmth": 0.2, "width": 1.0})"
  );

  const int N = 48000 * 5;  // 5 seconds
  std::vector<float> input(N * 2);
  std::vector<float> output(N * 2);

  // Generate -20 LUFS-ish sine tone
  for (int i = 0; i < N; ++i) {
    float s = 0.1f * std::sin(2.0f * 3.14159f * 440.0f * i / 48000.0f);
    input[i * 2]     = s;
    input[i * 2 + 1] = s;
  }

  engine.renderFull(input.data(), output.data(), N);

  double lufs = engine.getIntegratedLUFS();
  // Should be within 1 dB of target
  EXPECT_NEAR(lufs, -14.0, 1.0);
}

TEST(EngineAcceptanceTest, TruePeakBelowCeiling) {
  AuroraDSPEngine engine(48000, 2);
  engine.setSessionParams(
    R"({"target_lufs": -14.0, "ceiling_dbtp": -1.0})"
  );

  const int N = 48000 * 3;
  std::vector<float> input(N * 2);
  std::vector<float> output(N * 2);

  // Generate loud tone
  for (int i = 0; i < N; ++i) {
    float s = 0.9f * std::sin(2.0f * 3.14159f * 1000.0f * i / 48000.0f);
    input[i * 2]     = s;
    input[i * 2 + 1] = s;
  }

  engine.renderFull(input.data(), output.data(), N);

  double tp = engine.getTruePeakDBTP();
  EXPECT_LE(tp, -0.9);
}

}  // namespace aurora
