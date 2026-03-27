#include "aurora/engine.h"
#include "aurora/lufs.h"
#include "aurora/true_peak.h"
#include "aurora/crossover.h"
#include "aurora/saturation.h"
#include "aurora/linear_phase_eq.h"
#include "aurora/ms_processing.h"
#include "aurora/limiter.h"
#include "aurora/dither.h"

#include <cmath>
#include <algorithm>
#include <string>
#include <sstream>
#include <stdexcept>

// Minimal JSON key-value extraction (no external deps for WASM)
static float jsonFloat(const std::string& json, const std::string& key, float def = 0.0f) {
  auto pos = json.find("\"" + key + "\"");
  if (pos == std::string::npos) return def;
  pos = json.find(':', pos);
  if (pos == std::string::npos) return def;
  ++pos;
  while (pos < json.size() && (json[pos] == ' ' || json[pos] == '\t')) ++pos;
  try { return std::stof(json.substr(pos)); } catch (...) { return def; }
}

namespace aurora {

struct AuroraDSPEngine::Impl {
  int sampleRate;
  int numChannels;

  LUFSMeter      lufs;
  TruePeakMeter  truePeak;
  LR8Crossover   crossoverLow;   // Sub/Low split
  LR8Crossover   crossoverMid;   // Low/Mid split
  LR8Crossover   crossoverHigh;  // Mid/High split
  LinearPhaseEQ  eqLow;
  LinearPhaseEQ  eqMid;
  LinearPhaseEQ  eqHigh;
  Saturation     satLow, satMid, satHigh;
  MSProcessor    ms;
  SAILLimiter    limiter;
  Dither         ditherL, ditherR;

  // Macro parameters
  float targetLUFS  = -14.0f;
  float ceilingDBTP = -1.0f;
  float warmth      = 0.0f;  // 0-1: low-end saturation
  float air         = 0.0f;  // 0-1: high-shelf boost
  float width       = 1.0f;  // stereo width
  float punch       = 0.0f;  // 0-1: transient emphasis (limiter tightness)
  float brightness  = 0.0f;  // 0-1: high-freq EQ
  float depth       = 0.0f;  // 0-1: low-freq EQ

  Impl(int sr, int ch)
    : sampleRate(sr), numChannels(ch),
      lufs(sr, ch), truePeak(sr, ch),
      crossoverLow(sr, 200.0f),
      crossoverMid(sr, 2000.0f),
      crossoverHigh(sr, 8000.0f),
      eqLow(sr), eqMid(sr), eqHigh(sr),
      ms(),
      limiter(sr, ch),
      ditherL(), ditherR()
  {
    limiter.setCeilingDBTP(-1.0f);
    ditherL.setType(DitherType::TPDF);
    ditherR.setType(DitherType::TPDF);
    ditherL.setBitDepth(24);
    ditherR.setBitDepth(24);
  }

  void applyMacros() {
    // Warmth: low-shelf boost + low saturation
    EQBand warmthBand;
    warmthBand.type    = EQBand::Type::LOWSHELF;
    warmthBand.freqHz  = 200.0f;
    warmthBand.gainDB  = warmth * 3.0f;
    warmthBand.q       = 0.707f;
    eqLow.setBand(0, warmthBand);
    satLow.setMode(SaturationMode::TAPE);
    satLow.setDrive(warmth * 0.4f);
    satLow.setMix(warmth * 0.5f);

    // Brightness: high-shelf boost
    EQBand brightBand;
    brightBand.type   = EQBand::Type::HIGHSHELF;
    brightBand.freqHz = 8000.0f;
    brightBand.gainDB = brightness * 4.0f;
    brightBand.q      = 0.707f;
    eqHigh.setBand(0, brightBand);

    // Air: presence shelf at 12kHz
    EQBand airBand;
    airBand.type   = EQBand::Type::HIGHSHELF;
    airBand.freqHz = 12000.0f;
    airBand.gainDB = air * 3.0f;
    airBand.q      = 0.5f;
    eqHigh.setBand(1, airBand);

    // Depth: low-freq emphasis
    EQBand depthBand;
    depthBand.type   = EQBand::Type::PEAK;
    depthBand.freqHz = 60.0f;
    depthBand.gainDB = depth * 4.0f;
    depthBand.q      = 1.0f;
    eqLow.setBand(1, depthBand);

    // Width
    ms.setWidth(width);

    // Punch: tighter limiter release
    float releaseMs = 200.0f - punch * 150.0f;
    limiter.setReleaseMs(releaseMs);
    limiter.setCeilingDBTP(ceilingDBTP);
  }
};

AuroraDSPEngine::AuroraDSPEngine(int sampleRate, int numChannels)
    : sampleRate_(sampleRate), numChannels_(numChannels),
      impl_(std::make_unique<Impl>(sampleRate, numChannels)) {}

AuroraDSPEngine::~AuroraDSPEngine() = default;

void AuroraDSPEngine::setSessionParams(const std::string& manifestJSON) {
  impl_->targetLUFS  = jsonFloat(manifestJSON, "target_lufs", -14.0f);
  impl_->ceilingDBTP = jsonFloat(manifestJSON, "ceiling_dbtp", -1.0f);
  impl_->warmth      = jsonFloat(manifestJSON, "warmth", 0.0f);
  impl_->air         = jsonFloat(manifestJSON, "air", 0.0f);
  impl_->width       = jsonFloat(manifestJSON, "width", 1.0f);
  impl_->punch       = jsonFloat(manifestJSON, "punch", 0.0f);
  impl_->brightness  = jsonFloat(manifestJSON, "brightness", 0.0f);
  impl_->depth       = jsonFloat(manifestJSON, "depth", 0.0f);
  impl_->applyMacros();
}

void AuroraDSPEngine::renderFull(const float* input, float* output, int numFrames) {
  auto& im = *impl_;
  const int ch = numChannels_;

  // First pass: measure input level for gain correction
  im.lufs.reset();
  im.truePeak.reset();
  for (int f = 0; f < numFrames; ++f) {
    im.lufs.processFrame(input + f * ch);
    im.truePeak.processFrame(input + f * ch);
  }

  double measuredLUFS = im.lufs.getIntegratedLUFS();
  double gainDB = im.targetLUFS - measuredLUFS;
  // Clamp gain correction to ±18 dB
  gainDB = std::clamp(gainDB, -18.0, 18.0);
  float gainLin = static_cast<float>(std::pow(10.0, gainDB / 20.0));

  // Second pass: process audio
  // Reset meters for output measurement
  im.lufs.reset();
  im.truePeak.reset();
  im.limiter.reset();
  im.crossoverLow.reset();
  im.crossoverMid.reset();
  im.crossoverHigh.reset();
  im.eqLow.reset();
  im.eqMid.reset();
  im.eqHigh.reset();

  for (int f = 0; f < numFrames; ++f) {
    const float* in  = input  + f * ch;
    float*       out = output + f * ch;

    // Apply gain makeup
    float frame[2] = { in[0] * gainLin, (ch > 1 ? in[1] : in[0]) * gainLin };

    // M/S width processing
    im.ms.processStereoFrame(frame[0], frame[1]);

    // Multiband: crossover into 3 bands
    float low[2], mid[2], high[2], tmp[2];

    // crossoverLow splits sub (<200Hz) vs rest
    im.crossoverLow.processStereo(frame, low, tmp);
    // crossoverMid splits mid (<2kHz) vs high (>2kHz) from the "rest"
    im.crossoverMid.processStereo(tmp, mid, tmp);
    // crossoverHigh splits high (<8kHz) vs air (>8kHz)
    im.crossoverHigh.processStereo(tmp, high, tmp);

    // Per-band EQ
    low[0]  = im.eqLow.processSample(low[0], 0);
    low[1]  = im.eqLow.processSample(low[1], 1);
    mid[0]  = im.eqMid.processSample(mid[0], 0);
    mid[1]  = im.eqMid.processSample(mid[1], 1);
    high[0] = im.eqHigh.processSample(high[0], 0);
    high[1] = im.eqHigh.processSample(high[1], 1);

    // Per-band saturation on low band
    low[0] = im.satLow.process(low[0]);
    low[1] = im.satLow.process(low[1]);

    // Recombine bands
    float summed[2] = {
      low[0] + mid[0] + high[0] + tmp[0],
      low[1] + mid[1] + high[1] + tmp[1]
    };

    // Brickwall limiter
    im.limiter.processFrame(summed);

    // TPDF dither
    summed[0] = im.ditherL.process(summed[0]);
    if (ch > 1) summed[1] = im.ditherR.process(summed[1]);

    out[0] = summed[0];
    if (ch > 1) out[1] = summed[1];

    // Meter output
    im.lufs.processFrame(out);
    im.truePeak.processFrame(out);
  }
}

double AuroraDSPEngine::getIntegratedLUFS() const {
  return impl_->lufs.getIntegratedLUFS();
}

double AuroraDSPEngine::getTruePeakDBTP() const {
  return impl_->truePeak.getTruePeakDBTP();
}

std::string AuroraDSPEngine::getVersion() { return "5.0.0"; }
std::string AuroraDSPEngine::getBuildHash() { return "aurora-dsp-5.0.0"; }

}  // namespace aurora
