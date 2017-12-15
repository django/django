from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.models import User
from django.test import TestCase


class AdminAuthenticationFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(username='inactive', password='password', is_active=False)

    def test_inactive_user(self):
        data = {
            'username': 'inactive',
            'password': 'password',
        }
        form = AdminAuthenticationForm(None, data)
        self.assertEqual(form.non_field_errors(), ['This account is inactive.'])
