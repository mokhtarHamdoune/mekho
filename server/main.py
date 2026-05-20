"""
FastAPI server — entry point.

WebSocket message protocol
──────────────────────────
Client → Server:
  binary frame  : raw audio blob (WebM/Opus from MediaRecorder, or WAV)

Server → Client:
  text frame    : JSON  {"type": "status",       "text": "transcribing"|"thinking"|"speaking"|"idle"}
  text frame    : JSON  {"type": "transcript",   "text": "<what the user said>"}
  text frame    : JSON  {"type": "reply_chunk",  "text": "<one sentence of the reply>"}
  binary frame  : WAV bytes for the sentence in the preceding reply_chunk message

Run with:
  uvicorn server.main:app --host 127.0.0.1 --port 8080 --reload
"""

import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from . import transcriber, tts
from .llm import LLMSession
from .events import ToolEventEmitter
from .config import HOST, PORT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Mekho — Voice Assistant")

# Serve the frontend from the sibling static/ directory
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("static/index.html")


# ── WebSocket ─────────────────────────────────────────────────────────────────

class _WSEmitter:
    """Concrete ToolEventEmitter — forwards tool results to the browser over WS.

    Lives in main.py because it is the only place that knows about WebSocket.
    LLMSession only knows about the ToolEventEmitter Protocol.
    """

    def __init__(self, ws: WebSocket) -> None:
        self._ws = ws

    async def on_tool_result(self, tool_name: str, result: dict) -> None:
        await self._ws.send_text(json.dumps({
            "type": "tool_result",
            "tool": tool_name,
            "result": result,
        }))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    session = LLMSession(emitter=_WSEmitter(websocket))
    loop = asyncio.get_event_loop()
    logger.info("Client connected  [%s]", websocket.client)

    async def send_status(status: str) -> None:
        await websocket.send_text(json.dumps({"type": "status", "text": status}))


    try:
        while True:
            # ── 1. Receive audio from the browser ────────────────────────────
            audio_bytes: bytes = await websocket.receive_bytes()

            # ── 2. Transcribe (sync Whisper → thread executor) ────────────────
            await send_status("transcribing")
            transcript: str = await loop.run_in_executor(
                None, transcriber.transcribe_bytes, audio_bytes
            )
            logger.info("Transcript: %s", transcript)
            await websocket.send_text(json.dumps({"type": "transcript", "text": transcript}))

            if not transcript:
                await send_status("idle")
                continue

            # ── 3. Stream LLM reply sentence by sentence ──────────────────────
            await send_status("thinking")
            async for sentence in session.ask_stream(transcript):
                logger.info("Sentence: %s", sentence)
                await websocket.send_text(json.dumps({"type": "reply_chunk", "text": sentence}))
                await send_status("speaking")

                audio_wav: bytes = await loop.run_in_executor(None, tts.synthesize, sentence)
                await websocket.send_bytes(audio_wav)

            await send_status("idle")

    except WebSocketDisconnect:
        logger.info("Client disconnected [%s]", websocket.client)


# ── Dev entry-point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    # Pre-load models before the first request
    transcriber.load()
    tts.load()

    uvicorn.run("server.main:app", host=HOST, port=PORT, reload=False)
