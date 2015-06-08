from .channel import Channel

# Load a backend
from .backends.memory import InMemoryChannelBackend
DEFAULT_CHANNEL_LAYER = "default"
channel_layers = {
    DEFAULT_CHANNEL_LAYER: InMemoryChannelBackend(),
}

# Ensure monkeypatching
from .hacks import monkeypatch_django
monkeypatch_django()
