#include "aurora/spatial_renderer.h"
#include <cmath>
#include <algorithm>
#include <string>

namespace aurora {

static constexpr float kPi = 3.14159265358979f;
static constexpr float kDegToRad = kPi / 180.0f;

SpatialRenderer::SpatialRenderer(int sampleRate, Format outputFormat)
    : sampleRate_(sampleRate), format_(outputFormat)
{
  sources_.resize(16);  // pre-allocate up to 16 sources
}

int SpatialRenderer::numOutputChannels() const {
  switch (format_) {
    case Format::STEREO:    return 2;
    case Format::QUAD:      return 4;
    case Format::SURROUND_51: return 6;
    case Format::SURROUND_71: return 8;
    case Format::ATMOS_712:   return 10;  // 7.1.2
    case Format::BINAURAL:    return 2;
    default: return 2;
  }
}

std::string SpatialRenderer::formatName(Format f) {
  switch (f) {
    case Format::STEREO:      return "Stereo 2.0";
    case Format::QUAD:        return "Quadraphonic 4.0";
    case Format::SURROUND_51: return "5.1 Surround";
    case Format::SURROUND_71: return "7.1 Surround";
    case Format::ATMOS_712:   return "Dolby Atmos 7.1.2";
    case Format::BINAURAL:    return "Binaural";
    default: return "Unknown";
  }
}

void SpatialRenderer::setSourcePosition(int sourceId, const SourcePosition& pos) {
  if (sourceId < 0 || sourceId >= static_cast<int>(sources_.size())) return;
  sources_[sourceId].pos = pos;
  updateGains(sources_[sourceId]);
}

void SpatialRenderer::setListenerYaw(float yawDeg) {
  listenerYaw_ = yawDeg;
  for (auto& src : sources_) updateGains(src);
}

void SpatialRenderer::setRoomSize(float sizeMetres) {
  roomSize_ = std::max(1.0f, sizeMetres);
}

void SpatialRenderer::updateGains(Source& src) const {
  float az  = (src.pos.azimuth - listenerYaw_) * kDegToRad;
  float el  = src.pos.elevation * kDegToRad;
  float dist = std::max(0.1f, src.pos.distance);

  // Distance attenuation (inverse square)
  float distAtten = 1.0f / (dist * dist);
  distAtten = std::min(1.0f, distAtten);

  // Basic VBAP-style panning for stereo (L=0, R=1)
  float pan = std::sin(az) * std::cos(el);  // -1 = full left, +1 = full right
  src.gains[0] = distAtten * std::sqrt((1.0f - pan) * 0.5f);  // L
  src.gains[1] = distAtten * std::sqrt((1.0f + pan) * 0.5f);  // R

  if (format_ == Format::SURROUND_51 || format_ == Format::SURROUND_71 ||
      format_ == Format::ATMOS_712) {
    // Front/back balance based on elevation-adjusted cosine
    float front = (std::cos(az) + 1.0f) * 0.5f;
    float back  = 1.0f - front;
    float ht    = (el > 0.0f) ? std::sin(el) : 0.0f;  // height contribution

    // 5.1 channels: L(0) R(1) C(2) LFE(3) Ls(4) Rs(5)
    src.gains[2] = distAtten * front * (1.0f - std::abs(pan));  // C
    src.gains[3] = distAtten * 0.3f;  // LFE: constant level
    src.gains[4] = distAtten * back * std::sqrt((1.0f - pan) * 0.5f);  // Ls
    src.gains[5] = distAtten * back * std::sqrt((1.0f + pan) * 0.5f);  // Rs

    if (format_ == Format::SURROUND_71 || format_ == Format::ATMOS_712) {
      // Extra rear: Lrs(6) Rrs(7)
      src.gains[6] = distAtten * back * 0.7f * std::sqrt((1.0f - pan) * 0.5f);
      src.gains[7] = distAtten * back * 0.7f * std::sqrt((1.0f + pan) * 0.5f);
    }
    if (format_ == Format::ATMOS_712) {
      // Height channels: Ltf(8) Rtf(9)
      src.gains[8] = distAtten * ht * std::sqrt((1.0f - pan) * 0.5f);
      src.gains[9] = distAtten * ht * std::sqrt((1.0f + pan) * 0.5f);
    }
  }
}

void SpatialRenderer::processFrame(const float* monoInput, float** outputs, int numFrames) {
  int nOut = numOutputChannels();
  // Zero outputs
  for (int c = 0; c < nOut; ++c)
    for (int i = 0; i < numFrames; ++i)
      outputs[c][i] = 0.0f;

  for (const auto& src : sources_) {
    for (int c = 0; c < nOut; ++c) {
      float g = src.gains[c];
      if (g < 1e-6f) continue;
      for (int i = 0; i < numFrames; ++i)
        outputs[c][i] += monoInput[i] * g;
    }
  }
}

}  // namespace aurora
