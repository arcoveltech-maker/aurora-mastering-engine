#pragma once

#include <string>

namespace aurora {

class AuroraDSPEngine {
 public:
  AuroraDSPEngine(int sampleRate, int numChannels);
  void setSessionParams(const std::string& manifestJSON);
  void renderFull(const float* input, float* output, int numFrames);
  double getIntegratedLUFS() const;
  double getTruePeakDBTP() const;
  static std::string getVersion();
  static std::string getBuildHash();
 private:
  int sampleRate_ = 48000;
  int numChannels_ = 2;
};

}  // namespace aurora
