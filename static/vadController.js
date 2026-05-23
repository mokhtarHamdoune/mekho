/**
 * vadController.js — VADController
 *
 * Owns the Silero VAD (via @ricky0123/vad-web), the mic lifecycle,
 * and WAV encoding. Fires browser CustomEvents — app.js only wires handlers.
 *
 * Public API
 * ──────────
 *   const vadCtrl = new VADController();
 *   vadCtrl.start();    // initialize VAD and begin listening (call once at startup)
 *   vadCtrl.pause();    // suspend detection (e.g. while the assistant is speaking)
 *   vadCtrl.resume();   // resume after a pause()
 *
 * Events dispatched
 * ─────────────────
 *   'ready'        — VAD initialized and mic is live.
 *   'speech-start' — Voice activity detected.
 *   'speech-end'   — CustomEvent — detail: { wav: ArrayBuffer }
 *                    User finished speaking; WAV audio is ready to send.
 *   'misfire'      — Detected audio was too short to be real speech.
 *   'error'        — CustomEvent — detail: { error: Error }
 *                    Mic access denied or VAD initialization failed.
 */

'use strict';

class VADController extends EventTarget {
  static ONNX_WASM_BASE  = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.22.0/dist/';
  static BASE_ASSET_PATH = 'https://cdn.jsdelivr.net/npm/@ricky0123/vad-web@0.0.29/dist/';

  constructor() {
    super();
    this._vad = null;
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * start — initialize Silero VAD and begin listening.
   * Dispatches 'ready' on success, 'error' on failure.
   * Call once; use pause() / resume() for subsequent control.
   */
  async start() {
    try {
      this._vad = await vad.MicVAD.new({
        onSpeechStart: () => {
            console.info('Speech started');
          this.dispatchEvent(new CustomEvent('speech-start'));
        },
        onSpeechEnd: (audio) => {
          const wav = VADController._encodeWav(audio);
          this.dispatchEvent(new CustomEvent('speech-end', { detail: { wav } }));
        },
        onVADMisfire: () => {
          this.dispatchEvent(new CustomEvent('misfire'));
        },
        onnxWASMBasePath: VADController.ONNX_WASM_BASE,
        baseAssetPath:    VADController.BASE_ASSET_PATH,
      });
      this._vad.start();
      this.dispatchEvent(new CustomEvent('ready'));
    } catch (error) {
      this.dispatchEvent(new CustomEvent('error', { detail: { error } }));
    }
  }

  /** Suspend voice detection (e.g. while the assistant is speaking). */
  pause()  { this._vad?.pause(); }

  /** Resume voice detection after a pause(). */
  resume() { this._vad?.start(); }

  // ── Private ────────────────────────────────────────────────────────────────

  /**
   * _encodeWav — encode Float32 16 kHz mono PCM samples into a RIFF WAV ArrayBuffer.
   * Whisper accepts this directly without any re-muxing.
   *
   * @param {Float32Array} float32Array  Raw PCM samples from onSpeechEnd
   * @param {number}       sampleRate    Always 16000 for Silero VAD output
   * @returns {ArrayBuffer}
   */
  static _encodeWav(float32Array, sampleRate = 16000) {
    const numSamples = float32Array.length;
    const buffer     = new ArrayBuffer(44 + numSamples * 2);
    const view       = new DataView(buffer);

    function writeStr(offset, str) {
      for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    }

    writeStr(0, 'RIFF');
    view.setUint32(4,  36 + numSamples * 2, true);
    writeStr(8,  'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16,             true);   // chunk size
    view.setUint16(20, 1,              true);   // PCM
    view.setUint16(22, 1,              true);   // mono
    view.setUint32(24, sampleRate,     true);   // sample rate
    view.setUint32(28, sampleRate * 2, true);   // byte rate
    view.setUint16(32, 2,              true);   // block align
    view.setUint16(34, 16,             true);   // bits per sample
    writeStr(36, 'data');
    view.setUint32(40, numSamples * 2, true);

    for (let i = 0; i < numSamples; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return buffer;
  }
}
