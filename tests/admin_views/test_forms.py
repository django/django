from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.models import User
from django.test import TestCase, override_settings


# To verify that the login form rejects inactive users, use an authentication
# backend that allows them.
@override_settings(AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.AllowAllUsersModelBackend'])
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
