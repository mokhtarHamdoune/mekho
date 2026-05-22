/**
 * app.js — Mekho Voice Assistant — orchestration
 *
 * This file is intentionally thin.  All domain logic lives in the modules
 * loaded before it (see index.html):
 *
 *   ui.js          → UIController   — DOM updates, orb state, button styling
 *   orb.js         → OrbAnimator    — canvas drawing, amplitude animation
 *   audioPlayer.js → AudioPlayer    — WAV playback queue, AudioContext
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
const player = new AudioPlayer(orb);
const cart   = new CartPanel();

// =============================================================================
// Recording state
// =============================================================================

let mediaRecorder = null;   // active MediaRecorder, non-null only while recording
let audioChunks   = [];     // Blob chunks accumulated from MediaRecorder
let micStream     = null;   // MediaStream from getUserMedia

// =============================================================================
// WebSocket
// =============================================================================

const ws = new WebSocket(`ws://${location.host}/ws`);
ws.binaryType = 'arraybuffer';

ws.addEventListener('open', () => {
  console.info('[WS] Connected');
  ui.setOrbState('idle');
  ui.updateStatus('Press and hold to talk');
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

/** Maps server status strings → orb state + status label */

function onStatus(status) {
  const STATES = {
    transcribing: ['processing', 'Transcribing…'],
    thinking:     ['processing', 'Thinking…'],
    speaking:     ['speaking',   'Speaking…'],
    idle:         ['idle',       'Press and hold to talk'],
  };
  const [orbState, label] = STATES[status] ?? ['idle', ''];
  ui.setOrbState(orbState);
  ui.updateStatus(label);
}

// =============================================================================
// Push-to-talk recording
// =============================================================================

/**
 * startRecording — called on mousedown / touchstart.
 *
 * 1. Ensures the shared AudioContext exists (browser autoplay policy).
 * 2. Opens the microphone and wires it to an AnalyserNode for the orb.
 * 3. Starts the MediaRecorder buffering WebM/Opus chunks.
 */
async function startRecording() {
  // ensureContext() must be called inside a user gesture
  const audioCtx = player.ensureContext();

  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  } catch (err) {
    console.error('[Mic] Permission denied:', err);
    ui.updateStatus('Microphone access denied.');
    return;
  }

  // Wire the mic stream to an AnalyserNode for the orb's recording animation.
  // NOT connected to audioCtx.destination — that would cause speaker feedback.
  const micSource = audioCtx.createMediaStreamSource(micStream);
  const micAnalyser = audioCtx.createAnalyser();
  micAnalyser.fftSize = 256;
  micSource.connect(micAnalyser);
  orb.setMicAnalyser(micAnalyser);

  audioChunks = [];
  mediaRecorder = new MediaRecorder(micStream);
  mediaRecorder.addEventListener('dataavailable', (e) => {
    if (e.data.size > 0) audioChunks.push(e.data);
  });
  mediaRecorder.addEventListener('stop', onRecordingStop);
  mediaRecorder.start();

  ui.setOrbState('recording');
  ui.updateStatus('Recording…');
}

/** stopRecording — called on mouseup / touchend / mouseleave. */
function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
}

/**
 * onRecordingStop — fired after MediaRecorder flushes all chunks.
 * Releases the mic, assembles the WebM blob, and sends it to the server.
 */
async function onRecordingStop() {
  micStream.getTracks().forEach((t) => t.stop());
  micStream = null;
  orb.setMicAnalyser(null);

  const blob   = new Blob(audioChunks, { type: 'audio/webm' });
  const buffer = await blob.arrayBuffer();

  ui.clearTurn();           // clear previous turn's transcript + reply
  ws.send(buffer);
  ui.setOrbState('processing');
  ui.updateStatus('Transcribing…');
}

// =============================================================================
// Push-to-talk event listeners
// =============================================================================

ui.talkBtn.addEventListener('mousedown',  startRecording);
ui.talkBtn.addEventListener('mouseup',    stopRecording);
ui.talkBtn.addEventListener('mouseleave', stopRecording);  // released outside button
ui.talkBtn.addEventListener('touchstart', (e) => { e.preventDefault(); startRecording(); });
ui.talkBtn.addEventListener('touchend',   stopRecording);

// ── Ctrl key — hold to record, release to send ────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.key === 'Control' && !e.repeat && mediaRecorder === null) {
    startRecording();
  }
});
document.addEventListener('keyup', (e) => {
  if (e.key === 'Control') {
    stopRecording();
  }
});

// =============================================================================
// Init
// =============================================================================

orb.start();   // begin the rAF animation loop (shows breathing orb while WS connects)






