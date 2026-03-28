#pragma once
#include "aurora/biquad.h"
#include <deque>
#include <vector>

namespace aurora {

// ITU-R BS.1770-4 K-weighting filter (2-stage biquad)
class KWeightingFilter {
 public:
  explicit KWeightingFilter(int sampleRate);
  // Process a single sample; returns filtered sample
  float process(float x);
  void reset();
 private:
  BiquadFilter stage1a_;
  BiquadFilter stage1b_;
};

// Full ITU-R BS.1770-4 integrated loudness meter with gating, LRA
class LUFSMeter {
 public:
  LUFSMeter(int sampleRate, int numChannels);
  // Feed one interleaved frame (numChannels samples)
  void processFrame(const float* frame);
  // Feed a block of interleaved frames
  void process(const float* input, int numFrames);
  void reset();

  double getIntegratedLUFS() const;
  double getMomentaryLUFS() const;
  double getShortTermLUFS() const;
  double getLRA() const;

 private:
  int sampleRate_;
  int numChannels_;
  KWeightingFilter kL_;
  KWeightingFilter kR_;

  // Running sums for gated integrated
  double sumSq_ = 0.0;
  int    count_ = 0;

  // Momentary: 400 ms block, updated every 100 ms (75% overlap)
  int momentaryBlockSize_;   // samples = 0.4 * sr
  int momentaryHopSize_;     // samples = 0.1 * sr
  std::vector<double> momentaryBuf_;
  int momentaryBufPos_ = 0;
  int momentaryHopCount_ = 0;
  std::deque<double> momentaryBlocks_;  // last few 400ms block means

  // Short-term: 3 s block, 75% overlap (hop = 750 ms)
  int shortTermBlockSize_;
  int shortTermHopSize_;
  std::vector<double> shortTermBuf_;
  int shortTermBufPos_ = 0;
  int shortTermHopCount_ = 0;
  std::deque<double> shortTermBlocks_;  // for LRA

  double ungatedMean_ = 0.0;

  void advanceMomentary(double meanSq);
  void advanceShortTerm(double meanSq);
  static double blockToLUFS(double meanSq);
  double computeGatedLUFS() const;
};

}  // namespace aurora
