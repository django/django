import os
import re
import urllib

from django.conf import settings
from django.contrib.auth import SESSION_KEY, REDIRECT_FIELD_NAME
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.models import Site, RequestSite
from django.contrib.auth.models import User
from django.test import TestCase
from django.core import mail
from django.core.urlresolvers import reverse
from django.http import QueryDict

class AuthViewsTestCase(TestCase):
    """
    Helper base class for all the follow test cases.
    """
    fixtures = ['authtestdata.json']
    urls = 'django.contrib.auth.tests.urls'

    def setUp(self):
        self.old_LANGUAGES = settings.LANGUAGES
        self.old_LANGUAGE_CODE = settings.LANGUAGE_CODE
        settings.LANGUAGES = (('en', 'English'),)
        settings.LANGUAGE_CODE = 'en'
        self.old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        settings.TEMPLATE_DIRS = (
            os.path.join(os.path.dirname(__file__), 'templates'),
        )

    def tearDown(self):
        settings.LANGUAGES = self.old_LANGUAGES
        settings.LANGUAGE_CODE = self.old_LANGUAGE_CODE
        settings.TEMPLATE_DIRS = self.old_TEMPLATE_DIRS

    def login(self, password='password'):
        response = self.client.post('/login/', {
            'username': 'testclient',
            'password': password
            }
        )
        self.assertEquals(response.status_code, 302)
        self.assert_(response['Location'].endswith(settings.LOGIN_REDIRECT_URL))
        self.assert_(SESSION_KEY in self.client.session)

class PasswordResetTest(AuthViewsTestCase):

    def test_email_not_found(self):
        "Error is raised if the provided email address isn't currently registered"
        response = self.client.get('/password_reset/')
        self.assertEquals(response.status_code, 200)
        response = self.client.post('/password_reset/', {'email': 'not_a_real_email@email.com'})
        self.assertContains(response, "That e-mail address doesn&#39;t have an associated user account")
        self.assertEquals(len(mail.outbox), 0)

    def test_email_found(self):
        "Email is sent if a valid email address is provided for password reset"
        response = self.client.post('/password_reset/', {'email': 'staffmember@example.com'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)
        self.assert_("http://" in mail.outbox[0].body)
        self.assertEquals(settings.DEFAULT_FROM_EMAIL, mail.outbox[0].from_email)

    def test_email_found_custom_from(self):
        "Email is sent if a valid email address is provided for password reset when a custom from_email is provided."
        response = self.client.post('/password_reset_from_email/', {'email': 'staffmember@example.com'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)
        self.assertEquals("staffmember@example.com", mail.outbox[0].from_email)

    def _test_confirm_start(self):
        # Start by creating the email
        response = self.client.post('/password_reset/', {'email': 'staffmember@example.com'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(len(mail.outbox), 1)
        return self._read_signup_email(mail.outbox[0])

    def _read_signup_email(self, email):
        urlmatch = re.search(r"https?://[^/]*(/.*reset/\S*)", email.body)
        self.assert_(urlmatch is not None, "No URL found in sent email")
        return urlmatch.group(), urlmatch.groups()[0]

    def test_confirm_valid(self):
        url, path = self._test_confirm_start()
        response = self.client.get(path)
        # redirect to a 'complete' page:
        self.assertEquals(response.status_code, 200)
        self.assert_("Please enter your new password" in response.content)

    def test_confirm_invalid(self):
        url, path = self._test_confirm_start()
        # Let's munge the token in the path, but keep the same length,
        # in case the URLconf will reject a different length.
        path = path[:-5] + ("0"*4) + path[-1]

        response = self.client.get(path)
        self.assertEquals(response.status_code, 200)
        self.assert_("The password reset link was invalid" in response.content)

    def test_confirm_invalid_user(self):
        # Ensure that we get a 200 response for a non-existant user, not a 404
        response = self.client.get('/reset/123456-1-1/')
        self.assertEquals(response.status_code, 200)
        self.assert_("The password reset link was invalid" in response.content)

    def test_confirm_overflow_user(self):
        # Ensure that we get a 200 response for a base36 user id that overflows int
        response = self.client.get('/reset/zzzzzzzzzzzzz-1-1/')
        self.assertEquals(response.status_code, 200)
        self.assert_("The password reset link was invalid" in response.content)

    def test_confirm_invalid_post(self):
        # Same as test_confirm_invalid, but trying
        # to do a POST instead.
        url, path = self._test_confirm_start()
        path = path[:-5] + ("0"*4) + path[-1]

        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2':' anewpassword'})
        # Check the password has not been changed
        u = User.objects.get(email='staffmember@example.com')
        self.assert_(not u.check_password("anewpassword"))

    def test_confirm_complete(self):
        url, path = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2': 'anewpassword'})
        # It redirects us to a 'complete' page:
        self.assertEquals(response.status_code, 302)
        # Check the password has been changed
        u = User.objects.get(email='staffmember@example.com')
        self.assert_(u.check_password("anewpassword"))

        # Check we can't use the link again
        response = self.client.get(path)
        self.assertEquals(response.status_code, 200)
        self.assert_("The password reset link was invalid" in response.content)

    def test_confirm_different_passwords(self):
        url, path = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2':' x'})
        self.assertEquals(response.status_code, 200)
        self.assert_("The two password fields didn&#39;t match" in response.content)

class ChangePasswordTest(AuthViewsTestCase):

    def fail_login(self, password='password'):
        response = self.client.post('/login/', {
            'username': 'testclient',
            'password': password
            }
        )
        self.assertEquals(response.status_code, 200)
        self.assert_("Please enter a correct username and password. Note that both fields are case-sensitive." in response.content)

    def logout(self):
        response = self.client.get('/logout/')

    def test_password_change_fails_with_invalid_old_password(self):
        self.login()
        response = self.client.post('/password_change/', {
            'old_password': 'donuts',
            'new_password1': 'password1',
            'new_password2': 'password1',
            }
        )
        self.assertEquals(response.status_code, 200)
        self.assert_("Your old password was entered incorrectly. Please enter it again." in response.content)

    def test_password_change_fails_with_mismatched_passwords(self):
        self.login()
        response = self.client.post('/password_change/', {
            'old_password': 'password',
            'new_password1': 'password1',
            'new_password2': 'donuts',
            }
        )
        self.assertEquals(response.status_code, 200)
        self.assert_("The two password fields didn&#39;t match." in response.content)

    def test_password_change_succeeds(self):
        self.login()
        response = self.client.post('/password_change/', {
            'old_password': 'password',
            'new_password1': 'password1',
            'new_password2': 'password1',
            }
        )
        self.assertEquals(response.status_code, 302)
        self.assert_(response['Location'].endswith('/password_change/done/'))
        self.fail_login()
        self.login(password='password1')

class LoginTest(AuthViewsTestCase):

    def test_current_site_in_context_after_login(self):
        response = self.client.get(reverse('django.contrib.auth.views.login'))
        self.assertEquals(response.status_code, 200)
        if Site._meta.installed:
            site = Site.objects.get_current()
            self.assertEquals(response.context['site'], site)
            self.assertEquals(response.context['site_name'], site.name)
        else:
            self.assertIsInstance(response.context['site'], RequestSite)
        self.assert_(isinstance(response.context['form'], AuthenticationForm), 
                     'Login form is not an AuthenticationForm')

    def test_security_check(self, password='password'):
        login_url = reverse('django.contrib.auth.views.login')

        # Those URLs should not pass the security check
        for bad_url in ('http://example.com',
                        'https://example.com',
                        'ftp://exampel.com',
                        '//example.com'):

            nasty_url = '%(url)s?%(next)s=%(bad_url)s' % {
                'url': login_url,
                'next': REDIRECT_FIELD_NAME,
                'bad_url': urllib.quote(bad_url)
            }
            response = self.client.post(nasty_url, {
                'username': 'testclient',
                'password': password,
                }
            )
            self.assertEquals(response.status_code, 302)
            self.assertFalse(bad_url in response['Location'],
                             "%s should be blocked" % bad_url)

        # These URLs *should* still pass the security check
        for good_url in ('/view/?param=http://example.com',
                         '/view/?param=https://example.com',
                         '/view?param=ftp://exampel.com',
                         'view/?param=//example.com',
                         'https:///',
                         '//testserver/',
                         '/url%20with%20spaces/', # see ticket #12534
                         ):
            safe_url = '%(url)s?%(next)s=%(good_url)s' % {
                'url': login_url,
                'next': REDIRECT_FIELD_NAME,
                'good_url': urllib.quote(good_url)
            }
            response = self.client.post(safe_url, {
                    'username': 'testclient',
                    'password': password,
                }
            )
            self.assertEquals(response.status_code, 302)
            self.assertTrue(good_url in response['Location'],
                            "%s should be allowed" % good_url)


class LoginURLSettings(AuthViewsTestCase):
    urls = 'django.contrib.auth.tests.urls'
    
    def setUp(self):
        super(LoginURLSettings, self).setUp()
        self.old_LOGIN_URL = settings.LOGIN_URL

    def tearDown(self):
        super(LoginURLSettings, self).tearDown()
        settings.LOGIN_URL = self.old_LOGIN_URL

    def get_login_required_url(self, login_url):
        settings.LOGIN_URL = login_url
        response = self.client.get('/login_required/')
        self.assertEquals(response.status_code, 302)
        return response['Location']

    def test_standard_login_url(self):
        login_url = '/login/'
        login_required_url = self.get_login_required_url(login_url)
        querystring = QueryDict('', mutable=True)
        querystring['next'] = '/login_required/'
        self.assertEqual(login_required_url,
             'http://testserver%s?%s' % (login_url, querystring.urlencode('/')))

    def test_remote_login_url(self):
        login_url = 'http://remote.example.com/login'
        login_required_url = self.get_login_required_url(login_url)
        querystring = QueryDict('', mutable=True)
        querystring['next'] = 'http://testserver/login_required/'
        self.assertEqual(login_required_url,
                         '%s?%s' % (login_url, querystring.urlencode('/')))

    def test_https_login_url(self):
        login_url = 'https:///login/'
        login_required_url = self.get_login_required_url(login_url)
        querystring = QueryDict('', mutable=True)
        querystring['next'] = 'http://testserver/login_required/'
        self.assertEqual(login_required_url,
                         '%s?%s' % (login_url, querystring.urlencode('/')))

    def test_login_url_with_querystring(self):
        login_url = '/login/?pretty=1'
        login_required_url = self.get_login_required_url(login_url)
        querystring = QueryDict('pretty=1', mutable=True)
        querystring['next'] = '/login_required/'
        self.assertEqual(login_required_url, 'http://testserver/login/?%s' %
                         querystring.urlencode('/'))

    def test_remote_login_url_with_next_querystring(self):
        login_url = 'http://remote.example.com/login/'
        login_required_url = self.get_login_required_url('%s?next=/default/' %
                                                         login_url)
        querystring = QueryDict('', mutable=True)
        querystring['next'] = 'http://testserver/login_required/'
        self.assertEqual(login_required_url, '%s?%s' % (login_url,
                                                    querystring.urlencode('/')))


class LogoutTest(AuthViewsTestCase):
    urls = 'django.contrib.auth.tests.urls'

    def confirm_logged_out(self):
        self.assert_(SESSION_KEY not in self.client.session)

    def test_logout_default(self):
        "Logout without next_page option renders the default template"
        self.login()
        response = self.client.get('/logout/')
        self.assertEquals(200, response.status_code)
        self.assert_('Logged out' in response.content)
        self.confirm_logged_out()

    def test_14377(self):
        # Bug 14377
        self.login()
        response = self.client.get('/logout/')
        self.assertTrue('site' in response.context)

    def test_logout_with_overridden_redirect_url(self):
        # Bug 11223
        self.login()
        response = self.client.get('/logout/next_page/')
        self.assertEqual(response.status_code, 302)
        self.assert_(response['Location'].endswith('/somewhere/'))

        response = self.client.get('/logout/next_page/?next=/login/')
        self.assertEqual(response.status_code, 302)
        self.assert_(response['Location'].endswith('/login/'))

        self.confirm_logged_out()

    def test_logout_with_next_page_specified(self): 
        "Logout with next_page option given redirects to specified resource"
        self.login()
        response = self.client.get('/logout/next_page/')
        self.assertEqual(response.status_code, 302)
        self.assert_(response['Location'].endswith('/somewhere/'))
        self.confirm_logged_out()

    def test_logout_with_redirect_argument(self):
        "Logout with query string redirects to specified resource"
        self.login()
        response = self.client.get('/logout/?next=/login/')
        self.assertEqual(response.status_code, 302)
        self.assert_(response['Location'].endswith('/login/'))
        self.confirm_logged_out()

    def test_logout_with_custom_redirect_argument(self):
        "Logout with custom query string redirects to specified resource"
        self.login()
        response = self.client.get('/logout/custom_query/?follow=/somewhere/')
        self.assertEqual(response.status_code, 302)
        self.assert_(response['Location'].endswith('/somewhere/'))
        self.confirm_logged_out()

    def test_security_check(self, password='password'):
        logout_url = reverse('django.contrib.auth.views.logout')

        # Those URLs should not pass the security check
        for bad_url in ('http://example.com',
                        'https://example.com',
                        'ftp://exampel.com',
                        '//example.com'
                        ):
            nasty_url = '%(url)s?%(next)s=%(bad_url)s' % {
                'url': logout_url,
                'next': REDIRECT_FIELD_NAME,
                'bad_url': urllib.quote(bad_url)
            }
            self.login()
            response = self.client.get(nasty_url)
            self.assertEquals(response.status_code, 302)
            self.assertFalse(bad_url in response['Location'],
                             "%s should be blocked" % bad_url)
            self.confirm_logged_out()

        # These URLs *should* still pass the security check
        for good_url in ('/view/?param=http://example.com',
                         '/view/?param=https://example.com',
                         '/view?param=ftp://exampel.com',
                         'view/?param=//example.com',
                         'https:///',
                         '//testserver/',
                         '/url%20with%20spaces/', # see ticket #12534
                         ):
            safe_url = '%(url)s?%(next)s=%(good_url)s' % {
                'url': logout_url,
                'next': REDIRECT_FIELD_NAME,
                'good_url': urllib.quote(good_url)
            }
            self.login()
            response = self.client.get(safe_url)
            self.assertEquals(response.status_code, 302)
            self.assertTrue(good_url in response['Location'],
                            "%s should be allowed" % good_url)
            self.confirm_logged_out()
