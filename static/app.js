/**
 * app.js — Mekho Voice Assistant — orchestration
 *
 * This file is intentionally thin.  All domain logic lives in the modules
 * loaded before it (see index.html):
 *
 *   ui.js             → UIController   — DOM updates, orb state, button styling
 *   orb.js            → OrbAnimator    — canvas drawing, amplitude animation
 *   audioPlayer.js    → AudioPlayer    — WAV playback queue, AudioContext
 *   vadController.js  → VADController  — Silero VAD, WAV encoding, mic lifecycle
 *
 * What stays here
 * ───────────────
 * • WebSocket lifecycle and message routing
 * • Push-to-talk recording (getUserMedia + MediaRecorder)
 * • Wiring the three modules together on events
 *
 * WebSocket message protocol (mirrors server/main.py)
 * ────────────────────────────────────────────────────
 * Client → Server   binary frame : WebM/Opus audio blob
 * Server → Client   binary frame : WAV audio for the current sentence
 *                   text frame   : JSON { type, text }
 *                     "status"       → "transcribing" | "thinking" | "speaking" | "idle"
 *                     "transcript"   → what the user said
 *                     "reply_chunk"  → one sentence of the assistant reply
 *
 * To add tool/function calling, the server will emit a new message type
 * e.g. { type: "tool_result", tool: "...", result: {...} }
 */

'use strict';

// =============================================================================
// Module instances
// =============================================================================

const ui     = new UIController();
const orb    = new OrbAnimator(document.getElementById('orb-canvas'), ui);
const player = new AudioPlayer();
const voiceActivityCtrl    = new VADController();
const cart   = new CartPanel();

// ── AudioPlayer event wiring ──────────────────────────────────────────────────
// AudioPlayer knows nothing about the orb or app state — it just fires events.

player.addEventListener('playback-start', ({ detail: { analyser } }) => {
  orb.setPlaybackAnalyser(analyser);
});

player.addEventListener('playback-end', () => {
  orb.setPlaybackAnalyser(null);
  if (pendingIdle) {
    pendingIdle = false;
    applyIdle();
  }
});

// ── VAD event wiring ──────────────────────────────────────────────────
// VADController knows nothing about WS or app state — it just fires events.

voiceActivityCtrl.addEventListener('ready',        ()                      => ui.toIdle());
voiceActivityCtrl.addEventListener('speech-start', ()                      => ui.toRecording());
voiceActivityCtrl.addEventListener('speech-end',   ({ detail: { wav } })   => {
  ui.clearTurn();
  ws.send(wav);
  ui.toTranscribing();
});
voiceActivityCtrl.addEventListener('misfire',      ()                      => ui.toIdle());
voiceActivityCtrl.addEventListener('error',        ({ detail: { error } }) => {
  console.error('[VAD]', error);
  ui.updateStatus('Microphone access denied.');
});

// =============================================================================
// State
// =============================================================================

let pendingIdle = false;  // true when server said idle but player is still busy

// Called both when server sends idle AND when playback drains, whichever is last
function applyIdle() {
  ui.toIdle();
  voiceActivityCtrl.resume();
}

// =============================================================================
// WebSocket
// =============================================================================

const ws = new WebSocket(`ws://${location.host}/ws`);
ws.binaryType = 'arraybuffer';

ws.addEventListener('open', () => {
  console.info('[WS] Connected');
  ui.toIdle();
});

ws.addEventListener('close', () => {
  console.warn('[WS] Disconnected — reload to reconnect');
  ui.updateStatus('Disconnected. Please reload the page.');
});

ws.addEventListener('error', (e) => console.error('[WS] Error', e));

ws.addEventListener('message', (event) => {
  if (event.data instanceof ArrayBuffer) {
    player.enqueue(event.data);       // binary → WAV sentence
  } else {
    handleMessage(JSON.parse(event.data));  // text → JSON control message
  }
});

// ── Message handlers ──────────────────────────────────────────────────────────

/** @param {{ type: string, text: string }} msg */
function handleMessage(msg) {
  switch (msg.type) {
    case 'status':      onStatus(msg.text);          break;
    case 'transcript':  ui.showTranscript(msg.text); break;
    case 'reply_chunk': ui.appendReply(msg.text);    break;
    case 'tool_result': onToolResult(msg.tool, msg.result); break;
    default: console.warn('[WS] Unknown message type:', msg.type);
  }
}

/**
 * Dispatches tool results to the appropriate UI controller.
 * Both cart tools return a full `result.cart` snapshot — we hand it
 * directly to CartPanel so the UI always mirrors server state exactly.
 * @param {string} tool  The tool name (matches BaseTool.name)
 * @param {object} result  The raw dict returned by tool.run()
 */
function onToolResult(tool, result) {
  console.info('[Tool]', tool, result);
  switch (tool) {
    case 'add_to_cart':      cart.setCart(result.cart, 'add');    break;
    case 'remove_from_cart': cart.setCart(result.cart, 'remove'); break;
    default: break;
  }
}

/** Maps server status strings → orb state + status label, and pauses/resumes VAD */

function onStatus(status) {
  console.log("Status: ", status);

  if (status === 'idle') {
    if (player.isBusy) {
      pendingIdle = true;
    } else {
      applyIdle();
    }
    return;
  }

  pendingIdle = false;
  const ACTIONS = {
    transcribing: () => ui.toTranscribing(),
    thinking:     () => ui.toThinking(),
    speaking:     () => ui.toSpeaking(),
  };
  ACTIONS[status]?.();

  // Pause VAD while the server is active to avoid the assistant hearing itself
  voiceActivityCtrl.pause();
}

// =============================================================================
// Init
// =============================================================================

player.ensureContext();
voiceActivityCtrl.start();
orb.start();   // begin the rAF animation loop (shows breathing orb while WS connects)