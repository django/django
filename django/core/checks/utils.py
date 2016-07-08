import copy

from django.conf import settings


def patch_middleware_message(error):
    if settings.MIDDLEWARE is None:
        error = copy.copy(error)
        error.msg = error.msg.replace('MIDDLEWARE', 'MIDDLEWARE_CLASSES')
    return error
