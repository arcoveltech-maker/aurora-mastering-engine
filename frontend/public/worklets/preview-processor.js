/**
 * Aurora DSP AudioWorklet Processor
 * Runs in the AudioWorklet thread; receives params from main thread via port messages.
 * Falls back to passthrough until WASM module is loaded and initialised.
 */

const BLOCK_SIZE = 128;

class PreviewProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super(options);
    this._wasmExports = null;
    this._enginePtr   = 0;
    this._ready       = false;
    this._sampleRate  = sampleRate;

    // Gain/bypass from main thread
    this._bypass      = false;
    this._gainLinear  = 1.0;
    this._macros      = {};

    this.port.onmessage = (e) => {
      const { type, payload } = e.data || {};

      if (type === 'init_wasm') {
        this._initWasm(payload.wasmBuffer, payload.numChannels || 2);

      } else if (type === 'params') {
        if (payload.bypass    !== undefined) this._bypass     = payload.bypass;
        if (payload.gainLinear !== undefined) this._gainLinear = payload.gainLinear;
        if (payload.macros)                  this._macros     = payload.macros;
        // Forward macros to WASM engine if ready
        if (this._ready && this._wasmExports) {
          this._applyMacros(payload.macros || {});
        }

      } else if (type === 'ping') {
        this.port.postMessage({ type: 'pong', ready: this._ready });
      }
    };
  }

  async _initWasm(wasmBuffer, numChannels) {
    try {
      const { instance } = await WebAssembly.instantiate(wasmBuffer, {
        env: {
          memory: new WebAssembly.Memory({ initial: 256 }),
          abort: () => {},
        },
      });
      this._wasmExports = instance.exports;
      if (typeof this._wasmExports.aurora_create === 'function') {
        this._enginePtr = this._wasmExports.aurora_create(this._sampleRate, numChannels);
      }
      this._ready = true;
      this.port.postMessage({ type: 'wasm_ready', ptr: this._enginePtr });
    } catch (err) {
      this.port.postMessage({ type: 'wasm_error', message: String(err) });
    }
  }

  _applyMacros(macros) {
    // Future: map macros to WASM parameter setters
    // e.g. this._wasmExports.aurora_set_param(ptr, PARAM_EQ_LOW, macros.eq_low)
  }

  process(inputs, outputs, parameters) {
    const input  = inputs[0];
    const output = outputs[0];

    if (!input || input.length === 0) {
      // Silence output
      for (const ch of output) ch.fill(0);
      return true;
    }

    if (this._bypass || !this._ready) {
      // Passthrough
      for (let ch = 0; ch < output.length; ++ch) {
        const src = input[ch] || input[0];
        output[ch].set(src);
        if (this._gainLinear !== 1.0) {
          const buf = output[ch];
          for (let i = 0; i < buf.length; ++i) buf[i] *= this._gainLinear;
        }
      }
      return true;
    }

    // WASM processing path
    // For now: passthrough via WASM heap until full binding is complete
    for (let ch = 0; ch < output.length; ++ch) {
      const src = input[ch] || input[0];
      output[ch].set(src);
    }

    // Send metering data back to main thread every 4 blocks
    if (currentFrame % (BLOCK_SIZE * 4) === 0) {
      const peak = output[0]
        ? Math.max(...output[0].map(Math.abs))
        : 0;
      this.port.postMessage({ type: 'meter', peak });
    }

    return true;
  }
}

registerProcessor('preview-processor', PreviewProcessor);
