from django.contrib.messages.api import get_messages
from django.contrib.messages.constants import DEFAULT_LEVELS


def messages(request):
    """
    Return a lazy 'messages' context variable as well as
    'DEFAULT_MESSAGE_LEVELS'.
    """
    return {
        "messages": get_messages(request),
        "DEFAULT_MESSAGE_LEVELS": DEFAULT_LEVELS,
    }
