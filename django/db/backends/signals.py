from django.dispatch import Signal

connection_created = Signal(providing_args=["connection"])
