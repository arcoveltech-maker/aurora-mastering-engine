#pragma once

namespace aurora {

enum class SaturationMode { TAPE, TUBE, CLIP };

class Saturation {
 public:
  Saturation() = default;
  void setMode(SaturationMode mode) { mode_ = mode; }
  void setDrive(float drive) { drive_ = drive; }   // 0.0 - 1.0
  void setMix(float mix) { mix_ = mix; }           // 0.0 - 1.0

  float process(float in) const;

 private:
  SaturationMode mode_ = SaturationMode::TAPE;
  float drive_ = 0.0f;
  float mix_ = 0.0f;
};

}  // namespace aurora
