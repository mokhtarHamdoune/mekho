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
 *   const player = new AudioPlayer(orb);
 *   const audioCtx = player.ensureContext();  // call on first user gesture
 *   player.enqueue(wavArrayBuffer);           // called on each binary WS frame
 *
 * Playback flow
 * ─────────────
 *   enqueue(wav) → push to FIFO queue → if idle, call _playNext()
 *   _playNext()  → decodeAudioData → BufferSourceNode → AnalyserNode → destination
 *                → notifies OrbAnimator of the live analyser
 *                → on 'ended' event, recurse to drain the queue
 */

'use strict';

class AudioPlayer {
  /** FFT bin count for the playback AnalyserNode — must be a power of 2 */
  static FFT_SIZE = 256;

  /**
   * @param {OrbAnimator} orb  Receives setPlaybackAnalyser() calls so the orb
   *                           can react to the speaking amplitude in real time.
   */
  constructor(orb) {
    this._orb   = orb;
    this._ctx   = null;   // AudioContext — created lazily on first user gesture
    this._queue = [];     // FIFO of WAV ArrayBuffers waiting to be decoded
    this._busy  = false;  // true while a BufferSourceNode is actively playing
  }

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
   * The source node is wired through an AnalyserNode so OrbAnimator can read
   * the real-time playback amplitude for the speaking animation.
   *
   * Recurses via the source's 'ended' event, creating a seamless
   * sentence-by-sentence playback chain.
   */
  async _playNext() {
    if (this._queue.length === 0) {
      this._busy = false;
      // Tell the orb there's no longer any playback signal to track
      this._orb.setPlaybackAnalyser(null);
      return;
    }

    this._busy = true;
    const wavBuffer = this._queue.shift();

    try {
      const audioBuffer = await this._ctx.decodeAudioData(wavBuffer);
      const source = this._ctx.createBufferSource();
      source.buffer = audioBuffer;

      // Wire through an analyser so the orb reacts to playback amplitude
      const analyser = this._ctx.createAnalyser();
      analyser.fftSize = AudioPlayer.FFT_SIZE;
      source.connect(analyser);
      analyser.connect(this._ctx.destination);
      this._orb.setPlaybackAnalyser(analyser);

      // Chain the next sentence automatically when this one finishes
      source.addEventListener('ended', () => this._playNext());
      source.start();
    } catch (err) {
      // Skip a corrupted or empty chunk rather than stalling the whole queue
      console.error('[AudioPlayer] Failed to decode WAV chunk — skipping:', err);
      this._playNext();
    }
  }
}
