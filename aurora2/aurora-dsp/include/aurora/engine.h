#pragma once

#include <string>
#include <memory>

namespace aurora {

class AuroraDSPEngine {
 public:
  AuroraDSPEngine(int sampleRate, int numChannels);
  ~AuroraDSPEngine();
  void setSessionParams(const std::string& manifestJSON);
  void renderFull(const float* input, float* output, int numFrames);
  double getIntegratedLUFS() const;
  double getTruePeakDBTP() const;
  static std::string getVersion();
  static std::string getBuildHash();

 private:
  int sampleRate_ = 48000;
  int numChannels_ = 2;
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace aurora
