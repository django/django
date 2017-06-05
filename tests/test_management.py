from __future__ import unicode_literals

import logging

from asgiref.inmemory import ChannelLayer
from django.core.management import CommandError, call_command
from django.test import TestCase, mock
from six import StringIO

from channels.asgi import channel_layers, ChannelLayerWrapper
from channels.binding.base import BindingMetaclass
from channels.handler import ViewConsumer
from channels.management.commands import runserver
from channels.staticfiles import StaticFilesConsumer


class FakeChannelLayer(ChannelLayer):
    '''
    Dummy class to bypass the 'inmemory' string check.
    '''
    pass


@mock.patch('channels.management.commands.runworker.Worker')
class RunWorkerTests(TestCase):

    def setUp(self):
        import channels.log
        self.stream = StringIO()
        channels.log.handler = logging.StreamHandler(self.stream)
        BindingMetaclass.binding_classes = []
        self._old_layer = channel_layers.set(
            'fake_channel',
            ChannelLayerWrapper(
                FakeChannelLayer(),
                'fake_channel',
                channel_layers['fake_channel'].routing[:],
            )
        )

    def tearDown(self):
        channel_layers.set('fake_channel', self._old_layer)

    def test_runworker_no_local_only(self, mock_worker):
        """
        Runworker should fail with the default "inmemory" worker.
        """
        with self.assertRaises(CommandError):
            call_command('runworker')

    def test_debug(self, mock_worker):
        """
        Test that the StaticFilesConsumer is used in debug mode.
        """
        with self.settings(
            DEBUG=True,
            STATIC_URL='/static/',
            INSTALLED_APPS=['channels', 'django.contrib.staticfiles'],
        ):
            # Use 'fake_channel' that bypasses the 'inmemory' check
            call_command('runworker', '--layer', 'fake_channel')
            mock_worker.assert_called_with(
                only_channels=None,
                exclude_channels=None,
                callback=None,
                channel_layer=mock.ANY,
            )

            channel_layer = mock_worker.call_args[1]['channel_layer']
            static_consumer = channel_layer.router.root.routing[0].consumer
            self.assertIsInstance(static_consumer, StaticFilesConsumer)

    def test_debug_without_staticfiles(self, mock_worker):
        """
        Test that the StaticFilesConsumer is not used in debug mode when staticfiles app is not configured.
        """
        with self.settings(DEBUG=True, STATIC_URL=None, INSTALLED_APPS=['channels']):
            # Use 'fake_channel' that bypasses the 'inmemory' check
            call_command('runworker', '--layer', 'fake_channel')
            mock_worker.assert_called_with(
                only_channels=None,
                exclude_channels=None,
                callback=None,
                channel_layer=mock.ANY,
            )

            channel_layer = mock_worker.call_args[1]['channel_layer']
            static_consumer = channel_layer.router.root.routing[0].consumer
            self.assertNotIsInstance(static_consumer, StaticFilesConsumer)
            self.assertIsInstance(static_consumer, ViewConsumer)

    def test_runworker(self, mock_worker):
        # Use 'fake_channel' that bypasses the 'inmemory' check
        call_command('runworker', '--layer', 'fake_channel')
        mock_worker.assert_called_with(
            callback=None,
            only_channels=None,
            channel_layer=mock.ANY,
            exclude_channels=None,
        )

    def test_runworker_verbose(self, mocked_worker):
        # Use 'fake_channel' that bypasses the 'inmemory' check
        call_command('runworker', '--layer', 'fake_channel', '--verbosity', '2')

        # Verify the callback is set
        mocked_worker.assert_called_with(
            callback=mock.ANY,
            only_channels=None,
            channel_layer=mock.ANY,
            exclude_channels=None,
        )


class RunServerTests(TestCase):

    def setUp(self):
        import channels.log
        self.stream = StringIO()
        # Capture the logging of the channels moduel to match against the
        # output.
        channels.log.handler = logging.StreamHandler(self.stream)

    @mock.patch('channels.management.commands.runserver.sys.stdout', new_callable=StringIO)
    @mock.patch('channels.management.commands.runserver.Server')
    @mock.patch('channels.management.commands.runworker.Worker')
    def test_runserver_basic(self, mocked_worker, mocked_server, mock_stdout):
        # Django's autoreload util uses threads and this is not needed
        # in the test environment.
        # See:
        # https://github.com/django/django/blob/master/django/core/management/commands/runserver.py#L105
        call_command('runserver', '--noreload')
        mocked_server.assert_called_with(
            endpoints=['tcp:port=8000:interface=127.0.0.1'],
            signal_handlers=True,
            http_timeout=60,
            action_logger=mock.ANY,
            channel_layer=mock.ANY,
            ws_protocols=None,
            root_path='',
            websocket_handshake_timeout=5,
        )

    @mock.patch('channels.management.commands.runserver.sys.stdout', new_callable=StringIO)
    @mock.patch('channels.management.commands.runserver.Server')
    @mock.patch('channels.management.commands.runworker.Worker')
    def test_runserver_debug(self, mocked_worker, mocked_server, mock_stdout):
        """
        Test that the server runs with `DEBUG=True`.
        """
        # Debug requires the static url is set.
        with self.settings(DEBUG=True, STATIC_URL='/static/'):
            call_command('runserver', '--noreload')
            mocked_server.assert_called_with(
                endpoints=['tcp:port=8000:interface=127.0.0.1'],
                signal_handlers=True,
                http_timeout=60,
                action_logger=mock.ANY,
                channel_layer=mock.ANY,
                ws_protocols=None,
                root_path='',
                websocket_handshake_timeout=5,
            )

            call_command('runserver', '--noreload', 'localhost:8001')
            mocked_server.assert_called_with(
                endpoints=['tcp:port=8001:interface=localhost'],
                signal_handlers=True,
                http_timeout=60,
                action_logger=mock.ANY,
                channel_layer=mock.ANY,
                ws_protocols=None,
                root_path='',
                websocket_handshake_timeout=5,
            )

        self.assertFalse(
            mocked_worker.called,
            "The worker should not be called with '--noworker'",
        )

    @mock.patch('channels.management.commands.runserver.sys.stdout', new_callable=StringIO)
    @mock.patch('channels.management.commands.runserver.Server')
    @mock.patch('channels.management.commands.runworker.Worker')
    def test_runserver_noworker(self, mocked_worker, mocked_server, mock_stdout):
        '''
        Test that the Worker is not called when using the `--noworker` parameter.
        '''
        call_command('runserver', '--noreload', '--noworker')
        mocked_server.assert_called_with(
            endpoints=['tcp:port=8000:interface=127.0.0.1'],
            signal_handlers=True,
            http_timeout=60,
            action_logger=mock.ANY,
            channel_layer=mock.ANY,
            ws_protocols=None,
            root_path='',
            websocket_handshake_timeout=5,
        )
        self.assertFalse(
            mocked_worker.called,
            "The worker should not be called with '--noworker'",
        )

    @mock.patch('channels.management.commands.runserver.sys.stderr', new_callable=StringIO)
    def test_log_action(self, mocked_stderr):
        cmd = runserver.Command()
        test_actions = [
            (100, 'http', 'complete', 'HTTP GET /a-path/ 100 [0.12, a-client]'),
            (200, 'http', 'complete', 'HTTP GET /a-path/ 200 [0.12, a-client]'),
            (300, 'http', 'complete', 'HTTP GET /a-path/ 300 [0.12, a-client]'),
            (304, 'http', 'complete', 'HTTP GET /a-path/ 304 [0.12, a-client]'),
            (400, 'http', 'complete', 'HTTP GET /a-path/ 400 [0.12, a-client]'),
            (404, 'http', 'complete', 'HTTP GET /a-path/ 404 [0.12, a-client]'),
            (500, 'http', 'complete', 'HTTP GET /a-path/ 500 [0.12, a-client]'),
            (None, 'websocket', 'connected', 'WebSocket CONNECT /a-path/ [a-client]'),
            (None, 'websocket', 'disconnected', 'WebSocket DISCONNECT /a-path/ [a-client]'),
            (None, 'websocket', 'something', ''),  # This shouldn't happen
        ]

        for status_code, protocol, action, output in test_actions:
            details = {
                'status': status_code,
                'method': 'GET',
                'path': '/a-path/',
                'time_taken': 0.12345,
                'client': 'a-client',
            }
            cmd.log_action(protocol, action, details)
            self.assertIn(output, mocked_stderr.getvalue())
            # Clear previous output
            mocked_stderr.truncate(0)
