from django.conf import settings
from django.utils.module_loading import import_string


class SecretKeySettingsBackend:
    def get_secret_key(self):
        return settings.SECRET_KEY

    def get_verification_keys(self):
        return list(settings.VERIFICATION_SECRET_KEYS)

    def check_secret_key(self):

        from django.core.checks.security.base import (
            SECRET_KEY_MIN_LENGTH, SECRET_KEY_MIN_UNIQUE_CHARACTERS, W009,
        )

        passed_check = (
            getattr(settings, 'SECRET_KEY', None) and
            len(set(settings.SECRET_KEY)) >= SECRET_KEY_MIN_UNIQUE_CHARACTERS and
            len(settings.SECRET_KEY) >= SECRET_KEY_MIN_LENGTH
        )
        return [] if passed_check else [W009]


def _get_backend():
    return import_string(settings.SECRET_KEY_BACKEND)()


def get_secret_key():
    return _get_backend().get_secret_key()


def get_verification_keys():
    return _get_backend().get_verification_keys()


def check_secret_key():
    return _get_backend().check_secret_key()
