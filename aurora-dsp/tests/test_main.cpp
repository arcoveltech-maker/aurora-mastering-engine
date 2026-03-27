#include <cassert>
#include "aurora/engine.h"
#include "aurora/true_peak.h"

int main() {
  aurora::AuroraDSPEngine engine(48000, 2);
  assert(aurora::AuroraDSPEngine::getVersion() == "1.0.0");
  aurora::TruePeakMeter tp(48000, 2);
  float in[] = {0.5f, -0.5f};
  tp.process(in, 1);
  assert(tp.getTruePeakDBTP() > -10.0);
  return 0;
}
