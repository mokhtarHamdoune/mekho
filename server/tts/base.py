from abc import ABC, abstractmethod

class TTSProvider(ABC):
    @abstractmethod
    def load(self) -> None:
        pass

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """Convert text to WAV bytes (24 kHz, mono, float32)."""
        pass
