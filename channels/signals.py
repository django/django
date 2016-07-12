from django.db import close_old_connections
from django.dispatch import Signal


consumer_started = Signal(providing_args=["environ"])
consumer_finished = Signal()

# Connect connection closer to consumer finished as well
consumer_finished.connect(close_old_connections)
