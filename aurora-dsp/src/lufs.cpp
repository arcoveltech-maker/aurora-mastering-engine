#include "aurora/lufs.h"
#include "aurora/biquad.h"
#include <vector>

namespace aurora {

LUFSMeter::LUFSMeter(int sampleRate, int numChannels)
    : sampleRate_(sampleRate), numChannels_(numChannels) {}

void LUFSMeter::process(const float* input, int numFrames) {
  std::vector<float> weightedOutput(numFrames * numChannels_);
  KWeightingFilter kFilter(sampleRate_);

  for (int ch = 0; ch < numChannels_; ++ch) {
    kFilter.process(input + ch * numFrames, weightedOutput.data() + ch * numFrames, numFrames);
  }

  // Compute LUFS metrics (stub for now)
  integratedLUFS_ = -23.0; // Placeholder value
}

double LUFSMeter::getIntegratedLUFS() const { return integratedLUFS_; }
double LUFSMeter::getMomentaryLUFS() const { return -70.0; }
double LUFSMeter::getShortTermLUFS() const { return -70.0; }
double LUFSMeter::getLRA() const { return 0.0; }

KWeightingFilter::KWeightingFilter(int sampleRate) {
  BiquadCoeffs coeffs1a, coeffs1b;
  if (sampleRate == 48000) {
    coeffs1a = {1.53512485958697, -2.69169618940638, 1.19839281085285, -1.69065929318241, 0.73248077421585};
    coeffs1b = {0.99886234236998, -1.99772468473996, 0.99886234236998, -1.99772300507016, 0.99772636440976};
  }
  // Add other sample rates here
  stage1a_.setCoefficients(coeffs1a);
  stage1b_.setCoefficients(coeffs1b);
}

void KWeightingFilter::process(const float* input, float* output, int numFrames) {
  float temp[numFrames];
  stage1a_.process(input, temp, numFrames);
  stage1b_.process(temp, output, numFrames);
}

}  // namespace aurora
