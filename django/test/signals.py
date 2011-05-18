from django.dispatch import Signal

template_rendered = Signal(providing_args=["template", "context"])

setting_changed = Signal(providing_args=["setting", "value"])
