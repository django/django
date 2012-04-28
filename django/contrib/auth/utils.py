from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import base36_to_int

def confirm_password_reset(uidb36, token, token_generator=default_token_generator):
    try:
        uid_int = base36_to_int(uidb36)
        user = User.objects.get(id=uid_int)
    except (ValueError, User.DoesNotExist):
        user = None

    return user, token_generator.check_token(user, token) if user else False

