# Part 4: Analog fallback, EQ/M/S/transient/RIAA, WASM, acceptance tests

**Scope:** Phase 4E, 4F, 4G, 4H.  
**Do not proceed to Part 5 until instructed.**

Apply BLUEPRINT-INDEX: AnalogNet v1 fallback only; UI label "Analog Warmth Engine"; micro-drift depth **0–0.3%** (v5.0).

---

## Phase 4E — AnalogNet fallback (waveshaper + micro-drift)

**TASK 4E-1 — Chebyshev waveshaper**  
`aurora-dsp/include/aurora/saturation.h`, `aurora-dsp/src/saturation.cpp`: SaturationCharacter (EvenHarmonic, OddHarmonic, MixedHarmonic, Minimal). SaturationParams: drive, character, warmthMacro, hfRolloffHz, lfSaturationHz, driftRate (0.1–2 Hz), driftDepth (0–0.003). AnalogWarmthEngine: pre/post filters (HF rolloff, LF emphasis), LFO phase for micro-drift, waveshape() = tanh input + weighted T2,T3,T4,T5; DC blocker after. WARMTH 0→drive≈0 (THD ~0.01%), 5→~0.3, 10→~1 (THD ~3%). Character weights: Even  w2=0.15,w3=0.02,w4=0.05,w5=0.005; Odd w2=0.02,w3=0.12,w4=0.01,w5=0.04; Mixed/Minimal per spec.

**TASK 4E-2 — Neural residual stub**  
`aurora-dsp/include/aurora/analog_residual.h`, `aurora-dsp/src/analog_residual.cpp`: AnalogResidualNet; loadModel(), isModelLoaded(); processBlock() bypass (return input unchanged) until model available.

**TASK 4E-3 — Tests**  
`aurora-dsp/tests/test_saturation.cpp`: bypass at drive 0; THD increases with drive; even vs odd harmonic dominance; micro-drift varies THD over time; distinguishable from bypass (diff RMS > -60 dB, THD > 0.1% at WARMTH=5); no aliasing above 22 kHz; DC blocking (mean < 0.0001).

Run CTest. Report.

---

## Phase 4F — Linear-phase EQ, M/S, transient, RIAA

**TASK 4F-1 — Linear-phase FIR EQ**  
`aurora-dsp/include/aurora/linear_phase_eq.h`, `aurora-dsp/src/linear_phase_eq.cpp`: FIR_LENGTH=65536, up to 12 bands (Peak, LowShelf, HighShelf, etc.). computeTargetMagnitude from bands → IFFT → Kaiser window → causal shift. Overlap-save FFT convolution in processBlock(). getMagnitudeResponse, getLatencySamples().

**TASK 4F-2 — M/S**  
`aurora-dsp/include/aurora/ms_processing.h`, `aurora-dsp/src/ms_processing.cpp`: MSProcessingParams (widthMacro, bassMonoFreqHz, bassMonoSlope, haasDelay). Encode/decode; sideGain from WIDTH (0→-6 dB, 5→0, 10→+6 dB). Bass mono LR4 crossover. checkMonoCompatibility: deltaE = 20*log10(RMS_stereo/RMS_mono); <3 dB OK, 3–6 dB warning, >6 dB critical.

**TASK 4F-3 — Transient designer**  
`aurora-dsp/include/aurora/transient_designer.h`, `aurora-dsp/src/transient_designer.cpp`: TransientDesignerParams (attack, sustain, body -100..+100%, sensitivity 1–10, FreqRange). Fast/slow envelope followers; transient vs sustain gain modulation; smoothed gains.

**TASK 4F-4 — RIAA**  
`aurora-dsp/include/aurora/riaa.h`, `aurora-dsp/src/riaa.cpp`: Mode Standard/Extended. IEC 60098: τ1=3180µs, τ2=318µs, τ3=75µs; extended + 20 Hz rolloff. Biquad cascade from bilinear transform. Verify response at 20,50,100,500,1k,2.122k,5k,10k,15k,20k Hz within ±0.01 dB.

**TASK 4F-5 — Tests**  
`aurora-dsp/tests/test_ms.cpp`: M/S round-trip; mono compatibility at WIDTH 0/5/10; bass mono crossover; deltaE classification.  
`aurora-dsp/tests/test_riaa.cpp`: RIAA response ±0.01 dB at all reference freqs (44.1k, 48k, 96k); extended 20 Hz rolloff.

Run CTest. Report.

---

## Phase 4G — WASM bindings and build

**TASK 4G-1 — Engine facade**  
`aurora-dsp/include/aurora/engine.h`, `aurora-dsp/src/engine.cpp`: AuroraDSPEngine(sampleRate, numChannels). setSessionParams(manifestJSON), setMacro/setMacros, setLimiterMode, setLoudnessTarget, setSaturationCharacter. renderFull(input, numFrames) → output buffer; processStage() for debug. getIntegratedLUFS, getTruePeakDBTP, getLRA, getQCReportJSON, getBandGainReduction. getVersion(), getBuildHash(), getLatencySamples(). Chain: input → M/S → EQ → multiband → saturation → transient → SAIL (stub if needed) → output.

**TASK 4G-2 — Embind**  
`aurora-dsp/src/bindings.cpp` (if __EMSCRIPTEN__): class_ AuroraDSPEngine, LUFSMeter, TruePeakMeter; function renderAudio(sampleRate, channels, inputBuffer, manifestJSON) → { audio, integratedLUFS, truePeakDBTP, lra, qcReport, version }; getAuroraDSPVersion, getAuroraDSPBuildHash; supportsSharedMemory(). Typed array copy helpers.

**TASK 4G-3 — Emscripten build**  
`aurora-dsp/build_wasm.sh`: emcmake cmake -DAURORA_BUILD_WASM=ON -DAURORA_BUILD_TESTS=OFF; emmake make; sha256sum aurora_dsp.wasm → aurora_dsp.wasm.sha256; copy to frontend/public/wasm; optional archive to models/wasm-archive/{hash}.wasm. CMakeLists: when WASM ON use KissFFT, compile bindings.cpp, set INITIAL_MEMORY=256MB, MAXIMUM_MEMORY=4GB, ALLOW_MEMORY_GROWTH=1, MODULARIZE=1, EXPORT_ES6=1, EXPORT_NAME=AuroraDSP, ENVIRONMENT=web,worker, USE_PTHREADS=0, -msimd128, --bind, -O3, -flto.

**TASK 4G-4 — TypeScript loader**  
`frontend/src/utils/wasm-loader.ts`: loadAuroraDSP() → AuroraDSPModule (AuroraDSPEngine, LUFSMeter, TruePeakMeter, renderAudio, getVersion, getBuildHash, supportsSharedMemory). Interfaces for RenderResult, engine instance methods. locateFile → /wasm/.

**TASK 4G-5 — Execute WASM build**  
Run `./build_wasm.sh`. Fix compile errors (embind includes, Eigen alignment, KissFFT path) until aurora_dsp.wasm is produced. Report WASM size and SHA-256.

---

## Phase 4H — DSP acceptance test suite

**TASK 4H-1 — Test utils**  
`aurora-dsp/tests/test_utils.h`: generateSine, generatePinkNoise, generateWhiteNoise, generateSilence, generateSweep, generateImpulse, generateDrumHit; measureRMS_dBFS, measurePeak_dBFS; computeMagnitudeSpectrum, measureMagnitudeAtFrequency; computeTHD; crossCorrelation; computeThirdOctaveLevels; assertApprox; TestPRNG.

**TASK 4H-2 — Acceptance tests**  
`aurora-dsp/tests/test_acceptance.cpp`: LUFS EBU reference -23 / -33 and gating; True Peak ISP + stopband 50 dB; LR8 sum-to-unity and −6 dB at crossover; 6-band sum-to-unity; RIAA IEC60098 at 44.1/48/96k; Saturation distinguishable from bypass; Engine full render produces valid output and deterministic reproduction (same input+manifest → bit-identical output).

**TASK 4H-3 — Full native suite**  
`cd aurora-dsp/build-native && cmake .. -DAURORA_BUILD_WASM=OFF -DAURORA_BUILD_TESTS=ON && make && ctest --output-on-failure -V`. Fix failures until all pass. Re-run WASM build to confirm still compiles.

---

## End of Part 4

**Halt.** Report: (1) Files created/modified. (2) CTest summary (all pass). (3) WASM build status, file size, hash. (4) Any deviations.  
**Do not proceed to Part 5 until instructed.**
