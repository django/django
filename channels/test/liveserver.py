import multiprocessing

import django
from daphne.server import Server
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.utils import load_backend
from django.test.testcases import TransactionTestCase
from django.test.utils import modify_settings, override_settings
from twisted.internet import reactor

from .. import DEFAULT_CHANNEL_LAYER
from ..asgi import ChannelLayerManager
from ..staticfiles import StaticFilesConsumer
from ..worker import Worker, WorkerGroup

# NOTE: We use ChannelLayerManager to prevent layer instance sharing
# between forked process.  Some layers implementations create
# connections inside the __init__ method.  After forking child
# processes can lose the ability to use this connection and typically
# stuck on some network operation.  To prevent this we use new
# ChannelLayerManager each time we want to initiate default layer.
# This gives us guaranty that new layer instance will be created and
# new connection will be established.


class ProcessSetup(multiprocessing.Process):
    """Common initialization steps for test subprocess."""

    def common_setup(self):

        self.setup_django()
        self.setup_databases()
        self.override_settings()

    def setup_django(self):

        if django.VERSION >= (1, 10):
            django.setup(set_prefix=False)
        else:
            django.setup()

    def setup_databases(self):

        for alias, db in self.databases.items():
            backend = load_backend(db['ENGINE'])
            conn = backend.DatabaseWrapper(db, alias)
            if django.VERSION >= (1, 9):
                connections[alias].creation.set_as_test_mirror(
                    conn.settings_dict,
                )
            else:
                test_db_name = conn.settings_dict['NAME']
                connections[alias].settings_dict['NAME'] = test_db_name

    def override_settings(self):

        if self.overridden_settings:
            overridden = override_settings(**self.overridden_settings)
            overridden.enable()

        if self.modified_settings:
            modified = modify_settings(self.modified_settings)
            modified.enable()


class WorkerProcess(ProcessSetup):

    def __init__(self, is_ready, n_threads, overridden_settings,
                 modified_settings, databases, serve_static):

        self.is_ready = is_ready
        self.n_threads = n_threads
        self.overridden_settings = overridden_settings
        self.modified_settings = modified_settings
        self.databases = databases
        self.serve_static = serve_static
        super(WorkerProcess, self).__init__()
        self.daemon = True

    def run(self):

        try:
            self.common_setup()
            channel_layers = ChannelLayerManager()
            channel_layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)
            if self.serve_static and apps.is_installed('django.contrib.staticfiles'):
                channel_layer.router.check_default(http_consumer=StaticFilesConsumer())
            else:
                channel_layer.router.check_default()
            if self.n_threads == 1:
                self.worker = Worker(
                    channel_layer=channel_layer,
                    signal_handlers=False,
                )
            else:
                self.worker = WorkerGroup(
                    channel_layer=channel_layer,
                    signal_handlers=False,
                    n_threads=self.n_threads,
                )
            self.worker.ready()
            self.is_ready.set()
            self.worker.run()
        except Exception:
            self.is_ready.set()
            raise


class DaphneProcess(ProcessSetup):

    def __init__(self, host, port_storage, is_ready, overridden_settings,
                 modified_settings, databases):

        self.host = host
        self.port_storage = port_storage
        self.is_ready = is_ready
        self.overridden_settings = overridden_settings
        self.modified_settings = modified_settings
        self.databases = databases
        super(DaphneProcess, self).__init__()
        self.daemon = True

    def run(self):

        try:
            self.common_setup()
            channel_layers = ChannelLayerManager()
            channel_layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)
            self.server = Server(
                channel_layer=channel_layer,
                endpoints=['tcp:interface=%s:port=0' % (self.host)],
                signal_handlers=False,
            )
            reactor.callLater(0.5, self.resolve_port)
            self.server.run()
        except Exception:
            self.is_ready.set()
            raise

    def resolve_port(self):

        port = self.server.listeners[0].result.getHost().port
        self.port_storage.value = port
        self.is_ready.set()


class ChannelLiveServerTestCase(TransactionTestCase):
    """
    Does basically the same as TransactionTestCase but also launches a
    live Daphne server and Channels worker in a separate process, so
    that the tests may use another test framework, such as Selenium,
    instead of the built-in dummy client.
    """

    host = 'localhost'
    ProtocolServerProcess = DaphneProcess
    WorkerProcess = WorkerProcess
    worker_threads = 1
    serve_static = True

    @property
    def live_server_url(self):

        return 'http://%s:%s' % (self.host, self._port_storage.value)

    @property
    def live_server_ws_url(self):

        return 'ws://%s:%s' % (self.host, self._port_storage.value)

    def _pre_setup(self):

        for connection in connections.all():
            if self._is_in_memory_db(connection):
                raise ImproperlyConfigured(
                    'ChannelLiveServerTestCase can not be used with in memory databases'
                )

        channel_layers = ChannelLayerManager()
        if len(channel_layers.configs) > 1:
            raise ImproperlyConfigured(
                'ChannelLiveServerTestCase does not support multiple CHANNEL_LAYERS at this time'
            )

        channel_layer = channel_layers.make_test_backend(DEFAULT_CHANNEL_LAYER)
        if 'flush' in channel_layer.extensions:
            channel_layer.flush()

        super(ChannelLiveServerTestCase, self)._pre_setup()

        server_ready = multiprocessing.Event()
        self._port_storage = multiprocessing.Value('i')
        self._server_process = self.ProtocolServerProcess(
            self.host,
            self._port_storage,
            server_ready,
            self._overridden_settings,
            self._modified_settings,
            connections.databases,
        )
        self._server_process.start()
        server_ready.wait()

        worker_ready = multiprocessing.Event()
        self._worker_process = self.WorkerProcess(
            worker_ready,
            self.worker_threads,
            self._overridden_settings,
            self._modified_settings,
            connections.databases,
            self.serve_static,
        )
        self._worker_process.start()
        worker_ready.wait()

    def _post_teardown(self):

        self._server_process.terminate()
        self._server_process.join()
        self._worker_process.terminate()
        self._worker_process.join()
        super(ChannelLiveServerTestCase, self)._post_teardown()

    def _is_in_memory_db(self, connection):
        """Check if DatabaseWrapper holds in memory database."""

        if connection.vendor == 'sqlite':
            if django.VERSION >= (1, 11):
                return connection.is_in_memory_db()
            else:
                return connection.is_in_memory_db(
                    connection.settings_dict['NAME'],
                )
