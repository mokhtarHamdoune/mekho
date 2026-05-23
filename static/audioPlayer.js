/**
 * audioPlayer.js — AudioPlayer
 *
 * Owns the Web Audio AudioContext, the WAV playback queue, and the
 * playback AnalyserNode used by OrbAnimator for the speaking animation.
 *
 * The AudioContext is also shared with the recorder in app.js —
 * call ensureContext() from within a user gesture to create/resume it,
 * then use the returned AudioContext to wire the mic stream.
 *
 * Consumed by app.js:
 *   const player = new AudioPlayer();
 *   player.addEventListener('playback-start', ({ detail: { analyser } }) => …);
 *   player.addEventListener('playback-end', () => …);
 *   const audioCtx = player.ensureContext();  // call on first user gesture
 *   player.enqueue(wavArrayBuffer);           // called on each binary WS frame
 *
 * Events dispatched
 * ─────────────────
 *   'playback-start'  CustomEvent — detail: { analyser: AnalyserNode }
 *                     fired each time a new WAV chunk starts playing.
 *   'playback-end'    CustomEvent — fired when the queue fully drains.
 *
 * Playback flow
 * ─────────────
 *   enqueue(wav) → push to FIFO queue → if idle, call _playNext()
 *   _playNext()  → decodeAudioData → BufferSourceNode → AnalyserNode → destination
 *                → dispatches 'playback-start' with the live analyser
 *                → on 'ended' event, recurse to drain the queue
 *                → dispatches 'playback-end' when queue is empty
 */

'use strict';

class AudioPlayer extends EventTarget {
  /** FFT bin count for the playback AnalyserNode — must be a power of 2 */
  static FFT_SIZE = 256;

  constructor() {
    super();
    this._ctx   = null;   // AudioContext — created lazily on first user gesture
    this._queue = [];     // FIFO of WAV ArrayBuffers waiting to be decoded
    this._busy  = false;  // true while a BufferSourceNode is actively playing
  }

  /** @returns {boolean} true while audio is actively playing */
  get isBusy() { return this._busy; }

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * ensureContext — create or resume the shared Web Audio AudioContext.
   *
   * Browser autoplay policy requires AudioContext creation to happen inside
   * a user gesture handler (click, mousedown, touchstart, etc.).
   * Always call this before the first getUserMedia or enqueue() call.
   *
   * Returns the AudioContext so the recorder in app.js can wire the mic stream
   * to an AnalyserNode using the same context.
   *
   * @returns {AudioContext}
   */
  ensureContext() {
    if (!this._ctx) {
      this._ctx = new AudioContext();
    } else if (this._ctx.state === 'suspended') {
      this._ctx.resume();
    }
    return this._ctx;
  }

  /**
   * enqueue — add a WAV ArrayBuffer to the playback queue.
   * If nothing is currently playing, playback starts immediately.
   *
   * @param {ArrayBuffer} wavBuffer  Raw WAV bytes from the server
   */
  enqueue(wavBuffer) {
    this._queue.push(wavBuffer);
    if (!this._busy) this._playNext();
  }

  // ── Private ────────────────────────────────────────────────────────────────

  /**
   * _playNext — decode and play the next WAV buffer in the queue.
   *
   * Dispatches 'playback-start' with the live AnalyserNode when a chunk begins,
   * and 'playback-end' when the queue fully drains.
   * Recurses via the source's 'ended' event for seamless sentence-by-sentence playback.
   */
  async _playNext() {
    if (this._queue.length === 0) {
      this._busy = false;
      this.dispatchEvent(new CustomEvent('playback-end'));
      return;
    }

    this._busy = true;
    const wavBuffer = this._queue.shift();

    try {
      const audioBuffer = await this._ctx.decodeAudioData(wavBuffer);
      const source = this._ctx.createBufferSource();
      source.buffer = audioBuffer;

      const analyser = this._ctx.createAnalyser();
      analyser.fftSize = AudioPlayer.FFT_SIZE;
      source.connect(analyser);
      analyser.connect(this._ctx.destination);
      this.dispatchEvent(new CustomEvent('playback-start', { detail: { analyser } }));

      source.addEventListener('ended', () => this._playNext());
      source.start();
    } catch (err) {
      console.error('[AudioPlayer] Failed to decode WAV chunk — skipping:', err);
      this._playNext();
    }
  }
}
