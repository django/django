from django.contrib.messages import constants
from django.contrib.messages.storage import default_storage
from django.utils.functional import lazy, memoize

__all__ = (
    'add_message', 'get_messages',
    'debug', 'info', 'success', 'warning', 'error',
)


class MessageFailure(Exception):
    pass


def add_message(request, level, message, extra_tags='', fail_silently=False):
    """
    Attempts to add a message to the request using the 'messages' app, falling
    back to the user's message_set if MessageMiddleware hasn't been enabled.
    """
    if hasattr(request, '_messages'):
        return request._messages.add(level, message, extra_tags)
    if hasattr(request, 'user') and request.user.is_authenticated():
        return request.user.message_set.create(message=message)
    if not fail_silently:
        raise MessageFailure('Without the django.contrib.messages '
                                'middleware, messages can only be added to '
                                'authenticated users.')


def get_messages(request):
    """
    Returns the message storage on the request if it exists, otherwise returns
    user.message_set.all() as the old auth context processor did.
    """
    if hasattr(request, '_messages'):
        return request._messages

    def get_user():
        if hasattr(request, 'user'):
            return request.user
        else:
            from django.contrib.auth.models import AnonymousUser
            return AnonymousUser()

    return lazy(memoize(get_user().get_and_delete_messages, {}, 0), list)()


def get_level(request):
    """
    Returns the minimum level of messages to be recorded.

    The default level is the ``MESSAGE_LEVEL`` setting. If this is not found,
    the ``INFO`` level is used.
    """
    if hasattr(request, '_messages'):
        storage = request._messages
    else:
        storage = default_storage(request)
    return storage.level


def set_level(request, level):
    """
    Sets the minimum level of messages to be recorded, returning ``True`` if
    the level was recorded successfully.

    If set to ``None``, the default level will be used (see the ``get_level``
    method).
    """
    if not hasattr(request, '_messages'):
        return False
    request._messages.level = level
    return True


def debug(request, message, extra_tags='', fail_silently=False):
    """
    Adds a message with the ``DEBUG`` level.
    """
    add_message(request, constants.DEBUG, message, extra_tags=extra_tags,
                fail_silently=fail_silently)


def info(request, message, extra_tags='', fail_silently=False):
    """
    Adds a message with the ``INFO`` level.
    """
    add_message(request, constants.INFO, message, extra_tags=extra_tags,
                fail_silently=fail_silently)


def success(request, message, extra_tags='', fail_silently=False):
    """
    Adds a message with the ``SUCCESS`` level.
    """
    add_message(request, constants.SUCCESS, message, extra_tags=extra_tags,
                fail_silently=fail_silently)


def warning(request, message, extra_tags='', fail_silently=False):
    """
    Adds a message with the ``WARNING`` level.
    """
    add_message(request, constants.WARNING, message, extra_tags=extra_tags,
                fail_silently=fail_silently)


def error(request, message, extra_tags='', fail_silently=False):
    """
    Adds a message with the ``ERROR`` level.
    """
    add_message(request, constants.ERROR, message, extra_tags=extra_tags,
                fail_silently=fail_silently)
