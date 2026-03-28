# Part 3: DSP core — LUFS, True Peak, LR8, compressor, dynamic EQ

**Scope:** Phase 4A, 4B, 4C, 4D.  
**Do not proceed to Part 4 until instructed.**

**Critical:** K-weighting uses **negative** a1, a2 (v4.0 Appendix B). Biquad form: y = b0*x + b1*x[n-1] + b2*x[n-2] **− a1*y[n-1] − a2*y[n-2]**.

---

## Phase 4A — LUFS (ITU-R BS.1770-5)

**TASK 4A-1 — Biquad**  
`aurora-dsp/include/aurora/biquad.h`, `aurora-dsp/src/biquad.cpp`: Coefficients struct (b0,b1,b2,a1,a2). Direct Form II Transposed: y = b0*x + s1; s1 = b1*x − a1*y + s2; s2 = b2*x − a2*y. process(), processBlock(), reset().

**TASK 4A-2 — K-weighting**  
`aurora-dsp/include/aurora/lufs.h`, `aurora-dsp/src/lufs.cpp`: KWeightingFilter = Stage 1a (high shelf) + Stage 1b (RLB HPF). Use **negative** a1, a2 per v4.0:

- **48 kHz**  
  Stage 1a: b = [1.53512485958697, -2.69169618940638, 1.19839281085285], **a = [1.0, -1.69065929318241, 0.73248077421585]**  
  Stage 1b: b = [0.99886234236998, -1.99772468473996, 0.99886234236998], **a = [1.0, -1.99772300507016, 0.99772636440976]**
- **44.1 kHz**  
  Stage 1a: a = [1.0, **-1.66363919576498**, 0.71125390574362]; Stage 1b: a = [1.0, **-1.99724101099886**, 0.99724503976250]
- **96 kHz**  
  Stage 1a: a = [1.0, **-1.73976803439498**, 0.77968844085680]; Stage 1b: a = [1.0, **-1.99885929981498**, 0.99886032528746]

Other sample rates: bilinear transform from analog prototype.

**TASK 4A-3 — LUFSMeter**  
Config: sampleRate, numChannels, channelWeights (stereo [1,1]; 7.1.4 L,R,C=1, LFE=0, Ls,Rs,Lss,Rss,Ltf,Rtf,Ltr,Rtr=1.41). Per-channel K-weighting; 400 ms blocks, 100 ms hop; gating absolute −70 LUFS, relative −10 LU below mean. getMomentaryLUFS, getShortTermLUFS, getIntegratedLUFS, getLRA.

**TASK 4A-4 — Tests**  
`aurora-dsp/tests/test_lufs.cpp`: K-weighting response vs reference; momentary LUFS on 997 Hz tone; integrated with gating (silence gated out); 7.1.4 channel weights; sample rate consistency. Acceptance: integrated LUFS ±0.1 LU of reference.

Run: `cd aurora-dsp/build-native && cmake .. && make && ctest -V`. Report.

---

## Phase 4B — True Peak (4× oversampled FIR)

**TASK 4B-1 — FIR**  
`aurora-dsp/include/aurora/fir_filter.h`, `aurora-dsp/src/fir_filter.cpp`: FIRFilter(taps), process(), processBlock(), reset().

**TASK 4B-2 — Kaiser / coefficient generator**  
`aurora-dsp/data/tp_fir_generator.cpp`: Kaiser β from A=50 dB (β ≈ 4.541). 48-tap lowpass at normalized fc=0.25 for 4× oversample; sinc + Kaiser window; normalize; output 4 polyphase branches (12 taps each).

**TASK 4B-3 — TruePeakMeter**  
`aurora-dsp/include/aurora/true_peak.h`, `aurora-dsp/src/true_peak.cpp`: 4× polyphase FIR per channel; processBlock updates max absolute value; getTruePeakLinear, getTruePeakDBTP, getPerChannelTruePeakDBTP, exceedsCeiling(ceilingDBTP).

**TASK 4B-4 — Tests**  
`aurora-dsp/tests/test_true_peak.cpp`: DC true peak; full-scale sine ≈ +3.01 dBTP; worst-case adjacent +1,-1; stopband ≥50 dB; passband flatness ±0.01 dB; multi-channel; exceedsCeiling. Acceptance: ±0.05 dBTP, stopband ≥50 dB.

Run CTest. Report.

---

## Phase 4C — 6-band LR8 crossover

**TASK 4C-1 — Butterworth biquads**  
`aurora-dsp/include/aurora/crossover.h`, `aurora-dsp/src/crossover.cpp`: computeLowpass(sampleRate, fc, Q), computeHighpass(...). 4th-order Butterworth Q1=0.5412, Q2=1.3066. Bilinear with prewarp.

**TASK 4C-2 — LR8 point**  
LR8CrossoverPoint(sampleRate, crossoverFreqHz): 4× LP biquads + 4× HP biquads. Output { lowpass, highpass }. process(), reset().

**TASK 4C-3 — MultibandCrossover**  
Crossover freqs 40, 160, 600, 2500, 8000 Hz. Parallel topology: Band1=LP@40, Band2=HP@40*LP@160, … Band6=HP@8000. process() → BandOutput (6 bands); recombine = sum of bands.

**TASK 4C-4 — Tests**  
`aurora-dsp/tests/test_multiband.cpp`: Sum-to-unity ±0.01 dB 20 Hz–20 kHz (CRITICAL); −6 dB at each crossover; band isolation; phase coherence (transient cross-correlation >0.99); multi–sample-rate. Acceptance: LP+HP unity ±0.01 dB, −6 dB at crossover.

Run CTest. Report.

---

## Phase 4D — Per-band compressor and dynamic EQ

**TASK 4D-1 — Envelope follower**  
`aurora-dsp/include/aurora/envelope.h`, `aurora-dsp/src/envelope.cpp`: Config (attackMs, releaseMs, rmsWindowMs, mode Peak/RMS/PeakHold). process() → envelope dB; attack/release coeffs exp(-1/(T*sr)).

**TASK 4D-2 — BandCompressor**  
`aurora-dsp/include/aurora/compressor.h`, `aurora-dsp/src/compressor.cpp`: CompressorParams (threshold, ratio, attack, release, makeup, knee, lookahead, rmsWindow, sidechain HPF, programDependent). computeGainReduction (soft knee); process → output + gainReductionDB; optional lookahead delay; stereo linking (max L/R envelope).

**TASK 4D-3 — MultibandCompressor**  
`aurora-dsp/include/aurora/multiband_compressor.h`, `aurora-dsp/src/multiband_compressor.cpp`: MultibandCrossover + 6× BandCompressor (stereo-linked); processBlockStereo; optional per-band GR metering.

**TASK 4D-4 — DynamicEQ**  
`aurora-dsp/include/aurora/dynamic_eq.h`, `aurora-dsp/src/dynamic_eq.cpp`: Up to 8 bands (Peak/LowShelf/HighShelf/BandPass); threshold, ratio (compression/expansion), attack, release; sidechain Internal/External/FrequencyShifted. Modulate band gain from sidechain level; update EQ coeffs periodically (e.g. every 32 samples).

**TASK 4D-5 — Tests**  
`aurora-dsp/tests/test_compressor.cpp`: unity at ratio 1; known gain reduction; soft knee; attack/release timing; program-dependent; lookahead; stereo linking; multiband no crossover artifacts.  
`aurora-dsp/tests/test_dynamic_eq.cpp`: static band gain; dynamic compression; upward expansion.

Run: `ctest --output-on-failure -V`. Report.

---

## End of Part 3

**Halt.** Report: (1) Files created/modified. (2) All CTest results (4A–4D). (3) Any deviations.  
**Do not proceed to Part 4 until instructed.**
