#pragma once
#include <deque>
#include <vector>

namespace aurora {

// SAIL (Simple Adaptive Infinite Lookahead Limiter)
// Brickwall look-ahead limiter with attack/release envelope
class SAILLimiter {
 public:
  SAILLimiter(int sampleRate, int numChannels);

  void setCeilingDBTP(float ceilingDBTP);  // e.g. -1.0
  void setLookaheadMs(float ms);           // default 5ms
  void setReleaseMs(float ms);             // default 100ms
  void reset();

  // Process one interleaved frame (numChannels_ samples)
  // Returns true if limiting was applied
  bool processFrame(float* frame);

  float getGainReductionDB() const { return gainReductionDB_; }

 private:
  int sampleRate_;
  int numChannels_;
  float ceilingLin_ = 0.89125f;   // -1 dBFS
  int lookaheadSamples_ = 240;    // 5ms @ 48kHz
  float releaseCoeff_ = 0.9998f;

  std::deque<std::vector<float>> lookaheadBuf_;
  float gainEnv_ = 1.0f;
  float gainReductionDB_ = 0.0f;

  void setReleaseCoeff(float ms);
};

}  // namespace aurora
