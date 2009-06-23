
# Code from django_live_server_r8458.diff @  http://code.djangoproject.com/ticket/2879#comment:41
# Editing to monkey patch django rather than be in trunk

import socket
import threading
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers import basehttp
from django.test.testcases import call_command

#from django.core.management import call_command

# support both django 1.0 and 1.1
try:
    from django.test.testcases import TransactionTestCase as TestCase
except ImportError:
    from django.test.testcases import TestCase

class StoppableWSGIServer(basehttp.WSGIServer):
    """WSGIServer with short timeout, so that server thread can stop this server."""

    def server_bind(self):
        """Sets timeout to 1 second."""
        basehttp.WSGIServer.server_bind(self)
        self.socket.settimeout(1)

    def get_request(self):
        """Checks for timeout when getting request."""
        try:
            sock, address = self.socket.accept()
            sock.settimeout(None)
            return (sock, address)
        except socket.timeout:
            raise

class TestServerThread(threading.Thread):
    """Thread for running a http server while tests are running."""

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self._stopevent = threading.Event()
        self.started = threading.Event()
        self.error = None
        super(TestServerThread, self).__init__()

    def run(self):
        """Sets up test server and database and loops over handling http requests."""
        try:
            handler = basehttp.AdminMediaHandler(WSGIHandler())
            httpd = None
            while httpd is None:
                try:
                    server_address = (self.address, self.port)
                    httpd = StoppableWSGIServer(server_address, basehttp.WSGIRequestHandler)
                except basehttp.WSGIServerException, e:
                    if "Address already in use" in str(e):
                        self.port +=1
                    else:
                        raise e
            httpd.set_app(handler)
            self.started.set()
        except basehttp.WSGIServerException, e:
            self.error = e
            self.started.set()
            return

        # Must do database stuff in this new thread if database in memory.
        from django.conf import settings
        if settings.DATABASE_ENGINE == 'sqlite3' \
            and (not settings.TEST_DATABASE_NAME or settings.TEST_DATABASE_NAME == ':memory:'):
            from django.db import connection
            db_name = connection.creation.create_test_db(0)
            # Import the fixture data into the test database.
            if hasattr(self, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                call_command('loaddata', *self.fixtures, **{'verbosity': 0})

        # Loop until we get a stop event.
        while not self._stopevent.isSet():
            httpd.handle_request()
        httpd.server_close()

    def join(self, timeout=None):
        """Stop the thread and wait for it to finish."""
        self._stopevent.set()
        threading.Thread.join(self, timeout)


def start_test_server(self, address='localhost', port=8000):
    """Creates a live test server object (instance of WSGIServer)."""
    self.server_thread = TestServerThread(address, port)
    if hasattr(self, 'fixtures'):
        print 'loading fixtures %s' % self.fixtures
        self.server_thread.__setattr__('fixtures', self.fixtures)
    self.server_thread.start()
    self.server_thread.started.wait()
    if self.server_thread.error:
        raise self.server_thread.error

def stop_test_server(self):
    if self.server_thread:
        self.server_thread.join()

## New Code

TestCase.start_test_server = classmethod(start_test_server)
TestCase.stop_test_server = classmethod(stop_test_server)

from windmill.authoring import unit

class WindmillDjangoUnitTest(TestCase, unit.WindmillUnitTestCase):
    test_port = 8000
    def setUp(self):
        self.start_test_server('localhost', self.test_port)
        self.test_url = 'http://localhost:%d' % self.server_thread.port
        unit.WindmillUnitTestCase.setUp(self)

    def tearDown(self):
        unit.WindmillUnitTestCase.tearDown(self)
        self.stop_test_server()

WindmillDjangoTransactionUnitTest = WindmillDjangoUnitTest
