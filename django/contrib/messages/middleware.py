from django.conf import settings
from django.contrib.messages.storage import default_storage


class MessageMiddleware(object):
    """
    Middleware that handles temporary messages.
    """

    def process_request(self, request):
        request._messages = default_storage(request)

    def process_response(self, request, response):
        """
        Updates the storage backend (i.e., saves the messages).

        If not all messages could not be stored and ``DEBUG`` is ``True``, a
        ``ValueError`` is raised.
        """
        # A higher middleware layer may return a request which does not contain
        # messages storage, so make no assumption that it will be there.
        if hasattr(request, '_messages'):
            unstored_messages = request._messages.update(response)
            if unstored_messages and settings.DEBUG:
                raise ValueError('Not all temporary messages could be stored.')
        return response
