import itertools
import os
import re
try:
    from urllib.parse import urlparse, ParseResult
except ImportError:     # Python 2
    from urlparse import urlparse, ParseResult

from django.conf import global_settings, settings
from django.contrib.sites.models import Site, RequestSite
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse, NoReverseMatch
from django.http import QueryDict, HttpRequest
from django.utils.encoding import force_text
from django.utils.http import urlquote
from django.utils._os import upath
from django.test import TestCase
from django.test.utils import override_settings, patch_logger
from django.middleware.csrf import CsrfViewMiddleware
from django.contrib.sessions.middleware import SessionMiddleware

from django.contrib.auth import SESSION_KEY, REDIRECT_FIELD_NAME
from django.contrib.auth.forms import (AuthenticationForm, PasswordChangeForm,
                SetPasswordForm)
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.contrib.auth.views import login as login_view


@override_settings(
    LANGUAGES=(
        ('en', 'English'),
    ),
    LANGUAGE_CODE='en',
    TEMPLATE_LOADERS=global_settings.TEMPLATE_LOADERS,
    TEMPLATE_DIRS=(
        os.path.join(os.path.dirname(upath(__file__)), 'templates'),
    ),
    USE_TZ=False,
    PASSWORD_HASHERS=('django.contrib.auth.hashers.SHA1PasswordHasher',),
)
class AuthViewsTestCase(TestCase):
    """
    Helper base class for all the follow test cases.
    """
    fixtures = ['authtestdata.json']
    urls = 'django.contrib.auth.tests.urls'

    def login(self, password='password'):
        response = self.client.post('/login/', {
            'username': 'testclient',
            'password': password,
            })
        self.assertTrue(SESSION_KEY in self.client.session)
        return response

    def assertFormError(self, response, error):
        """Assert that error is found in response.context['form'] errors"""
        form_errors = list(itertools.chain(*response.context['form'].errors.values()))
        self.assertIn(force_text(error), form_errors)

    def assertURLEqual(self, url, expected, parse_qs=False):
        """
        Given two URLs, make sure all their components (the ones given by
        urlparse) are equal, only comparing components that are present in both
        URLs.
        If `parse_qs` is True, then the querystrings are parsed with QueryDict.
        This is useful if you don't want the order of parameters to matter.
        Otherwise, the query strings are compared as-is.
        """
        fields = ParseResult._fields

        for attr, x, y in zip(fields, urlparse(url), urlparse(expected)):
            if parse_qs and attr == 'query':
                x, y = QueryDict(x), QueryDict(y)
            if x and y and x != y:
                self.fail("%r != %r (%s doesn't match)" % (url, expected, attr))


@skipIfCustomUser
class AuthViewNamedURLTests(AuthViewsTestCase):
    urls = 'django.contrib.auth.urls'

    def test_named_urls(self):
        "Named URLs should be reversible"
        expected_named_urls = [
            ('login', [], {}),
            ('logout', [], {}),
            ('password_change', [], {}),
            ('password_change_done', [], {}),
            ('password_reset', [], {}),
            ('password_reset_done', [], {}),
            ('password_reset_confirm', [], {
                'uidb64': 'aaaaaaa',
                'token': '1111-aaaaa',
            }),
            ('password_reset_complete', [], {}),
        ]
        for name, args, kwargs in expected_named_urls:
            try:
                reverse(name, args=args, kwargs=kwargs)
            except NoReverseMatch:
                self.fail("Reversal of url named '%s' failed with NoReverseMatch" % name)


@skipIfCustomUser
class PasswordResetTest(AuthViewsTestCase):

    def test_email_not_found(self):
        """If the provided email is not registered, don't raise any error but
        also don't send any email."""
        response = self.client.get('/password_reset/')
        self.assertEqual(response.status_code, 200)
        response = self.client.post('/password_reset/', {'email': 'not_a_real_email@email.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_found(self):
        "Email is sent if a valid email address is provided for password reset"
        response = self.client.post('/password_reset/', {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue("http://" in mail.outbox[0].body)
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, mail.outbox[0].from_email)

    def test_email_found_custom_from(self):
        "Email is sent if a valid email address is provided for password reset when a custom from_email is provided."
        response = self.client.post('/password_reset_from_email/', {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual("staffmember@example.com", mail.outbox[0].from_email)

    @override_settings(ALLOWED_HOSTS=['adminsite.com'])
    def test_admin_reset(self):
        "If the reset view is marked as being for admin, the HTTP_HOST header is used for a domain override."
        response = self.client.post('/admin_password_reset/',
            {'email': 'staffmember@example.com'},
            HTTP_HOST='adminsite.com'
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue("http://adminsite.com" in mail.outbox[0].body)
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, mail.outbox[0].from_email)

    # Skip any 500 handler action (like sending more mail...)
    @override_settings(DEBUG_PROPAGATE_EXCEPTIONS=True)
    def test_poisoned_http_host(self):
        "Poisoned HTTP_HOST headers can't be used for reset emails"
        # This attack is based on the way browsers handle URLs. The colon
        # should be used to separate the port, but if the URL contains an @,
        # the colon is interpreted as part of a username for login purposes,
        # making 'evil.com' the request domain. Since HTTP_HOST is used to
        # produce a meaningful reset URL, we need to be certain that the
        # HTTP_HOST header isn't poisoned. This is done as a check when get_host()
        # is invoked, but we check here as a practical consequence.
        with patch_logger('django.security.DisallowedHost', 'error') as logger_calls:
            response = self.client.post('/password_reset/',
                    {'email': 'staffmember@example.com'},
                    HTTP_HOST='www.example:dr.frankenstein@evil.tld'
                )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(len(mail.outbox), 0)
            self.assertEqual(len(logger_calls), 1)

    # Skip any 500 handler action (like sending more mail...)
    @override_settings(DEBUG_PROPAGATE_EXCEPTIONS=True)
    def test_poisoned_http_host_admin_site(self):
        "Poisoned HTTP_HOST headers can't be used for reset emails on admin views"
        with patch_logger('django.security.DisallowedHost', 'error') as logger_calls:
            response = self.client.post('/admin_password_reset/',
                    {'email': 'staffmember@example.com'},
                    HTTP_HOST='www.example:dr.frankenstein@evil.tld'
                )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(len(mail.outbox), 0)
            self.assertEqual(len(logger_calls), 1)


    def _test_confirm_start(self):
        # Start by creating the email
        response = self.client.post('/password_reset/', {'email': 'staffmember@example.com'})
        self.assertEqual(len(mail.outbox), 1)
        return self._read_signup_email(mail.outbox[0])

    def _read_signup_email(self, email):
        urlmatch = re.search(r"https?://[^/]*(/.*reset/\S*)", email.body)
        self.assertTrue(urlmatch is not None, "No URL found in sent email")
        return urlmatch.group(), urlmatch.groups()[0]

    def test_confirm_valid(self):
        url, path = self._test_confirm_start()
        response = self.client.get(path)
        # redirect to a 'complete' page:
        self.assertContains(response, "Please enter your new password")

    def test_confirm_invalid(self):
        url, path = self._test_confirm_start()
        # Let's munge the token in the path, but keep the same length,
        # in case the URLconf will reject a different length.
        path = path[:-5] + ("0" * 4) + path[-1]

        response = self.client.get(path)
        self.assertContains(response, "The password reset link was invalid")

    def test_confirm_invalid_user(self):
        # Ensure that we get a 200 response for a non-existant user, not a 404
        response = self.client.get('/reset/123456/1-1/')
        self.assertContains(response, "The password reset link was invalid")

    def test_confirm_overflow_user(self):
        # Ensure that we get a 200 response for a base36 user id that overflows int
        response = self.client.get('/reset/zzzzzzzzzzzzz/1-1/')
        self.assertContains(response, "The password reset link was invalid")

    def test_confirm_invalid_post(self):
        # Same as test_confirm_invalid, but trying
        # to do a POST instead.
        url, path = self._test_confirm_start()
        path = path[:-5] + ("0" * 4) + path[-1]

        self.client.post(path, {
            'new_password1': 'anewpassword',
            'new_password2': ' anewpassword',
        })
        # Check the password has not been changed
        u = User.objects.get(email='staffmember@example.com')
        self.assertTrue(not u.check_password("anewpassword"))

    def test_confirm_complete(self):
        url, path = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2': 'anewpassword'})
        # Check the password has been changed
        u = User.objects.get(email='staffmember@example.com')
        self.assertTrue(u.check_password("anewpassword"))

        # Check we can't use the link again
        response = self.client.get(path)
        self.assertContains(response, "The password reset link was invalid")

    def test_confirm_different_passwords(self):
        url, path = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2': 'x'})
        self.assertFormError(response, SetPasswordForm.error_messages['password_mismatch'])

    def test_reset_redirect_default(self):
        response = self.client.post('/password_reset/',
            {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/password_reset/done/')

    def test_reset_custom_redirect(self):
        response = self.client.post('/password_reset/custom_redirect/',
            {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/custom/')

    def test_reset_custom_redirect_named(self):
        response = self.client.post('/password_reset/custom_redirect/named/',
            {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/password_reset/')

    def test_confirm_redirect_default(self):
        url, path = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2': 'anewpassword'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/reset/done/')

    def test_confirm_redirect_custom(self):
        url, path = self._test_confirm_start()
        path = path.replace('/reset/', '/reset/custom/')
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2': 'anewpassword'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/custom/')

    def test_confirm_redirect_custom_named(self):
        url, path = self._test_confirm_start()
        path = path.replace('/reset/', '/reset/custom/named/')
        response = self.client.post(path, {'new_password1': 'anewpassword',
                                           'new_password2': 'anewpassword'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/password_reset/')


@override_settings(AUTH_USER_MODEL='auth.CustomUser')
class CustomUserPasswordResetTest(AuthViewsTestCase):
    fixtures = ['custom_user.json']

    def _test_confirm_start(self):
        # Start by creating the email
        response = self.client.post('/password_reset/', {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        return self._read_signup_email(mail.outbox[0])

    def _read_signup_email(self, email):
        urlmatch = re.search(r"https?://[^/]*(/.*reset/\S*)", email.body)
        self.assertTrue(urlmatch is not None, "No URL found in sent email")
        return urlmatch.group(), urlmatch.groups()[0]

    def test_confirm_valid_custom_user(self):
        url, path = self._test_confirm_start()
        response = self.client.get(path)
        # redirect to a 'complete' page:
        self.assertContains(response, "Please enter your new password")


@skipIfCustomUser
class ChangePasswordTest(AuthViewsTestCase):

    def fail_login(self, password='password'):
        response = self.client.post('/login/', {
            'username': 'testclient',
            'password': password,
        })
        self.assertFormError(response, AuthenticationForm.error_messages['invalid_login'] % {
                'username': User._meta.get_field('username').verbose_name
            })

    def logout(self):
        response = self.client.get('/logout/')

    def test_password_change_fails_with_invalid_old_password(self):
        self.login()
        response = self.client.post('/password_change/', {
            'old_password': 'donuts',
            'new_password1': 'password1',
            'new_password2': 'password1',
        })
        self.assertFormError(response, PasswordChangeForm.error_messages['password_incorrect'])

    def test_password_change_fails_with_mismatched_passwords(self):
        self.login()
        response = self.client.post('/password_change/', {
            'old_password': 'password',
            'new_password1': 'password1',
            'new_password2': 'donuts',
        })
        self.assertFormError(response, SetPasswordForm.error_messages['password_mismatch'])

    def test_password_change_succeeds(self):
        self.login()
        response = self.client.post('/password_change/', {
            'old_password': 'password',
            'new_password1': 'password1',
            'new_password2': 'password1',
        })
        self.fail_login()
        self.login(password='password1')

    def test_password_change_done_succeeds(self):
        self.login()
        response = self.client.post('/password_change/', {
            'old_password': 'password',
            'new_password1': 'password1',
            'new_password2': 'password1',
        })
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/password_change/done/')

    @override_settings(LOGIN_URL='/login/')
    def test_password_change_done_fails(self):
        response = self.client.get('/password_change/done/')
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/login/?next=/password_change/done/')

    def test_password_change_redirect_default(self):
        self.login()
        response = self.client.post('/password_change/', {
            'old_password': 'password',
            'new_password1': 'password1',
            'new_password2': 'password1',
        })
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/password_change/done/')

    def test_password_change_redirect_custom(self):
        self.login()
        response = self.client.post('/password_change/custom/', {
            'old_password': 'password',
            'new_password1': 'password1',
            'new_password2': 'password1',
        })
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/custom/')

    def test_password_change_redirect_custom_named(self):
        self.login()
        response = self.client.post('/password_change/custom/named/', {
            'old_password': 'password',
            'new_password1': 'password1',
            'new_password2': 'password1',
        })
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/password_reset/')


@skipIfCustomUser
class LoginTest(AuthViewsTestCase):

    def test_current_site_in_context_after_login(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        if Site._meta.installed:
            site = Site.objects.get_current()
            self.assertEqual(response.context['site'], site)
            self.assertEqual(response.context['site_name'], site.name)
        else:
            self.assertIsInstance(response.context['site'], RequestSite)
        self.assertTrue(isinstance(response.context['form'], AuthenticationForm),
                     'Login form is not an AuthenticationForm')

    def test_security_check(self, password='password'):
        login_url = reverse('login')

        # Those URLs should not pass the security check
        for bad_url in ('http://example.com',
                        'https://example.com',
                        'ftp://exampel.com',
                        '//example.com'):

            nasty_url = '%(url)s?%(next)s=%(bad_url)s' % {
                'url': login_url,
                'next': REDIRECT_FIELD_NAME,
                'bad_url': urlquote(bad_url),
            }
            response = self.client.post(nasty_url, {
                'username': 'testclient',
                'password': password,
            })
            self.assertEqual(response.status_code, 302)
            self.assertFalse(bad_url in response.url,
                             "%s should be blocked" % bad_url)

        # These URLs *should* still pass the security check
        for good_url in ('/view/?param=http://example.com',
                         '/view/?param=https://example.com',
                         '/view?param=ftp://exampel.com',
                         'view/?param=//example.com',
                         'https:///',
                         '//testserver/',
                         '/url%20with%20spaces/'):  # see ticket #12534
            safe_url = '%(url)s?%(next)s=%(good_url)s' % {
                'url': login_url,
                'next': REDIRECT_FIELD_NAME,
                'good_url': urlquote(good_url),
            }
            response = self.client.post(safe_url, {
                    'username': 'testclient',
                    'password': password,
            })
            self.assertEqual(response.status_code, 302)
            self.assertTrue(good_url in response.url,
                            "%s should be allowed" % good_url)

    def test_login_form_contains_request(self):
        # 15198
        response = self.client.post('/custom_requestauth_login/', {
            'username': 'testclient',
            'password': 'password',
        }, follow=True)
        # the custom authentication form used by this login asserts
        # that a request is passed to the form successfully.

    def test_login_csrf_rotate(self, password='password'):
        """
        Makes sure that a login rotates the currently-used CSRF token.
        """
        # Do a GET to establish a CSRF token
        # TestClient isn't used here as we're testing middleware, essentially.
        req = HttpRequest()
        CsrfViewMiddleware().process_view(req, login_view, (), {})
        req.META["CSRF_COOKIE_USED"] = True
        resp = login_view(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = resp2.cookies.get(settings.CSRF_COOKIE_NAME, None)
        token1 = csrf_cookie.coded_value

        # Prepare the POST request
        req = HttpRequest()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = token1
        req.method = "POST"
        req.POST = {'username': 'testclient', 'password': password, 'csrfmiddlewaretoken': token1}
        req.REQUEST = req.POST

        # Use POST request to log in
        SessionMiddleware().process_request(req)
        CsrfViewMiddleware().process_view(req, login_view, (), {})
        req.META["SERVER_NAME"] = "testserver"  # Required to have redirect work in login view
        req.META["SERVER_PORT"] = 80
        req.META["CSRF_COOKIE_USED"] = True
        resp = login_view(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = resp2.cookies.get(settings.CSRF_COOKIE_NAME, None)
        token2 = csrf_cookie.coded_value

        # Check the CSRF token switched
        self.assertNotEqual(token1, token2)


@skipIfCustomUser
class LoginURLSettings(AuthViewsTestCase):
    """Tests for settings.LOGIN_URL."""
    def assertLoginURLEquals(self, url, parse_qs=False):
        response = self.client.get('/login_required/')
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, url, parse_qs=parse_qs)

    @override_settings(LOGIN_URL='/login/')
    def test_standard_login_url(self):
        self.assertLoginURLEquals('/login/?next=/login_required/')

    @override_settings(LOGIN_URL='login')
    def test_named_login_url(self):
        self.assertLoginURLEquals('/login/?next=/login_required/')

    @override_settings(LOGIN_URL='http://remote.example.com/login')
    def test_remote_login_url(self):
        quoted_next = urlquote('http://testserver/login_required/')
        expected = 'http://remote.example.com/login?next=%s' % quoted_next
        self.assertLoginURLEquals(expected)

    @override_settings(LOGIN_URL='https:///login/')
    def test_https_login_url(self):
        quoted_next = urlquote('http://testserver/login_required/')
        expected = 'https:///login/?next=%s' % quoted_next
        self.assertLoginURLEquals(expected)

    @override_settings(LOGIN_URL='/login/?pretty=1')
    def test_login_url_with_querystring(self):
        self.assertLoginURLEquals('/login/?pretty=1&next=/login_required/', parse_qs=True)

    @override_settings(LOGIN_URL='http://remote.example.com/login/?next=/default/')
    def test_remote_login_url_with_next_querystring(self):
        quoted_next = urlquote('http://testserver/login_required/')
        expected = 'http://remote.example.com/login/?next=%s' % quoted_next
        self.assertLoginURLEquals(expected)


@skipIfCustomUser
class LoginRedirectUrlTest(AuthViewsTestCase):
    """Tests for settings.LOGIN_REDIRECT_URL."""
    def assertLoginRedirectURLEqual(self, url):
        response = self.login()
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, url)

    def test_default(self):
        self.assertLoginRedirectURLEqual('/accounts/profile/')

    @override_settings(LOGIN_REDIRECT_URL='/custom/')
    def test_custom(self):
        self.assertLoginRedirectURLEqual('/custom/')

    @override_settings(LOGIN_REDIRECT_URL='password_reset')
    def test_named(self):
        self.assertLoginRedirectURLEqual('/password_reset/')

    @override_settings(LOGIN_REDIRECT_URL='http://remote.example.com/welcome/')
    def test_remote(self):
        self.assertLoginRedirectURLEqual('http://remote.example.com/welcome/')


@skipIfCustomUser
class LogoutTest(AuthViewsTestCase):

    def confirm_logged_out(self):
        self.assertTrue(SESSION_KEY not in self.client.session)

    def test_logout_default(self):
        "Logout without next_page option renders the default template"
        self.login()
        response = self.client.get('/logout/')
        self.assertContains(response, 'Logged out')
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
        self.assertURLEqual(response.url, '/somewhere/')

        response = self.client.get('/logout/next_page/?next=/login/')
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/login/')

        self.confirm_logged_out()

    def test_logout_with_next_page_specified(self):
        "Logout with next_page option given redirects to specified resource"
        self.login()
        response = self.client.get('/logout/next_page/')
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/somewhere/')
        self.confirm_logged_out()

    def test_logout_with_redirect_argument(self):
        "Logout with query string redirects to specified resource"
        self.login()
        response = self.client.get('/logout/?next=/login/')
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/login/')
        self.confirm_logged_out()

    def test_logout_with_custom_redirect_argument(self):
        "Logout with custom query string redirects to specified resource"
        self.login()
        response = self.client.get('/logout/custom_query/?follow=/somewhere/')
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/somewhere/')
        self.confirm_logged_out()

    def test_logout_with_named_redirect(self):
        "Logout resolves names or URLs passed as next_page."
        self.login()
        response = self.client.get('/logout/next_page/named/')
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/password_reset/')
        self.confirm_logged_out()

    def test_security_check(self, password='password'):
        logout_url = reverse('logout')

        # Those URLs should not pass the security check
        for bad_url in ('http://example.com',
                        'https://example.com',
                        'ftp://exampel.com',
                        '//example.com'):
            nasty_url = '%(url)s?%(next)s=%(bad_url)s' % {
                'url': logout_url,
                'next': REDIRECT_FIELD_NAME,
                'bad_url': urlquote(bad_url),
            }
            self.login()
            response = self.client.get(nasty_url)
            self.assertEqual(response.status_code, 302)
            self.assertFalse(bad_url in response.url,
                             "%s should be blocked" % bad_url)
            self.confirm_logged_out()

        # These URLs *should* still pass the security check
        for good_url in ('/view/?param=http://example.com',
                         '/view/?param=https://example.com',
                         '/view?param=ftp://exampel.com',
                         'view/?param=//example.com',
                         'https:///',
                         '//testserver/',
                         '/url%20with%20spaces/'):  # see ticket #12534
            safe_url = '%(url)s?%(next)s=%(good_url)s' % {
                'url': logout_url,
                'next': REDIRECT_FIELD_NAME,
                'good_url': urlquote(good_url),
            }
            self.login()
            response = self.client.get(safe_url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(good_url in response.url,
                            "%s should be allowed" % good_url)
            self.confirm_logged_out()

@skipIfCustomUser
class ChangelistTests(AuthViewsTestCase):
    urls = 'django.contrib.auth.tests.urls_admin'

    # #20078 - users shouldn't be allowed to guess password hashes via
    # repeated password__startswith queries.
    def test_changelist_disallows_password_lookups(self):
        # Make me a superuser before loging in.
        User.objects.filter(username='testclient').update(is_staff=True, is_superuser=True)
        self.login()

        # A lookup that tries to filter on password isn't OK
        with patch_logger('django.security.DisallowedModelAdminLookup', 'error') as logger_calls:
            response = self.client.get('/admin/auth/user/?password__startswith=sha1$')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(len(logger_calls), 1)
