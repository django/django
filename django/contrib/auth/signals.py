from django.dispatch import Signal

user_logged_in = Signal(providing_args=['request', 'user'])
user_logged_out = Signal(providing_args=['request', 'user'])
