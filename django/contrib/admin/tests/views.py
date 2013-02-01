from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry
from django.test import TestCase
from django.test.utils import override_settings

from django.contrib.auth import SESSION_KEY


@override_settings(
    LANGUAGES=(
        ('en', 'English'),
    ),
    LANGUAGE_CODE='en',
    USE_TZ=False,
    PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',),
)
class AdminViewsTestCase(TestCase):
    """
    Helper base class for all the follow test cases.
    """
    fixtures = ['admintestdata.json']
    urls = 'django.contrib.admin.tests.urls'

    @property
    def admin(self):
        if getattr(self, '_admin', None) is None:
            try:
                setattr(self, '_admin', User.objects.get(pk=1))
            except User.DoesNotExist:
                self.fail("Fail load fixture.")
        return getattr(self, '_admin')

    def login(self, password='password'):
        response = self.client.post('/admin/', {
            'username': self.admin.username,
            'password': password,
            'this_is_the_login_form': '1',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SESSION_KEY in self.client.session)

    def logout(self):
        response = self.client.get('/admin/logout/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SESSION_KEY not in self.client.session)


class AdminAuthUserLogEntryTest(AdminViewsTestCase):

    def get_user_data(self, user):
        return {
            'username': user.username,
            'password': user.password,
            'email': user.email,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'last_login_0': user.last_login.strftime('%Y-%m-%d'),
            'last_login_1': user.last_login.strftime('%H:%M:%S'),
            'initial-last_login_0': user.last_login.strftime('%Y-%m-%d'),
            'initial-last_login_1': user.last_login.strftime('%H:%M:%S'),
            'date_joined_0': user.date_joined.strftime('%Y-%m-%d'),
            'date_joined_1': user.date_joined.strftime('%H:%M:%S'),
            'initial-date_joined_0': user.date_joined.strftime('%Y-%m-%d'),
            'initial-date_joined_1': user.date_joined.strftime('%H:%M:%S'),
            }

    def test_user_change_email(self):
        self.login()
        data = self.get_user_data(self.admin)
        data['email'] = 'new_' + data['email']
        response = self.client.post(
            '/admin/auth/user/%s/' % self.admin.pk,
            data
        )
        self.assertEqual(response.status_code, 302)
        row = LogEntry.objects.reverse()[:1].get()
        self.assertEqual(row.change_message, 'Changed email.')

    def test_user_not_change(self):
        self.login()
        response = self.client.post(
            '/admin/auth/user/%s/' % self.admin.pk,
            self.get_user_data(self.admin)
        )
        self.assertEqual(response.status_code, 302)
        row = LogEntry.objects.reverse()[:1].get()
        self.assertEqual(row.change_message, 'No fields changed.')

    def test_user_change_password(self):
        self.login()
        response = self.client.post(
            '/admin/auth/user/%s/password/' % self.admin.pk,
            {
                'password1': 'password1',
                'password2': 'password1',
            }
        )
        self.assertEqual(response.status_code, 302)
        row = LogEntry.objects.reverse()[:1].get()
        self.assertEqual(row.change_message, 'Changed password.')
        self.logout()
        self.login(password='password1')
