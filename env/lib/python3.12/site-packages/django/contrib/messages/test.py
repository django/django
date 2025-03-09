from .api import get_messages


class MessagesTestMixin:
    def assertMessages(self, response, expected_messages, *, ordered=True):
        request_messages = list(get_messages(response.wsgi_request))
        assertion = self.assertEqual if ordered else self.assertCountEqual
        assertion(request_messages, expected_messages)
