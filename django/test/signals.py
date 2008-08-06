from django.dispatch import Signal

template_rendered = Signal(providing_args=["template", "context"])
