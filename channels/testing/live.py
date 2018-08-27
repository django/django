from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.test.testcases import TransactionTestCase
from django.test.utils import modify_settings

from channels.routing import get_default_application
from daphne.testing import DaphneProcess


class ChannelsLiveServerTestCase(TransactionTestCase):
    """
    Does basically the same as TransactionTestCase but also launches a
    live Daphne server in a separate process, so
    that the tests may use another test framework, such as Selenium,
    instead of the built-in dummy client.
    """

    host = "localhost"
    ProtocolServerProcess = DaphneProcess
    serve_static = True

    @property
    def live_server_url(self):
        return "http://%s:%s" % (self.host, self._port)

    @property
    def live_server_ws_url(self):
        return "ws://%s:%s" % (self.host, self._port)

    def _pre_setup(self):
        for connection in connections.all():
            if self._is_in_memory_db(connection):
                raise ImproperlyConfigured(
                    "ChannelLiveServerTestCase can not be used with in memory databases"
                )

        super(ChannelsLiveServerTestCase, self)._pre_setup()

        self._live_server_modified_settings = modify_settings(
            ALLOWED_HOSTS={"append": self.host}
        )
        self._live_server_modified_settings.enable()
        self._server_process = self.ProtocolServerProcess(
            self.host, get_default_application()
        )
        self._server_process.start()
        self._server_process.ready.wait()
        self._port = self._server_process.port.value

    def _post_teardown(self):
        self._server_process.terminate()
        self._server_process.join()
        self._live_server_modified_settings.disable()
        super(ChannelsLiveServerTestCase, self)._post_teardown()

    def _is_in_memory_db(self, connection):
        """
        Check if DatabaseWrapper holds in memory database.
        """
        if connection.vendor == "sqlite":
            return connection.is_in_memory_db()
