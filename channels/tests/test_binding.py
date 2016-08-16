from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from channels.binding.websockets import WebsocketBinding
from channels.tests import ChannelTestCase, apply_routes, HttpClient
from channels import route

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

        with apply_routes([route('test', TestBinding.consumer)]):
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

        user = User.objects.create(username='test', email='test@test.com')

        with apply_routes([route('test', TestBinding.consumer)]):
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

        user = User.objects.create(username='test', email='test@test.com')

        with apply_routes([route('test', TestBinding.consumer)]):
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
