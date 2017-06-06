from django.dispatch import Signal

pre_command = Signal(providing_args=['instance'], use_caching=True)
post_command = Signal(providing_args=['instance'], use_caching=True)
