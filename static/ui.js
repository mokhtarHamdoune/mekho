/**
 * ui.js — UIController
 *
 * Owns every DOM element and the orb visual state.
 * This is the only file allowed to touch the page's text content,
 * CSS classes, data attributes, or the canvas context.
 *
 * Consumed by app.js:
 *   const ui = new UIController();
 *   ui.toIdle()            // orb: idle,       label: 'Listening…'
 *   ui.toRecording()       // orb: recording,  label: 'Listening…'
 *   ui.toTranscribing()    // orb: processing, label: 'Transcribing…'
 *   ui.toThinking()        // orb: processing, label: 'Thinking…'
 *   ui.toSpeaking()        // orb: speaking,   label: 'Speaking…'
 *   ui.toIdle('Custom')    // any method accepts an optional label override
 *   ui.updateStatus(text)  // standalone label update — orb state unchanged
 *   ui.showTranscript('hello world');
 *   ui.appendReply('Sure, here is what I found.');
 *   ui.clearTurn();
 *
 * Orb state values (set internally by the named methods above)
 * ──────────────────────────────────────────────────────────────────────────
 *   'idle'        → breathing pulse, blue
 *   'recording'   → reacts to mic amplitude, green
 *   'processing'  → spinning ring, amber  (transcribing + thinking)
 *   'speaking'    → reacts to playback amplitude, purple
 */

'use strict';

class UIController {
  constructor() {
    // ── DOM references ───────────────────────────────────────────────────────
    /** @type {HTMLElement} One-line state description below the orb */
    this._statusEl = document.getElementById('status-text');

    /** @type {HTMLElement} What Whisper heard — shown in italic, dimmed */
    this._transcriptEl = document.getElementById('transcript-text');

    /** @type {HTMLElement} Streamed assistant reply, filled sentence by sentence */
    this._replyEl = document.getElementById('reply-text');


    // ── Internal state ───────────────────────────────────────────────────────
    /**
     * Current visual state of the orb.
     * Read by app.js canvas drawing on every animation frame.
     * @type {'idle'|'recording'|'processing'|'speaking'}
     */
    this._orbState = 'idle';
  }

  // ── Getters ────────────────────────────────────────────────────────────────

  /**
   * The current orb state — read by the canvas animation loop in app.js
   * to choose colors and animation style.
   * @returns {'idle'|'recording'|'processing'|'speaking'}
   */
  get orbState() {
    return this._orbState;
  }

  // ── State ──────────────────────────────────────────────────────────────────

  /**
   * setOrbState — change the orb visual state.
   *
   * Keeps the internal state variable and the button's data-state attribute
   * in sync so both the canvas animation and CSS button styles stay consistent.
   *
   * @param {'idle'|'recording'|'processing'|'speaking'} state
   */
  setOrbState(state) {
    this._orbState = state;
  }

  // ── Text updates ───────────────────────────────────────────────────────────

  /**
   * updateStatus — replace the one-line status label beneath the orb.
   * Examples: "Press and hold to talk", "Thinking…", "Disconnected."
   *
   * @param {string} text
   */
  updateStatus(text) {
    this._statusEl.textContent = text;
  }

  // ── Named state transitions ────────────────────────────────────────────────
  // Each method sets the orb state and status label together.
  // Pass an optional label to override the default for that state.

  /** @param {string} [label] */
  toIdle(label = 'Listening…')       { this.setOrbState('idle');       this.updateStatus(label); }

  /** @param {string} [label] */
  toRecording(label = 'Listening…')  { this.setOrbState('recording');  this.updateStatus(label); }

  /** @param {string} [label] */
  toTranscribing(label = 'Transcribing…') { this.setOrbState('processing'); this.updateStatus(label); }

  /** @param {string} [label] */
  toThinking(label = 'Thinking…')    { this.setOrbState('processing'); this.updateStatus(label); }

  /** @param {string} [label] */
  toSpeaking(label = 'Speaking…')    { this.setOrbState('speaking');   this.updateStatus(label); }

  /**
   * showTranscript — display what Whisper heard for the current turn.
   * Wraps the text in quotes and shows it in the dimmed italic area.
   *
   * @param {string} text   Raw transcript string from the server
   */
  showTranscript(text) {
    this._transcriptEl.textContent = `"${text}"`;
  }

  /**
   * appendReply — add one sentence to the assistant reply display.
   * Called once per reply_chunk message; sentences accumulate until clearTurn().
   *
   * @param {string} sentence  A single clean sentence (no markdown)
   */
  appendReply(sentence) {
    const sep = this._replyEl.textContent ? ' ' : '';
    this._replyEl.textContent += sep + sentence;
  }

  /**
   * clearTurn — wipe the transcript and reply text in preparation for a
   * new recording turn.  Called just before a new audio blob is sent.
   */
  clearTurn() {
    this._transcriptEl.textContent = '';
    this._replyEl.textContent = '';
  }
}
