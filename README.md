# Mekho

Mekho is a simple Voice Assistant designed to provide a layer of interaction over various AI models and modules. It serves as a lightweight and extensible platform for voice-based AI interactions.

## How it works:

Mekho acts as a bridge between the user and underlying AI models, enabling voice-based commands and responses. It integrates multiple AI modules to deliver a seamless experience.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mokhtarHamdoune/mekho
   cd Mekho
   ```
2. Set up a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Run server

To start the server, run the following command:

```bash
uvicorn server.main:app
```

The server will start, and you can interact with Mekho through its voice interface.

## Objectives

- Turn the assistant into an action-capable voice agent.
- Keep the architecture simple enough to evolve.
- Preserve a clear boundary between model, backend, and frontend.

## Agent Progress

- [x] **important!** Voice Mode
- [x] **important!** Tools Support ( Contract + Registry)
- [x] **important!** Voice Activity Detector
- [] **important!** Support Arabic (Algerian, Moroccan , Gulf)
- [] New Session Action
- [] Support French

## Tools Progress:

### Shopping Cart Tool

- [x] Adding An Item To Shopping Cart
- [x] Removing An Item From Shopping Cart
- [] Possible Current Cart State For The LLM (We may need to store the state after each change)

### Catalog Tool

- [x] Search Product Tool
- [x] Product Details Tool
- [] Simple Product Recommendation Tool

## Checkout Tool

- [] Simple Order Confirmation Tool That Close The Loop and

## Sequence diagram

```mermaid
sequenceDiagram
    actor User
    participant Browser as Browser (Frontend)
    participant VAD as Silero VAD<br/>(ONNX in browser)
    participant WS as WebSocket
    participant Server as FastAPI Server
    participant ASR as Whisper (ASR)
    participant LLM as LLM Session
    participant TTS as TTS Engine

    Note over Browser,VAD: VAD runs continuously in background
    User ->> Browser: Speaks (no button press)
    Browser ->> VAD: Feed 30ms audio chunks
    VAD -->> Browser: onSpeechStart (probability > 0.5)
    Browser ->> Browser: Set orb → recording, buffer audio
    VAD -->> Browser: onSpeechEnd (silence detected)
    Browser ->> WS: Send WebM/WAV blob (binary frame)
    WS ->> Server: audio_bytes received
    Server ->> WS: status: "transcribing"
    Server ->> ASR: transcribe_bytes(audio_bytes)
    ASR -->> Server: transcript text
    Server ->> WS: { type: "transcript", text: "..." }
    Server ->> LLM: ask_stream(transcript)
    Server ->> WS: status: "thinking"
    loop per sentence
        LLM -->> Server: sentence chunk
        Server ->> WS: { type: "reply_chunk", text: "..." }
        Server ->> TTS: synthesize(sentence)
        TTS -->> Server: WAV bytes
        Server ->> WS: binary WAV frame
        WS ->> Browser: WAV audio
        Server ->> WS: status: "speaking"
        Browser ->> User: Plays audio via AudioPlayer
    end
    Server ->> WS: status: "idle"
    Browser ->> VAD: Resume listening

```
