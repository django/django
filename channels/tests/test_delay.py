from __future__ import unicode_literals

import json
from datetime import timedelta

from django.utils import timezone

from channels import DEFAULT_CHANNEL_LAYER, Channel, channel_layers
from channels.delay.models import DelayedMessage
from channels.delay.worker import Worker
from channels.tests import ChannelTestCase

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

    def test_invalid_message(self):
        """
        Tests the worker won't delay an invalid message
        """
        Channel('asgi.delay').send({'test': 'value'}, immediately=True)

        worker = PatchedWorker(channel_layers[DEFAULT_CHANNEL_LAYER])
        worker.termed = 1

        worker.run()

        self.assertEqual(DelayedMessage.objects.count(), 0)

    def test_delay_message(self):
        """
        Tests the message is delayed and dispatched when due
        """
        Channel('asgi.delay').send({
            'channel': 'test',
            'delay': 1000,
            'content': {'test': 'value'}
        }, immediately=True)

        worker = PatchedWorker(channel_layers[DEFAULT_CHANNEL_LAYER])
        worker.termed = 1

        worker.run()

        self.assertEqual(DelayedMessage.objects.count(), 1)

        with mock.patch('django.utils.timezone.now', return_value=timezone.now() + timedelta(milliseconds=1001)):
            worker.termed = 1
            worker.run()

        self.assertEqual(DelayedMessage.objects.count(), 0)

        message = self.get_next_message('test', require=True)
        self.assertEqual(message.content, {'test': 'value'})


class DelayedMessageTests(ChannelTestCase):

    def _create_message(self):
        kwargs = {
            'content': json.dumps({'test': 'data'}),
            'channel_name': 'test',
            'delay': 1000 * 5
        }
        delayed_message = DelayedMessage(**kwargs)
        delayed_message.save()

        return delayed_message

    def test_is_due(self):
        message = self._create_message()

        self.assertEqual(DelayedMessage.objects.is_due().count(), 0)

        with mock.patch('django.utils.timezone.now', return_value=message.due_date + timedelta(milliseconds=1)):
            self.assertEqual(DelayedMessage.objects.is_due().count(), 1)

    def test_send(self):
        message = self._create_message()
        message.send(channel_layer=channel_layers[DEFAULT_CHANNEL_LAYER])

        self.get_next_message(message.channel_name, require=True)

        self.assertEqual(DelayedMessage.objects.count(), 0)
