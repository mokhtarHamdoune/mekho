from ..config import TTS_PROVIDER, LANGUAGE
from .kokoro_provider import KokoroProvider
from .edge_provider import EdgeProvider
from .supertonic_provider import SupertonicProvider


def get_provider():
    provider = TTS_PROVIDER
    if provider == "auto":
        provider = "kokoro" if LANGUAGE == "en" else "supertonic"
    if provider == "kokoro":
        return KokoroProvider()
    if provider == "edge":
        return EdgeProvider()
    if provider == "supertonic":
        return SupertonicProvider()
    raise ValueError(f"Unknown TTS_PROVIDER: {provider}")
