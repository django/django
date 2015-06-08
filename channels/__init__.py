from .consumer_registry import ConsumerRegistry

# Make a site-wide registry
coreg = ConsumerRegistry()

# Load an implementation of Channel
from .backends import InMemoryChannel as Channel

# Ensure monkeypatching
from .hacks import monkeypatch_django
monkeypatch_django()
