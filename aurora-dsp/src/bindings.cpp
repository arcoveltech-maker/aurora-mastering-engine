#include "aurora/engine.h"
#include <string>

#ifdef __EMSCRIPTEN__
#include <emscripten/bind.h>

EMSCRIPTEN_BINDINGS(aurora) {
  emscripten::class_<aurora::AuroraDSPEngine>("AuroraDSPEngine")
    .constructor<int, int>()
    .function("setSessionParams", &aurora::AuroraDSPEngine::setSessionParams)
    .function("getIntegratedLUFS", &aurora::AuroraDSPEngine::getIntegratedLUFS)
    .function("getTruePeakDBTP", &aurora::AuroraDSPEngine::getTruePeakDBTP);
  emscripten::function("getAuroraDSPVersion", &aurora::AuroraDSPEngine::getVersion);
  emscripten::function("getAuroraDSPBuildHash", &aurora::AuroraDSPEngine::getBuildHash);
}
#endif
