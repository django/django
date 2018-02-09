from django.conf import settings
from django.db import connections
from django.test.testcases import LiveServerTestCase, LiveServerThread

from daphne.endpoints import build_endpoint_description_strings
from daphne.server import Server

from ..routing import get_default_application
from ..staticfiles import StaticFilesWrapper


class DaphneServerThread(LiveServerThread):
    """
    LiveServerThread subclass that runs Daphne
    """

    def __init__(self, host, application, *args, **kwargs):
        self.application = application
        super().__init__(host, None, *args, **kwargs)

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
            application=self.application,
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
    """
    Drop-in replacement for Django's LiveServerTestCase.

    In order to serve static files create a subclass with serve_static = True.
    """

    server_thread_class = DaphneServerThread
    static_wrapper = StaticFilesWrapper
    serve_static = False

    @classmethod
    def _create_server_thread(cls, connections_override):
        if cls.serve_static:
            application = cls.static_wrapper(get_default_application())
        else:
            application = get_default_application()

        return cls.server_thread_class(
            cls.host,
            application,
            connections_override=connections_override,
            port=cls.port,
        )
