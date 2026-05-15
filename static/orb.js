/**
 * orb.js — OrbAnimator
 *
 * Owns the <canvas> element and everything needed to animate the orb.
 * Reads the current visual state from UIController each frame, and reads
 * audio amplitude from AnalyserNodes supplied by the recorder and audio player.
 *
 * Consumed by app.js:
 *   const orb = new OrbAnimator(document.getElementById('orb-canvas'), ui);
 *   orb.start();                          // kick off the rAF loop — call once
 *   orb.setMicAnalyser(analyserOrNull);   // set/clear while recording
 *   orb.setPlaybackAnalyser(analyserOrNull); // set/clear while playing audio
 *
 * Visual states (driven by ui.orbState, set by UIController)
 * ────────────────────────────────────────────────────────────
 *   idle        → slow breathing sine pulse             (blue)
 *   recording   → expands with microphone amplitude     (green)
 *   processing  → gentle pulse + rotating arc ring      (amber)
 *   speaking    → expands with playback amplitude       (purple)
 */

'use strict';

class OrbAnimator {
  // ── Configuration ──────────────────────────────────────────────────────────

  /** Internal canvas resolution in logical pixels (CSS controls display size) */
  static CANVAS_SIZE = 400;

  /** Resting orb radius in canvas pixels */
  static BASE_RADIUS = 90;

  /** Max extra pixels the orb grows when audio amplitude is at 1.0 */
  static AMPLITUDE_SCALE = 65;

  /** FFT bin count for AnalyserNode reads — must be a power of 2 */
  static FFT_SIZE = 256;

  /**
   * Gradient colours per visual state.
   * Each entry is [innerColor, outerColor] for a radial gradient.
   * The outer colour is always fully transparent so the orb blends into the
   * dark background without a hard edge.
   */
  static COLORS = {
    idle:       ['rgba(80,  160, 255, 0.85)', 'rgba(30,   80, 200, 0)'],
    recording:  ['rgba(60,  210, 110, 0.90)', 'rgba(20,  150,  60, 0)'],
    processing: ['rgba(255, 185,  50, 0.90)', 'rgba(200, 100,   0, 0)'],
    speaking:   ['rgba(185,  75, 255, 0.90)', 'rgba(100,  20, 180, 0)'],
  };

  // ── Constructor ────────────────────────────────────────────────────────────

  /**
   * @param {HTMLCanvasElement} canvasEl  The canvas to draw on
   * @param {UIController}      ui        Provides orbState each frame
   */
  constructor(canvasEl, ui) {
    this._ui     = ui;
    this._canvas = canvasEl;
    this._ctx    = canvasEl.getContext('2d');

    // Set internal resolution; CSS width/height controls display size
    this._canvas.width  = OrbAnimator.CANVAS_SIZE;
    this._canvas.height = OrbAnimator.CANVAS_SIZE;

    // Animation phase accumulators
    this._idlePhase       = 0;   // sine wave phase for idle / processing breath
    this._processingAngle = 0;   // rotation angle for the spinner arc

    // Reusable buffer for reading frequency data from AnalyserNodes
    this._dataArray = new Uint8Array(OrbAnimator.FFT_SIZE / 2);

    // AnalyserNodes — updated externally via setters
    this._micAnalyser      = null;
    this._playbackAnalyser = null;
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * start — kick off the requestAnimationFrame draw loop.
   * Call exactly once during app initialisation.
   */
  start() {
    const loop = () => {
      this._draw();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  /**
   * setMicAnalyser — supply (or clear) the AnalyserNode connected to the mic.
   * Pass null when recording stops so the orb stops reacting to mic amplitude.
   *
   * @param {AnalyserNode | null} analyser
   */
  setMicAnalyser(analyser) {
    this._micAnalyser = analyser;
  }

  /**
   * setPlaybackAnalyser — supply (or clear) the AnalyserNode connected to the
   * currently playing audio source.
   * Pass null when the queue empties so the orb stops reacting to playback.
   *
   * @param {AnalyserNode | null} analyser
   */
  setPlaybackAnalyser(analyser) {
    this._playbackAnalyser = analyser;
  }

  // ── Private ────────────────────────────────────────────────────────────────

  /**
   * _getAmplitude — read average frequency amplitude from an AnalyserNode.
   * Returns a value in [0, 1].  Returns 0 if no analyser is wired.
   *
   * @param {AnalyserNode | null} analyser
   * @returns {number}
   */
  _getAmplitude(analyser) {
    if (!analyser) return 0;
    analyser.getByteFrequencyData(this._dataArray);
    const sum = this._dataArray.reduce((a, b) => a + b, 0);
    return sum / (this._dataArray.length * 255);
  }

  /**
   * _draw — render one animation frame onto the canvas.
   * Reads ui.orbState to determine which visual to produce.
   */
  _draw() {
    const { CANVAS_SIZE, BASE_RADIUS, AMPLITUDE_SCALE, COLORS } = OrbAnimator;
    const cx    = CANVAS_SIZE / 2;
    const cy    = CANVAS_SIZE / 2;
    const state = this._ui.orbState;

    this._ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

    const [innerColor, outerColor] = COLORS[state] ?? COLORS.idle;
    let radius = BASE_RADIUS;

    switch (state) {
      case 'idle':
        this._idlePhase += 0.025;
        radius += Math.sin(this._idlePhase) * 12;
        break;

      case 'recording':
        radius += this._getAmplitude(this._micAnalyser) * AMPLITUDE_SCALE;
        break;

      case 'speaking':
        radius += this._getAmplitude(this._playbackAnalyser) * AMPLITUDE_SCALE;
        break;

      case 'processing':
        // Background pulse so it doesn't look frozen while waiting for the server
        this._idlePhase += 0.04;
        radius += Math.sin(this._idlePhase) * 8;
        // Rotating arc ring drawn just outside the main orb body
        this._drawSpinnerRing(cx, cy, radius + 26, innerColor);
        break;
    }

    // Main orb — radial gradient fills a circle
    const gradient = this._ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
    gradient.addColorStop(0, innerColor);
    gradient.addColorStop(1, outerColor);

    this._ctx.beginPath();
    this._ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    this._ctx.fillStyle = gradient;
    this._ctx.fill();
  }

  /**
   * _drawSpinnerRing — a short rotating arc around the orb.
   * Used only in the 'processing' state to signal server activity.
   *
   * @param {number} cx     canvas centre X
   * @param {number} cy     canvas centre Y
   * @param {number} r      ring radius (larger than the orb)
   * @param {string} color  stroke colour — matches the orb's inner colour
   */
  _drawSpinnerRing(cx, cy, r, color) {
    this._processingAngle += 0.07;         // rotation speed
    const start = this._processingAngle;
    const end   = start + Math.PI * 1.2;  // ~216° visible arc

    this._ctx.beginPath();
    this._ctx.arc(cx, cy, r, start, end);
    this._ctx.strokeStyle = color;
    this._ctx.lineWidth   = 4;
    this._ctx.lineCap     = 'round';
    this._ctx.stroke();
  }
}
