#pragma once

namespace aurora {

// Transient designer: separate attack/sustain envelopes, apply independent gain
class TransientDesigner {
 public:
  explicit TransientDesigner(int sampleRate);
  // attackGainDb: -12 to +12, sustainGainDb: -12 to +12
  void setParams(float attackGainDb, float sustainGainDb);
  void process(float* buffer, int numFrames, int numChannels);
  void reset();

 private:
  int sampleRate_;
  float attackGainDb_   = 0.0f;
  float sustainGainDb_  = 0.0f;

  // Fast envelope follower (~1 ms attack, 50 ms release) → transient detector
  float envFast_ = 0.0f;
  // Slow envelope follower (~100 ms attack, 400 ms release) → sustain reference
  float envSlow_ = 0.0f;

  float fastAttCoeff_;
  float fastRelCoeff_;
  float slowAttCoeff_;
  float slowRelCoeff_;
};

}  // namespace aurora
