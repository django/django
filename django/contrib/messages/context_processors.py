from django.contrib.messages.api import get_messages
from django.contrib.messages.constants import DEFAULT_LEVELS


def messages(request):
    """
    Returns a lazy 'messages' context variable.
    """
    return {
        'messages': get_messages(request),
        'DEFAULT_MESSAGE_LEVELS': DEFAULT_LEVELS,
    }
