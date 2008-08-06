from django.dispatch import Signal

request_started = Signal()
request_finished = Signal()
got_request_exception = Signal(providing_args=["request"])
