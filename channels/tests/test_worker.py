from __future__ import unicode_literals

try:
    from unittest import mock
except ImportError:
    import mock
import threading

from channels import Channel, route, DEFAULT_CHANNEL_LAYER
from channels.asgi import channel_layers
from channels.tests import ChannelTestCase
from channels.worker import Worker, WorkerGroup
from channels.exceptions import ConsumeLater
from channels.signals import worker_ready


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
    """
    Test threaded workers.
    """

    def setUp(self):
        self.channel_layer = channel_layers[DEFAULT_CHANNEL_LAYER]
        self.worker = WorkerGroup(self.channel_layer, n_threads=4)
        self.subworkers = self.worker.workers

    def test_subworkers_created(self):
        self.assertEqual(len(self.subworkers), 3)

    def test_subworkers_no_sigterm(self):
        for wrk in self.subworkers:
            self.assertFalse(wrk.signal_handlers)

    def test_ready_signals_sent(self):
        self.in_signal = 0

        def handle_signal(sender, *args, **kwargs):
            self.in_signal += 1

        worker_ready.connect(handle_signal)
        WorkerGroup(self.channel_layer, n_threads=4)
        self.worker.ready()
        self.assertEqual(self.in_signal, 4)

    def test_sigterm_handler(self):
        threads = []
        for wkr in self.subworkers:
            t = threading.Thread(target=wkr.run)
            t.start()
            threads.append(t)
        self.worker.sigterm_handler(None, None)
        for t in threads:
            t.join()
