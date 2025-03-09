from django.dispatch import Signal

user_logged_in = Signal()
user_login_failed = Signal()
user_logged_out = Signal()
