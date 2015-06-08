from .channel import Channel
from .consumer_registry import ConsumerRegistry

# Make a site-wide registry
coreg = ConsumerRegistry()

# Load a backend
from .backends.memory import InMemoryChannelBackend
DEFAULT_CHANNEL_LAYER = "default"
channel_layers = {
    DEFAULT_CHANNEL_LAYER: InMemoryChannelBackend(),
}

# Ensure monkeypatching
from .hacks import monkeypatch_django
monkeypatch_django()
