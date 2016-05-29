from __future__ import unicode_literals

from django.test import override_settings
from channels import route_class
from channels.generic import BaseConsumer, websockets
from channels.tests import ChannelTestCase
from channels.tests import apply_routes, Client


@override_settings(SESSION_ENGINE="django.contrib.sessions.backends.cache")
class GenericTests(ChannelTestCase):

    def test_base_consumer(self):

        class Consumers(BaseConsumer):

            method_mapping = {
                'test.create': 'create',
                'test.test': 'test',
            }

            def create(self, message, **kwargs):
                self.called = 'create'

            def test(self, message, **kwargs):
                self.called = 'test'

        with apply_routes([route_class(Consumers)]):
            client = Client()

            #  check that methods for certain channels routes successfully
            self.assertEqual(client.send_and_consume('test.create').called, 'create')
            self.assertEqual(client.send_and_consume('test.test').called, 'test')

            #  send to the channels without routes
            client.send('test.wrong')
            message = self.get_next_message('test.wrong')
            self.assertEqual(client.channel_layer.router.match(message), None)

            client.send('test')
            message = self.get_next_message('test')
            self.assertEqual(client.channel_layer.router.match(message), None)

    def test_websockets_consumers_handlers(self):

        class WebsocketConsumer(websockets.WebsocketConsumer):

            def connect(self, message, **kwargs):
                self.called = 'connect'
                self.id = kwargs['id']

            def disconnect(self, message, **kwargs):
                self.called = 'disconnect'

            def receive(self, text=None, bytes=None, **kwargs):
                self.text = text

        with apply_routes([route_class(WebsocketConsumer, path='/path/(?P<id>\d+)')]):
            client = Client()

            consumer = client.send_and_consume('websocket.connect', {'path': '/path/1'})
            self.assertEqual(consumer.called, 'connect')
            self.assertEqual(consumer.id, '1')

            consumer = client.send_and_consume('websocket.receive', {'path': '/path/1', 'text': 'text'})
            self.assertEqual(consumer.text, 'text')

            consumer = client.send_and_consume('websocket.disconnect', {'path': '/path/1'})
            self.assertEqual(consumer.called, 'disconnect')

    def test_websockets_decorators(self):
        class WebsocketConsumer(websockets.WebsocketConsumer):
            slight_ordering = True

            def connect(self, message, **kwargs):
                self.order = message['order']

        with apply_routes([route_class(WebsocketConsumer, path='/path')]):
            client = Client()

            client.send('websocket.connect', {'path': '/path', 'order': 1})
            client.send('websocket.connect', {'path': '/path', 'order': 0})
            client.consume('websocket.connect')
            self.assertEqual(client.consume('websocket.connect').order, 0)
            self.assertEqual(client.consume('websocket.connect').order, 1)
