# TTS Providers

This package provides a swappable TTS interface for the project.

- `base.py`: Abstract interface for TTS providers.
- `kokoro_provider.py`: Wrapper for Kokoro TTS 82M (English, local).
- `edge_provider.py`: Wrapper for edge-tts (Arabic, cloud).
- `supertonic_provider.py`: Wrapper for supertonic v3 99M (local)
- `factory.py`: Selects provider based on config.
- `__init__.py`: Exposes `synthesize()` for callers.

Add new providers by implementing `TTSProvider` and updating `factory.py`.
