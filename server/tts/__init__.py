from .factory import get_provider

_provider = None


def load() -> None:
    global _provider
    if _provider is None:
        _provider = get_provider()
    _provider.load()


def synthesize(text: str) -> bytes:
    global _provider
    if _provider is None:
        _provider = get_provider()
    return _provider.synthesize(text)
