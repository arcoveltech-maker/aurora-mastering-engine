#pragma once

namespace aurora {

// Mid/Side encode-process-decode
// All processing operates on M and S channels independently
class MSProcessor {
 public:
  MSProcessor() = default;

  void setMidGainDB(float gainDB) { midGainLin_ = dbToLin(gainDB); }
  void setSideGainDB(float gainDB) { sideGainLin_ = dbToLin(gainDB); }
  void setWidth(float width) { width_ = width; }  // 0.0=mono, 1.0=normal, 2.0=wide

  // Encode L/R -> M/S
  static void encode(float l, float r, float& mid, float& side);
  // Decode M/S -> L/R
  static void decode(float mid, float side, float& l, float& r);

  // Apply mid/side gain and width to a stereo frame in-place
  void processStereoFrame(float& l, float& r) const;

 private:
  float midGainLin_ = 1.0f;
  float sideGainLin_ = 1.0f;
  float width_ = 1.0f;

  static float dbToLin(float db);
};

}  // namespace aurora
