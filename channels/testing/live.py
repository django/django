from django.conf import settings
from django.db import connections
from django.test.testcases import LiveServerTestCase, LiveServerThread

from daphne.endpoints import build_endpoint_description_strings
from daphne.server import Server

from ..routing import get_default_application


class DaphneServerThread(LiveServerThread):
    """
    LiveServerThread subclass that runs Daphne
    """

    def run(self):
        """
        Sets up the live server and databases, and then loops over handling
        http requests.
        """
        if self.connections_override:
            # Override this thread's database connections with the ones
            # provided by the main thread.
            for alias, conn in self.connections_override.items():
                connections[alias] = conn
        try:
            self.daphne = self._create_server()
            self.daphne.run()
        except Exception as e:
            self.error = e
            self.is_ready.set()
        finally:
            connections.close_all()

    @property
    def port(self):
        # Dynamically fetch real listen port if we were given 0
        if self._port == 0:
            return self.daphne.listening_addresses[0][1]
        return self._port

    @port.setter
    def port(self, value):
        self._port = value

    def _create_server(self):
        endpoints = build_endpoint_description_strings(host=self.host, port=self._port)
        return Server(
            application=get_default_application(),
            endpoints=endpoints,
            signal_handlers=False,
            ws_protocols=getattr(settings, "CHANNELS_WS_PROTOCOLS", None),
            root_path=getattr(settings, "FORCE_SCRIPT_NAME", "") or "",
            ready_callable=lambda: self.is_ready.set(),
        )

    def terminate(self):
        if hasattr(self, "daphne"):
            # Stop the WSGI server
            self.daphne.stop()
        self.join()


class ChannelsLiveServerTestCase(LiveServerTestCase):

    server_thread_class = DaphneServerThread
