from django.contrib.auth.models import User
from django.test import TestCase
from django.test.utils import override_settings


@override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',))
class XViewMiddlewareTest(TestCase):
    fixtures = ['data.xml']
    urls = 'admin_docs.urls'

    def test_xview_func(self):
        user = User.objects.get(username='super')
        response = self.client.head('/xview/func/')
        self.assertFalse('X-View' in response)
        self.client.login(username='super', password='secret')
        response = self.client.head('/xview/func/')
        self.assertTrue('X-View' in response)
        self.assertEqual(response['X-View'], 'admin_docs.views.xview')
        user.is_staff = False
        user.save()
        response = self.client.head('/xview/func/')
        self.assertFalse('X-View' in response)
        user.is_staff = True
        user.is_active = False
        user.save()
        response = self.client.head('/xview/func/')
        self.assertFalse('X-View' in response)

    def test_xview_class(self):
        user = User.objects.get(username='super')
        response = self.client.head('/xview/class/')
        self.assertFalse('X-View' in response)
        self.client.login(username='super', password='secret')
        response = self.client.head('/xview/class/')
        self.assertTrue('X-View' in response)
        self.assertEqual(response['X-View'], 'admin_docs.views.XViewClass')
        user.is_staff = False
        user.save()
        response = self.client.head('/xview/class/')
        self.assertFalse('X-View' in response)
        user.is_staff = True
        user.is_active = False
        user.save()
        response = self.client.head('/xview/class/')
        self.assertFalse('X-View' in response)
