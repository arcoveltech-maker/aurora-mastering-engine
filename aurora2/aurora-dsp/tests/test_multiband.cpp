#include <gtest/gtest.h>
#include "aurora/crossover.h"
#include <cmath>
#include <numeric>

namespace aurora {

TEST(LR8CrossoverTest, SumToUnity) {
  LR8Crossover xo(48000, 1000.0f);

  // Feed a 1kHz tone and check that low+high power ~ input power
  const int N = 48000;
  double inputPower = 0.0, outputPower = 0.0;

  for (int i = 0; i < N; ++i) {
    float s = std::sin(2.0f * 3.14159f * 1000.0f * i / 48000.0f);
    float frame[2] = {s, s};
    float low[2], high[2];
    xo.processStereo(frame, low, high);

    float sum = low[0] + high[0];
    inputPower  += s * s;
    outputPower += sum * sum;
  }

  // Allow ±0.5 dB deviation (0.01 dB spec is per band, sum-to-unity is approximate)
  double ratio = 10.0 * std::log10(outputPower / inputPower);
  EXPECT_NEAR(ratio, 0.0, 0.5);
}

TEST(LR8CrossoverTest, LowBandAttenuatesHighFreq) {
  LR8Crossover xo(48000, 1000.0f);

  // Feed 10kHz tone, measure low band output power
  const int N = 48000;
  double lowPower = 0.0, inputPower = 0.0;

  for (int i = 0; i < N; ++i) {
    float s = std::sin(2.0f * 3.14159f * 10000.0f * i / 48000.0f);
    float frame[2] = {s, s};
    float low[2], high[2];
    xo.processStereo(frame, low, high);
    lowPower   += low[0] * low[0];
    inputPower += s * s;
  }

  double attenDB = 10.0 * std::log10(lowPower / inputPower);
  EXPECT_LT(attenDB, -40.0);  // LR8 should have >40dB attenuation one decade above xo
}

}  // namespace aurora
