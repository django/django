from django.http import HttpResponse
from django.conf import settings
from django.contrib import messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.messages.storage.base import Message
from django.contrib.messages.tests.urls import ContactFormViewWithMsg
from django.contrib.messages.views import MessageMixin, _MessageAPIWrapper
from django.core.urlresolvers import reverse
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from django.views.generic import View


# The CookieStorage is used because it doesn't require middleware to be installed
@override_settings(MESSAGE_STORAGE='django.contrib.messages.storage.cookie.CookieStorage')
class MessageMixinTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.middleware = MessageMiddleware()

    def get_request(self, *args, **kwargs):
        request = self.rf.get('/')
        self.middleware.process_request(request)
        return request

    def get_response(self, request, view):
        response = view(request)
        self.middleware.process_response(request, response)
        return response

    def get_request_response(self, view, *args, **kwargs):
        request = self.get_request(*args, **kwargs)
        response = self.get_response(request, view)
        return request, response

    def test_add_messages(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.add_message(messages.SUCCESS, 'test')
                return HttpResponse('OK')

        request, response = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0].message, 'test')
        self.assertEqual(msg[0].level, messages.SUCCESS)

    def test_get_messages(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.add_message(messages.SUCCESS, 'success')
                self.messages.add_message(messages.WARNING, 'warning')
                content = ','.join(m.message for m in self.messages.get_messages())
                return HttpResponse(content)

        _, response = self.get_request_response(TestView.as_view())
        self.assertEqual(response.content, b"success,warning")

    def test_get_level(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                return HttpResponse(self.messages.get_level())

        _, response = self.get_request_response(TestView.as_view())
        self.assertEqual(int(response.content), messages.INFO)  # default

    def test_set_level(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.set_level(messages.WARNING)
                self.messages.add_message(messages.SUCCESS, 'success')
                self.messages.add_message(messages.WARNING, 'warning')
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(msg, [Message(messages.WARNING, 'warning')])

    @override_settings(MESSAGE_LEVEL=messages.DEBUG)
    def test_debug(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.debug("test")
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0], Message(messages.DEBUG, 'test'))

    def test_info(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.info("test")
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0], Message(messages.INFO, 'test'))

    def test_success(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.success("test")
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0], Message(messages.SUCCESS, 'test'))

    def test_warning(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.warning("test")
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0], Message(messages.WARNING, 'test'))

    def test_error(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.error("test")
                return HttpResponse('OK')

        request, _ = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0], Message(messages.ERROR, 'test'))

    def test_invalid_attribute(self):
        class TestView(MessageMixin, View):
            def get(self, request):
                self.messages.invalid()
                return HttpResponse('OK')

        with self.assertRaises(AttributeError):
            self.get_request_response(TestView.as_view())

    def test_wrapper_available_in_dispatch(self):
        """
        Make sure that self.messages is available in dispatch() even before
        calling the parent's implementation.
        """
        class TestView(MessageMixin, View):
            def dispatch(self, request):
                self.messages.add_message(messages.SUCCESS, 'test')
                return super(TestView, self).dispatch(request)

            def get(self, request):
                return HttpResponse('OK')

        request, response = self.get_request_response(TestView.as_view())
        msg = list(request._messages)
        self.assertEqual(len(msg), 1)
        self.assertEqual(msg[0].message, 'test')
        self.assertEqual(msg[0].level, messages.SUCCESS)

    def test_API(self):
        """
        Make sure that our assumptions about messages.api are still valid.
        """
        # If this test breaks because you've added or removed something from
        # messages/api.py, you should either change _MessageAPIWrapper.API to
        # add your new function or add it to excluded_API under here.
        excluded_API = {'MessageFailure'}
        self.assertEqual(
            _MessageAPIWrapper.API | excluded_API,
            set(messages.api.__all__)
        )


class SuccessMessageMixinTests(TestCase):
    urls = 'django.contrib.messages.tests.urls'

    def test_set_messages_success(self):
        author = {'name': 'John Doe',
                  'slug': 'success-msg'}
        add_url = reverse('add_success_msg')
        req = self.client.post(add_url, author)
        self.assertIn(ContactFormViewWithMsg.success_message % author,
                      req.cookies['messages'].value)
