// Aurora DSP WASM loader
// Loads aurora_dsp.js from /wasm/ and wraps AuroraDSPEngine

export interface AuroraDSPEngineInstance {
  setSessionParams(manifestJSON: string): void;
  renderFull(inputPtr: number, outputPtr: number, numFrames: number): void;
  getIntegratedLUFS(): number;
  getTruePeakDBTP(): number;
  delete(): void;
}

export interface AuroraDSPModule {
  AuroraDSPEngine: new (sampleRate: number, numChannels: number) => AuroraDSPEngineInstance;
  getAuroraDSPVersion(): string;
  getAuroraDSPBuildHash(): string;
  _malloc(size: number): number;
  _free(ptr: number): void;
  HEAPF32: Float32Array;
}

let modulePromise: Promise<AuroraDSPModule> | null = null;

export async function loadAuroraDSP(): Promise<AuroraDSPModule> {
  if (modulePromise) return modulePromise;

  modulePromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = '/wasm/aurora_dsp.js';
    script.onload = () => {
      // Emscripten module factory is exposed as globalThis.AuroraDSP
      const factory = (globalThis as Record<string, unknown>)['AuroraDSP'];
      if (typeof factory !== 'function') {
        reject(new Error('AuroraDSP WASM module factory not found'));
        return;
      }
      (factory as (opts: unknown) => Promise<AuroraDSPModule>)({
        locateFile: (file: string) => `/wasm/${file}`,
      })
        .then(resolve)
        .catch(reject);
    };
    script.onerror = () => reject(new Error('Failed to load aurora_dsp.js'));
    document.head.appendChild(script);
  });

  return modulePromise;
}

// Convenience: render audio buffer using WASM engine
export async function renderWithWASM(
  manifestJSON: string,
  inputBuffer: Float32Array,
  numChannels: number,
  sampleRate: number,
): Promise<{ output: Float32Array; integratedLUFS: number; truePeakDBTP: number }> {
  const mod = await loadAuroraDSP();
  const numFrames = inputBuffer.length / numChannels;
  const bytesPerFloat = 4;

  const inputPtr = mod._malloc(inputBuffer.length * bytesPerFloat);
  const outputPtr = mod._malloc(inputBuffer.length * bytesPerFloat);

  try {
    mod.HEAPF32.set(inputBuffer, inputPtr / bytesPerFloat);

    const engine = new mod.AuroraDSPEngine(sampleRate, numChannels);
    engine.setSessionParams(manifestJSON);
    engine.renderFull(inputPtr, outputPtr, numFrames);

    const integratedLUFS = engine.getIntegratedLUFS();
    const truePeakDBTP = engine.getTruePeakDBTP();
    engine.delete();

    const output = new Float32Array(inputBuffer.length);
    output.set(mod.HEAPF32.subarray(outputPtr / bytesPerFloat, outputPtr / bytesPerFloat + inputBuffer.length));

    return { output, integratedLUFS, truePeakDBTP };
  } finally {
    mod._free(inputPtr);
    mod._free(outputPtr);
  }
}
