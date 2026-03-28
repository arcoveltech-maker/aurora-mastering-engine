#pragma once
#include <vector>
#include <array>

namespace aurora {

class SpatialRenderer {
 public:
  enum class Format {
    STEREO,
    QUAD,
    SURROUND_51,
    SURROUND_71,
    ATMOS_712,   // 7.1.2 Dolby Atmos bed
    BINAURAL,
  };

  struct SourcePosition {
    float azimuth  = 0.0f;    // degrees: 0 = front, 90 = right
    float elevation = 0.0f;   // degrees: 0 = horizontal, +90 = above
    float distance  = 1.0f;   // metres (for distance attenuation)
  };

  SpatialRenderer(int sampleRate, Format outputFormat = Format::STEREO);

  void setSourcePosition(int sourceId, const SourcePosition& pos);
  void setListenerYaw(float yawDeg);    // head rotation
  void setRoomSize(float sizeMetres);   // for early reflection timing

  // Process mono input → multi-channel output
  // outputChannels must have numOutputChannels() elements, each of numFrames samples
  void processFrame(const float* monoInput, float** outputChannels, int numFrames);

  int numOutputChannels() const;
  static std::string formatName(Format f);

 private:
  int     sampleRate_;
  Format  format_;
  float   listenerYaw_ = 0.0f;
  float   roomSize_    = 5.0f;

  // Per-source positioning
  struct Source {
    SourcePosition pos;
    float gains[12] = {};  // per output channel
  };
  std::vector<Source> sources_;

  void updateGains(Source& src) const;
  void applyPanning(const float* input, float** outputs, int nFrames, const float* gains) const;
};

}  // namespace aurora
