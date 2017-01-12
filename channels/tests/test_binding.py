from __future__ import unicode_literals

from django.contrib.auth import get_user_model

from channels import route
from channels.binding.base import CREATE, DELETE, UPDATE
from channels.binding.websockets import WebsocketBinding
from channels.generic.websockets import WebsocketDemultiplexer
from channels.tests import ChannelTestCase, HttpClient, apply_routes

User = get_user_model()


class TestsBinding(ChannelTestCase):

    def test_trigger_outbound_create(self):

        class TestBinding(WebsocketBinding):
            model = User
            stream = 'test'
            fields = ['username', 'email', 'password', 'last_name']

            @classmethod
            def group_names(cls, instance):
                return ["users"]

            def has_permission(self, user, action, pk):
                return True

        client = HttpClient()
        client.join_group('users')

        user = User.objects.create(username='test', email='test@test.com')

        received = client.receive()
        self.assertTrue('payload' in received)
        self.assertTrue('action' in received['payload'])
        self.assertTrue('data' in received['payload'])
        self.assertTrue('username' in received['payload']['data'])
        self.assertTrue('email' in received['payload']['data'])
        self.assertTrue('password' in received['payload']['data'])
        self.assertTrue('last_name' in received['payload']['data'])
        self.assertTrue('model' in received['payload'])
        self.assertTrue('pk' in received['payload'])

        self.assertEqual(received['payload']['action'], 'create')
        self.assertEqual(received['payload']['model'], 'auth.user')
        self.assertEqual(received['payload']['pk'], user.pk)

        self.assertEqual(received['payload']['data']['email'], 'test@test.com')
        self.assertEqual(received['payload']['data']['username'], 'test')
        self.assertEqual(received['payload']['data']['password'], '')
        self.assertEqual(received['payload']['data']['last_name'], '')

        received = client.receive()
        self.assertIsNone(received)

    def test_trigger_outbound_create_exclude(self):
        class TestBinding(WebsocketBinding):
            model = User
            stream = 'test'
            exclude = ['first_name', 'last_name']

            @classmethod
            def group_names(cls, instance):
                return ["users_exclude"]

            def has_permission(self, user, action, pk):
                return True

        with apply_routes([route('test', TestBinding.consumer)]):
            client = HttpClient()
            client.join_group('users_exclude')

            user = User.objects.create(username='test', email='test@test.com')
            received = client.receive()

            self.assertTrue('payload' in received)
            self.assertTrue('action' in received['payload'])
            self.assertTrue('data' in received['payload'])
            self.assertTrue('username' in received['payload']['data'])
            self.assertTrue('email' in received['payload']['data'])
            self.assertTrue('password' in received['payload']['data'])
            self.assertTrue('model' in received['payload'])
            self.assertTrue('pk' in received['payload'])

            self.assertFalse('last_name' in received['payload']['data'])
            self.assertFalse('first_name' in received['payload']['data'])

            self.assertEqual(received['payload']['action'], 'create')
            self.assertEqual(received['payload']['model'], 'auth.user')
            self.assertEqual(received['payload']['pk'], user.pk)

            self.assertEqual(received['payload']['data']['email'], 'test@test.com')
            self.assertEqual(received['payload']['data']['username'], 'test')
            self.assertEqual(received['payload']['data']['password'], '')

            received = client.receive()
            self.assertIsNone(received)

    def test_omit_fields_and_exclude(self):
        def _declare_class():
            class TestBinding(WebsocketBinding):
                model = User
                stream = 'test'

                @classmethod
                def group_names(cls, instance):
                    return ["users_omit"]

                def has_permission(self, user, action, pk):
                    return True
        self.assertRaises(ValueError, _declare_class)

    def test_trigger_outbound_update(self):
        class TestBinding(WebsocketBinding):
            model = User
            stream = 'test'
            fields = ['__all__']

            @classmethod
            def group_names(cls, instance):
                return ["users2"]

            def has_permission(self, user, action, pk):
                return True

        # Make model and clear out pending sends
        user = User.objects.create(username='test', email='test@test.com')

        client = HttpClient()
        client.join_group('users2')

        user.username = 'test_new'
        user.save()

        received = client.receive()
        self.assertTrue('payload' in received)
        self.assertTrue('action' in received['payload'])
        self.assertTrue('data' in received['payload'])
        self.assertTrue('username' in received['payload']['data'])
        self.assertTrue('email' in received['payload']['data'])
        self.assertTrue('password' in received['payload']['data'])
        self.assertTrue('last_name' in received['payload']['data'])
        self.assertTrue('model' in received['payload'])
        self.assertTrue('pk' in received['payload'])

        self.assertEqual(received['payload']['action'], 'update')
        self.assertEqual(received['payload']['model'], 'auth.user')
        self.assertEqual(received['payload']['pk'], user.pk)

        self.assertEqual(received['payload']['data']['email'], 'test@test.com')
        self.assertEqual(received['payload']['data']['username'], 'test_new')
        self.assertEqual(received['payload']['data']['password'], '')
        self.assertEqual(received['payload']['data']['last_name'], '')

        received = client.receive()
        self.assertIsNone(received)

    def test_trigger_outbound_delete(self):
        class TestBinding(WebsocketBinding):
            model = User
            stream = 'test'
            fields = ['username']

            @classmethod
            def group_names(cls, instance):
                return ["users3"]

            def has_permission(self, user, action, pk):
                return True

        # Make model and clear out pending sends
        user = User.objects.create(username='test', email='test@test.com')

        client = HttpClient()
        client.join_group('users3')

        user.delete()

        received = client.receive()
        self.assertTrue('payload' in received)
        self.assertTrue('action' in received['payload'])
        self.assertTrue('data' in received['payload'])
        self.assertTrue('username' in received['payload']['data'])
        self.assertTrue('model' in received['payload'])
        self.assertTrue('pk' in received['payload'])

        self.assertEqual(received['payload']['action'], 'delete')
        self.assertEqual(received['payload']['model'], 'auth.user')
        self.assertEqual(received['payload']['pk'], 1)
        self.assertEqual(received['payload']['data']['username'], 'test')

        received = client.receive()
        self.assertIsNone(received)

    def test_inbound_create(self):
        self.assertEqual(User.objects.all().count(), 0)

        class UserBinding(WebsocketBinding):
            model = User
            stream = 'users'
            fields = ['username', 'email', 'password', 'last_name']

            @classmethod
            def group_names(cls, instance):
                return ['users_outbound']

            def has_permission(self, user, action, pk):
                return True

        class Demultiplexer(WebsocketDemultiplexer):
            consumers = {
                'users': UserBinding.consumer,
            }

            groups = ['inbound']

        with apply_routes([Demultiplexer.as_route(path='/')]):
            client = HttpClient()
            client.send_and_consume('websocket.connect', path='/')
            client.send_and_consume('websocket.receive', path='/', text={
                'stream': 'users',
                'payload': {
                    'action': CREATE,
                    'data': {'username': 'test_inbound', 'email': 'test@user_steam.com'},
                },
            })

        self.assertEqual(User.objects.all().count(), 1)
        user = User.objects.all().first()
        self.assertEqual(user.username, 'test_inbound')
        self.assertEqual(user.email, 'test@user_steam.com')

        self.assertIsNone(client.receive())

    def test_inbound_update(self):
        user = User.objects.create(username='test', email='test@channels.com')

        class UserBinding(WebsocketBinding):
            model = User
            stream = 'users'
            fields = ['username', ]

            @classmethod
            def group_names(cls, instance):
                return ['users_outbound']

            def has_permission(self, user, action, pk):
                return True

        class Demultiplexer(WebsocketDemultiplexer):
            consumers = {
                'users': UserBinding.consumer,
            }

            groups = ['inbound']

        with apply_routes([Demultiplexer.as_route(path='/')]):
            client = HttpClient()
            client.send_and_consume('websocket.connect', path='/')
            client.send_and_consume('websocket.receive', path='/', text={
                'stream': 'users',
                'payload': {'action': UPDATE, 'pk': user.pk, 'data': {'username': 'test_inbound'}}
            })

            user = User.objects.get(pk=user.pk)
            self.assertEqual(user.username, 'test_inbound')
            self.assertEqual(user.email, 'test@channels.com')

            # trying change field that not in binding fields
            client.send_and_consume('websocket.receive', path='/', text={
                'stream': 'users',
                'payload': {'action': UPDATE, 'pk': user.pk, 'data': {'email': 'new@test.com'}}
            })

            user = User.objects.get(pk=user.pk)
            self.assertEqual(user.username, 'test_inbound')
            self.assertEqual(user.email, 'test@channels.com')

            self.assertIsNone(client.receive())

    def test_inbound_delete(self):
        user = User.objects.create(username='test', email='test@channels.com')

        class UserBinding(WebsocketBinding):
            model = User
            stream = 'users'
            fields = ['username', ]

            @classmethod
            def group_names(cls, instance):
                return ['users_outbound']

            def has_permission(self, user, action, pk):
                return True

        class Demultiplexer(WebsocketDemultiplexer):
            consumers = {
                'users': UserBinding.consumer,
            }

            groups = ['inbound']

        with apply_routes([Demultiplexer.as_route(path='/')]):
            client = HttpClient()
            client.send_and_consume('websocket.connect', path='/')
            client.send_and_consume('websocket.receive', path='/', text={
                'stream': 'users',
                'payload': {'action': DELETE, 'pk': user.pk}
            })

        self.assertIsNone(User.objects.filter(pk=user.pk).first())
        self.assertIsNone(client.receive())
