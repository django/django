import sys

from django.test import TestCase
from django.core.signals import got_request_exception

class TestException(Exception):
    pass

class TestMiddleware(object):
    def process_request(self, request):
        raise TestException('Test Exception')

class MiddlewareExceptionTest(TestCase):
    def setUp(self):
        self.exceptions = []
        got_request_exception.connect(self._on_request_exception)
        self.client.handler.load_middleware()

    def tearDown(self):
        got_request_exception.disconnect(self._on_request_exception)
        self.exceptions = []

    def _on_request_exception(self, sender, request, **kwargs):
        self.exceptions.append(sys.exc_info())

    def test_process_request(self):
        self.client.handler._request_middleware.insert(0, TestMiddleware().process_request)
        try:
            response = self.client.get('/')
        except TestException, e:
            # Test client indefinitely re-raises any exceptions being raised
            # during request handling. Hence actual testing that exception was
            # properly handled is done by relying on got_request_exception
            # signal being sent.
            pass
        except Exception, e:
            self.fail("Unexpected exception: %s" % e)
        self.assertEquals(len(self.exceptions), 1)
        exception, value, tb = self.exceptions[0]
        self.assertEquals(value.args, ('Test Exception', ))
