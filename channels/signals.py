from django.db import close_old_connections
from django.dispatch import Signal


consumer_started = Signal(providing_args=["environ"])
consumer_finished = Signal()
worker_ready = Signal()
worker_process_ready = Signal()

# Called when a message is sent directly to a channel. Not called for group
# sends or direct ASGI usage. For convenience/nicer errors only.
message_sent = Signal(providing_args=["channel", "keys"])

# Connect connection closer to consumer finished as well
consumer_finished.connect(close_old_connections)
