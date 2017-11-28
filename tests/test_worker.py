from __future__ import unicode_literals

import time
import threading

from channels import DEFAULT_CHANNEL_LAYER, Channel, route
from channels.asgi import channel_layers
from channels.exceptions import ConsumeLater
from channels.test import ChannelTestCase
from channels.worker import Worker, WorkerGroup

try:
    from unittest import mock
except ImportError:
    import mock


class PatchedWorker(Worker):
    """Worker with specific numbers of loops"""
    def get_termed(self):
        if not self.__iters:
            return True
        self.__iters -= 1
        return False

    def set_termed(self, value):
        self.__iters = value

    termed = property(get_termed, set_termed)


class WorkerTests(ChannelTestCase):
    """
    Tests that the router's routing code works correctly.
    """

    def test_channel_filters(self):
        """
        Tests that the include/exclude logic works
        """
        # Include
        worker = Worker(None, only_channels=["yes.*", "maybe.*"])
        self.assertEqual(
            worker.apply_channel_filters(["yes.1", "no.1"]),
            ["yes.1"],
        )
        self.assertEqual(
            worker.apply_channel_filters(["yes.1", "no.1", "maybe.2", "yes"]),
            ["yes.1", "maybe.2"],
        )
        # Exclude
        worker = Worker(None, exclude_channels=["no.*", "maybe.*"])
        self.assertEqual(
            worker.apply_channel_filters(["yes.1", "no.1", "maybe.2", "yes"]),
            ["yes.1", "yes"],
        )
        # Both
        worker = Worker(None, exclude_channels=["no.*"], only_channels=["yes.*"])
        self.assertEqual(
            worker.apply_channel_filters(["yes.1", "no.1", "maybe.2", "yes"]),
            ["yes.1"],
        )

    def test_run_with_consume_later_error(self):

        # consumer with ConsumeLater error at first call
        def _consumer(message, **kwargs):
            _consumer._call_count = getattr(_consumer, '_call_count', 0) + 1
            if _consumer._call_count == 1:
                raise ConsumeLater()

        Channel('test').send({'test': 'test'}, immediately=True)
        channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
        channel_layer.router.add_route(route('test', _consumer))
        old_send = channel_layer.send
        channel_layer.send = mock.Mock(side_effect=old_send)  # proxy 'send' for counting

        worker = PatchedWorker(channel_layer)
        worker.termed = 2  # first loop with error, second with sending

        worker.run()
        self.assertEqual(getattr(_consumer, '_call_count', None), 2)
        self.assertEqual(channel_layer.send.call_count, 1)

    def test_normal_run(self):
        consumer = mock.Mock()
        Channel('test').send({'test': 'test'}, immediately=True)
        channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
        channel_layer.router.add_route(route('test', consumer))
        old_send = channel_layer.send
        channel_layer.send = mock.Mock(side_effect=old_send)  # proxy 'send' for counting

        worker = PatchedWorker(channel_layer)
        worker.termed = 2

        worker.run()
        self.assertEqual(consumer.call_count, 1)
        self.assertEqual(channel_layer.send.call_count, 0)


class WorkerGroupTests(ChannelTestCase):

    def test_graceful_stop(self):

        callback_is_running = threading.Event()

        def callback(channel, message):
            callback_is_running.set()
            # emulate some delay to validate graceful stop
            time.sleep(0.1)
            callback_is_running.clear()

        consumer = mock.Mock()
        Channel('test').send({'test': 'test'}, immediately=True)
        channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
        channel_layer.router.add_route(route('test', consumer))
        old_send = channel_layer.send
        channel_layer.send = mock.Mock(side_effect=old_send)  # proxy 'send' for counting
        worker_group = WorkerGroup(channel_layer, n_threads=3,
                                   signal_handlers=False, stop_gracefully=True,
                                   callback=callback)
        worker_group_t = threading.Thread(target=worker_group.run)
        worker_group_t.daemon = True
        worker_group_t.start()
        # wait when a worker starts the callback and terminate the worker group
        callback_is_running.wait()
        self.assertRaises(SystemExit, worker_group.sigterm_handler, None, None)
        self.assertFalse(callback_is_running.is_set())

        self.assertEqual(consumer.call_count, 1)
        self.assertEqual(channel_layer.send.call_count, 0)
