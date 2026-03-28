#pragma once

namespace aurora {

// AnalogNet neural residual stub (v5.0).
// Full implementation requires trained AnalogNet weights + NORMALIZATION_VALIDATED=true.
// For now: waveshaper + micro-drift.
class AnalogResidual {
 public:
  explicit AnalogResidual(int sampleRate);
  void setDrive(float drive);   // 0.0 (clean) to 1.0 (warm saturation)
  void process(float* buffer, int numFrames, int numChannels);
  void reset();

 private:
  int   sampleRate_;
  float drive_     = 0.2f;
  float driftPhase_ = 0.0f;
  float driftRate_;          // very slow LFO for micro-drift
  float dcState_[2] = {};

  float waveshape(float x, float drive) const;
};

}  // namespace aurora
