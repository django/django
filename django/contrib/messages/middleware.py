from django.conf import settings
from django.contrib.messages.storage import default_storage


class MessageMiddleware:
    """
    Middleware that handles temporary messages.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._messages = default_storage(request)
        response = self.get_response(request)
        return self.process_response(request, response)

    def process_response(self, request, response):
        """
        Update the storage backend (i.e., save the messages).

        Raise ValueError if not all messages could be stored and DEBUG is True.
        """
        # A higher middleware layer may return a request which does not contain
        # messages storage, so make no assumption that it will be there.
        if hasattr(request, '_messages'):
            unstored_messages = request._messages.update(response)
            if unstored_messages and settings.DEBUG:
                raise ValueError('Not all temporary messages could be stored.')
        return response
