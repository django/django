from .consumer_registry import ConsumerRegistry

# Make a site-wide registry
coreg = ConsumerRegistry()

# Load an implementation of Channel
from .channels.memory import Channel
