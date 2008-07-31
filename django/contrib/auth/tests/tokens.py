TOKEN_GENERATOR_TESTS = """
>>> from django.contrib.auth.models import User, AnonymousUser
>>> from django.contrib.auth.tokens import PasswordResetTokenGenerator
>>> from django.conf import settings
>>> u = User.objects.create_user('tokentestuser', 'test2@example.com', 'testpw')
>>> p0 = PasswordResetTokenGenerator()
>>> tk1 = p0.make_token(u)
>>> p0.check_token(u, tk1)
True

Tests to ensure we can use the token after n days, but no greater.
Use a mocked version of PasswordResetTokenGenerator so we can change
the value of 'today'

>>> class Mocked(PasswordResetTokenGenerator):
...     def __init__(self, today):
...         self._today_val = today
...     def _today(self):
...         return self._today_val

>>> from datetime import date, timedelta
>>> p1 = Mocked(date.today() + timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS))
>>> p1.check_token(u, tk1)
True
>>> p2 = Mocked(date.today() + timedelta(settings.PASSWORD_RESET_TIMEOUT_DAYS + 1))
>>> p2.check_token(u, tk1)
False

"""
