"""
FastAPI server — entry point.

TODO — Phase 2: Client / Shop Assistant
────────────────────────────────────────
1. Add server/products.json  — small product catalog (name, description, qty available).
2. Add server/catalog.py     — load_catalog() helper that reads products.json.
3. Update SYSTEM_PROMPT      — inject catalog data so the LLM knows what is in stock.
4. Play a greeting on startup via TTS (company name + "How can I help you today?").
5. Add cart state per session (simple dict: {product_id: qty}).
6. Handle "add to cart" / "remove from cart" intents in the LLM reply loop.
7. (Later) Replace prompt injection with proper LLM tool/function calling
   so the LLM can call get_product_info() on demand instead of loading
   the full catalog into every prompt.

WebSocket message protocol
──────────────────────────
Client → Server:
  binary frame  : raw audio blob (WebM/Opus from MediaRecorder, or WAV)

Server → Client:
  text frame    : JSON  {"type": "status",       "text": "transcribing"|"thinking"|"speaking"|"idle"}
  text frame    : JSON  {"type": "transcript",   "text": "<what the user said>"}
  text frame    : JSON  {"type": "reply_chunk",  "text": "<one sentence of the reply>"}
  text frame    : JSON  {"type": "cart_update",  "cart": {<product_id>: <qty>, ...}}
  binary frame  : WAV bytes for the sentence in the preceding reply_chunk message

Run with:
  uvicorn server.main:app --host 127.0.0.1 --port 8080 --reload
"""

import asyncio
import json
import logging
import re

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from . import transcriber, tts
from .llm import LLMSession
from .catalog import load_catalog, find_product
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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    session = LLMSession()
    cart: dict[str, int] = {}  # {product_id: qty}
    loop = asyncio.get_event_loop()
    logger.info("Client connected  [%s]", websocket.client)

    async def send_status(status: str) -> None:
        await websocket.send_text(json.dumps({"type": "status", "text": status}))

    async def send_cart() -> None:
        await websocket.send_text(json.dumps({"type": "cart_update", "cart": cart}))

    def _apply_cart_actions(reply_text: str) -> None:
        """Parse the LLM reply for cart signals and update cart state."""
        # "Added to your cart" → look for a product name match in the reply
        if re.search(r"\badded to your cart\b", reply_text, re.IGNORECASE):
            for product in load_catalog():
                if product["name"].lower() in reply_text.lower():
                    # Default qty to 1 unless a number is mentioned nearby
                    qty_match = re.search(
                        rf"(\d+)\s+(?:units?\s+of\s+)?{re.escape(product['name'])}",
                        reply_text, re.IGNORECASE,
                    )
                    qty = int(qty_match.group(1)) if qty_match else 1
                    cart[product["id"]] = cart.get(product["id"], 0) + qty
                    logger.info("Cart add: %s x%d", product["id"], qty)

        # "Removed from your cart"
        if re.search(r"\bremoved from your cart\b", reply_text, re.IGNORECASE):
            for product in load_catalog():
                if product["name"].lower() in reply_text.lower():
                    cart.pop(product["id"], None)
                    logger.info("Cart remove: %s", product["id"])


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
            full_reply_parts: list[str] = []
            async for sentence in session.ask_stream(transcript):
                logger.info("Sentence: %s", sentence)
                full_reply_parts.append(sentence)

                await websocket.send_text(json.dumps({"type": "reply_chunk", "text": sentence}))
                await send_status("speaking")

                audio_wav: bytes = await loop.run_in_executor(None, tts.synthesize, sentence)
                await websocket.send_bytes(audio_wav)

            # ── 4. Update cart based on full reply ────────────────────────────
            full_reply = " ".join(full_reply_parts)
            cart_before = dict(cart)
            _apply_cart_actions(full_reply)
            if cart != cart_before:
                await send_cart()

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
