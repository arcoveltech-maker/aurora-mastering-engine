#include "aurora/engine.h"

namespace aurora {

AuroraDSPEngine::AuroraDSPEngine(int sampleRate, int numChannels)
    : sampleRate_(sampleRate), numChannels_(numChannels) {}

void AuroraDSPEngine::setSessionParams(const std::string& manifestJSON) {
  (void)manifestJSON;
}

void AuroraDSPEngine::renderFull(const float* input, float* output, int numFrames) {
  for (int i = 0; i < numFrames * numChannels_; ++i)
    output[i] = input[i];
}

double AuroraDSPEngine::getIntegratedLUFS() const { return -70.0; }
double AuroraDSPEngine::getTruePeakDBTP() const { return -100.0; }

std::string AuroraDSPEngine::getVersion() { return "1.0.0"; }
std::string AuroraDSPEngine::getBuildHash() { return "stub"; }

}  // namespace aurora
