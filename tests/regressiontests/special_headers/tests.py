from django.test import TestCase
from django.contrib.auth.models import User

class SpecialHeadersTest(TestCase):
    fixtures = ['data.xml']

    def test_xheaders(self):
        user = User.objects.get(username='super')
        response = self.client.get('/special_headers/article/1/')
        # import pdb; pdb.set_trace()
        self.failUnless('X-Object-Type' not in response)
        self.client.login(username='super', password='secret')
        response = self.client.get('/special_headers/article/1/')
        self.failUnless('X-Object-Type' in response)
        user.is_staff = False
        user.save()
        response = self.client.get('/special_headers/article/1/')
        self.failUnless('X-Object-Type' not in response)
        user.is_staff = True
        user.is_active = False
        user.save()
        response = self.client.get('/special_headers/article/1/')
        self.failUnless('X-Object-Type' not in response)

    def test_xview(self):
        user = User.objects.get(username='super')
        response = self.client.head('/special_headers/xview/')
        self.failUnless('X-View' not in response)
        self.client.login(username='super', password='secret')
        response = self.client.head('/special_headers/xview/')
        self.failUnless('X-View' in response)
        user.is_staff = False
        user.save()
        response = self.client.head('/special_headers/xview/')
        self.failUnless('X-View' not in response)
        user.is_staff = True
        user.is_active = False
        user.save()
        response = self.client.head('/special_headers/xview/')
        self.failUnless('X-View' not in response)
