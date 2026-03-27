#include "aurora/lufs.h"
#include <cassert>
#include <iostream>

void testKWeightingResponse() {
  aurora::KWeightingFilter filter(48000);
  const int numFrames = 1024;
  float input[numFrames] = {1.0f}; // Impulse
  float output[numFrames] = {0.0f};

  filter.process(input, output, numFrames);

  // Validate output (placeholder check)
  assert(output[0] > 0.0f);
  std::cout << "K-weighting response test passed.\n";
}

void testLUFSCalculation() {
  aurora::LUFSMeter meter(48000, 2);
  const int numFrames = 1024;
  float input[numFrames * 2] = {1.0f}; // Stereo impulse

  meter.process(input, numFrames);
  double integratedLUFS = meter.getIntegratedLUFS();

  // Validate LUFS (placeholder check)
  assert(integratedLUFS == -23.0);
  std::cout << "LUFS calculation test passed.\n";
}

int main() {
  testKWeightingResponse();
  testLUFSCalculation();
  return 0;
}