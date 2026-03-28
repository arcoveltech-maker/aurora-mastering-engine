#include "aurora/lufs.h"
#include <algorithm>
#include <cmath>
#include <numeric>

namespace aurora {

// ── KWeightingFilter ───────────────────────────────────────────────────────

KWeightingFilter::KWeightingFilter(int sampleRate) {
  BiquadCoeffs c1, c2;
  if (sampleRate == 48000) {
    // Stage 1: high-shelf pre-filter
    c1 = {1.53512485958697, -2.69169618940638, 1.19839281085285,
          -1.69065929318241, 0.73248077421585};
    // Stage 2: high-pass
    c2 = {0.99886234236998, -1.99772468473996, 0.99886234236998,
          -1.99772300507016, 0.99772636440976};
  } else if (sampleRate == 44100) {
    c1 = {1.54552898911403, -2.72551298371706, 1.20027895764338,
          -1.72551298371706, 0.74552898911403};
    c2 = {0.99887799826089, -1.99775601652179, 0.99887799826089,
          -1.99775600753555, 0.99775602550802};
  } else if (sampleRate == 96000) {
    c1 = {1.69065929318241, -3.07476781648595, 1.43231688822172,
          -1.86843189408394, 0.87516086097894};
    c2 = {0.99943380897914, -1.99886761795828, 0.99943380897914,
          -1.99886759784451, 0.99886763807205};
  } else {
    // Fallback: use 48 kHz coefficients
    c1 = {1.53512485958697, -2.69169618940638, 1.19839281085285,
          -1.69065929318241, 0.73248077421585};
    c2 = {0.99886234236998, -1.99772468473996, 0.99886234236998,
          -1.99772300507016, 0.99772636440976};
  }
  stage1a_.setCoefficients(c1);
  stage1b_.setCoefficients(c2);
}

float KWeightingFilter::process(float x) {
  return stage1b_.process(stage1a_.process(x));
}

void KWeightingFilter::reset() {
  stage1a_.reset();
  stage1b_.reset();
}

// ── LUFSMeter ──────────────────────────────────────────────────────────────

static constexpr double kAbsGate   = -70.0;   // LUFS — ITU-R BS.1770-4
static constexpr double kRelOffset =  -10.0;  // LU below ungated mean

LUFSMeter::LUFSMeter(int sampleRate, int numChannels)
    : sampleRate_(sampleRate), numChannels_(numChannels),
      kL_(sampleRate), kR_(sampleRate)
{
  momentaryBlockSize_ = static_cast<int>(sampleRate * 0.4);
  momentaryHopSize_   = static_cast<int>(sampleRate * 0.1);
  momentaryBuf_.assign(momentaryBlockSize_, 0.0);

  shortTermBlockSize_ = static_cast<int>(sampleRate * 3.0);
  shortTermHopSize_   = static_cast<int>(sampleRate * 0.75);
  shortTermBuf_.assign(shortTermBlockSize_, 0.0);
}

void LUFSMeter::reset() {
  sumSq_ = 0.0;
  count_ = 0;
  momentaryBufPos_   = 0;
  momentaryHopCount_ = 0;
  shortTermBufPos_   = 0;
  shortTermHopCount_ = 0;
  momentaryBlocks_.clear();
  shortTermBlocks_.clear();
  ungatedMean_ = 0.0;
  kL_.reset();
  kR_.reset();
  std::fill(momentaryBuf_.begin(), momentaryBuf_.end(), 0.0);
  std::fill(shortTermBuf_.begin(), shortTermBuf_.end(), 0.0);
}

void LUFSMeter::processFrame(const float* frame) {
  float wL = kL_.process(frame[0]);
  float wR = (numChannels_ > 1) ? kR_.process(frame[1]) : wL;
  double meanSq = (static_cast<double>(wL * wL) + static_cast<double>(wR * wR)) * 0.5;

  // Global accumulation (for ungated mean)
  sumSq_ += meanSq;
  ++count_;

  // Momentary 400 ms sliding buffer
  momentaryBuf_[momentaryBufPos_] = meanSq;
  momentaryBufPos_ = (momentaryBufPos_ + 1) % momentaryBlockSize_;
  if (++momentaryHopCount_ >= momentaryHopSize_) {
    momentaryHopCount_ = 0;
    double blockMean = std::accumulate(momentaryBuf_.begin(), momentaryBuf_.end(), 0.0)
                       / static_cast<double>(momentaryBlockSize_);
    advanceMomentary(blockMean);
  }

  // Short-term 3 s sliding buffer
  shortTermBuf_[shortTermBufPos_] = meanSq;
  shortTermBufPos_ = (shortTermBufPos_ + 1) % shortTermBlockSize_;
  if (++shortTermHopCount_ >= shortTermHopSize_) {
    shortTermHopCount_ = 0;
    double blockMean = std::accumulate(shortTermBuf_.begin(), shortTermBuf_.end(), 0.0)
                       / static_cast<double>(shortTermBlockSize_);
    advanceShortTerm(blockMean);
  }
}

void LUFSMeter::process(const float* input, int numFrames) {
  for (int i = 0; i < numFrames; ++i)
    processFrame(input + i * numChannels_);
}

void LUFSMeter::advanceMomentary(double meanSq) {
  momentaryBlocks_.push_back(meanSq);
  // Keep only last 4 blocks (covers 400 ms with 100 ms hops)
  while (static_cast<int>(momentaryBlocks_.size()) > 4)
    momentaryBlocks_.pop_front();
}

void LUFSMeter::advanceShortTerm(double meanSq) {
  shortTermBlocks_.push_back(meanSq);
  // Keep enough for LRA (no strict limit; cap at ~600 blocks ≈ 10 min at 1 Hz)
  while (static_cast<int>(shortTermBlocks_.size()) > 600)
    shortTermBlocks_.pop_front();
}

double LUFSMeter::blockToLUFS(double meanSq) {
  if (meanSq <= 0.0) return -144.0;
  return -0.691 + 10.0 * std::log10(meanSq);
}

double LUFSMeter::computeGatedLUFS() const {
  if (count_ == 0) return -70.0;
  ungatedMean_ = sumSq_ / static_cast<double>(count_);
  double ungatedLUFS = blockToLUFS(ungatedMean_);

  // Absolute gate threshold
  double absThresh = std::pow(10.0, (kAbsGate + 0.691) / 10.0);
  // Relative gate threshold
  double relThreshLUFS = ungatedLUFS + kRelOffset;
  double relThresh = std::pow(10.0, (relThreshLUFS + 0.691) / 10.0);

  double gatedSum = 0.0;
  int    gatedCount = 0;

  // Use short-term blocks as gating blocks per BS.1770-4 §3.3
  for (double b : shortTermBlocks_) {
    if (b >= absThresh && b >= relThresh) {
      gatedSum += b;
      ++gatedCount;
    }
  }

  if (gatedCount == 0) return ungatedLUFS;
  return blockToLUFS(gatedSum / static_cast<double>(gatedCount));
}

double LUFSMeter::getIntegratedLUFS() const {
  return computeGatedLUFS();
}

double LUFSMeter::getMomentaryLUFS() const {
  if (momentaryBlocks_.empty()) return -70.0;
  double mean = 0.0;
  for (double b : momentaryBlocks_) mean += b;
  mean /= static_cast<double>(momentaryBlocks_.size());
  return blockToLUFS(mean);
}

double LUFSMeter::getShortTermLUFS() const {
  if (shortTermBlocks_.empty()) return -70.0;
  // Average of last ~3 s worth (last hop)
  int n = std::min(static_cast<int>(shortTermBlocks_.size()), 4);
  double mean = 0.0;
  auto it = shortTermBlocks_.end();
  for (int i = 0; i < n; ++i) mean += *--it;
  mean /= static_cast<double>(n);
  return blockToLUFS(mean);
}

double LUFSMeter::getLRA() const {
  if (shortTermBlocks_.size() < 2) return 0.0;
  // Collect LUFS values for all short-term blocks
  std::vector<double> vals;
  vals.reserve(shortTermBlocks_.size());
  double absMeanSq = sumSq_ / std::max(1, count_);
  double ungated = blockToLUFS(absMeanSq);
  double relThreshLUFS = ungated - 20.0;  // -20 LU relative gate for LRA (EBU R128)
  double relThresh = std::pow(10.0, (relThreshLUFS + 0.691) / 10.0);
  double absThresh = std::pow(10.0, (kAbsGate + 0.691) / 10.0);

  for (double b : shortTermBlocks_) {
    if (b >= absThresh && b >= relThresh)
      vals.push_back(blockToLUFS(b));
  }
  if (vals.size() < 2) return 0.0;
  std::sort(vals.begin(), vals.end());
  double p10 = vals[static_cast<size_t>(vals.size() * 0.10)];
  double p95 = vals[static_cast<size_t>(vals.size() * 0.95)];
  return p95 - p10;
}

}  // namespace aurora
