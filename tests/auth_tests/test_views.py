# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import itertools
import re
from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth import REDIRECT_FIELD_NAME, SESSION_KEY
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm, SetPasswordForm,
)
from django.contrib.auth.models import User
from django.contrib.auth.views import login as login_view, redirect_to_login
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sites.requests import RequestSite
from django.core import mail
from django.core.urlresolvers import NoReverseMatch, reverse, reverse_lazy
from django.db import connection
from django.http import HttpRequest, QueryDict
from django.middleware.csrf import CsrfViewMiddleware
from django.test import (
    TestCase, ignore_warnings, modify_settings, override_settings,
)
from django.test.utils import patch_logger
from django.utils.deprecation import RemovedInDjango110Warning
from django.utils.encoding import force_text
from django.utils.http import urlquote
from django.utils.six.moves.urllib.parse import ParseResult, urlparse
from django.utils.translation import LANGUAGE_SESSION_KEY

from .models import UUIDUser
from .settings import AUTH_TEMPLATES


@override_settings(
    LANGUAGES=(
        ('en', 'English'),
    ),
    LANGUAGE_CODE='en',
    TEMPLATES=AUTH_TEMPLATES,
    USE_TZ=False,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.SHA1PasswordHasher'],
    ROOT_URLCONF='auth_tests.urls',
)
class AuthViewsTestCase(TestCase):
    """
    Helper base class for all the follow test cases.
    """
    fixtures = ['authtestdata.json']

    def login(self, username='testclient', password='password'):
        response = self.client.post('/login/', {
            'username': username,
            'password': password,
        })
        self.assertIn(SESSION_KEY, self.client.session)
        return response

    def logout(self):
        response = self.client.get('/admin/logout/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

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


@override_settings(ROOT_URLCONF='django.contrib.auth.urls')
class AuthViewNamedURLTests(AuthViewsTestCase):

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
        self.assertIn("http://", mail.outbox[0].body)
        self.assertEqual(settings.DEFAULT_FROM_EMAIL, mail.outbox[0].from_email)
        # optional multipart text/html email has been added.  Make sure original,
        # default functionality is 100% the same
        self.assertFalse(mail.outbox[0].message().is_multipart())

    def test_html_mail_template(self):
        """
        A multipart email with text/plain and text/html is sent
        if the html_email_template parameter is passed to the view
        """
        response = self.client.post('/password_reset/html_email_template/', {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0].message()
        self.assertEqual(len(message.get_payload()), 2)
        self.assertTrue(message.is_multipart())
        self.assertEqual(message.get_payload(0).get_content_type(), 'text/plain')
        self.assertEqual(message.get_payload(1).get_content_type(), 'text/html')
        self.assertNotIn('<html>', message.get_payload(0).get_payload())
        self.assertIn('<html>', message.get_payload(1).get_payload())

    def test_email_found_custom_from(self):
        "Email is sent if a valid email address is provided for password reset when a custom from_email is provided."
        response = self.client.post('/password_reset_from_email/', {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual("staffmember@example.com", mail.outbox[0].from_email)

    @ignore_warnings(category=RemovedInDjango110Warning)
    @override_settings(ALLOWED_HOSTS=['adminsite.com'])
    def test_admin_reset(self):
        "If the reset view is marked as being for admin, the HTTP_HOST header is used for a domain override."
        response = self.client.post('/admin_password_reset/',
            {'email': 'staffmember@example.com'},
            HTTP_HOST='adminsite.com'
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("http://adminsite.com", mail.outbox[0].body)
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
            response = self.client.post(
                '/password_reset/',
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
            response = self.client.post(
                '/admin_password_reset/',
                {'email': 'staffmember@example.com'},
                HTTP_HOST='www.example:dr.frankenstein@evil.tld'
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(len(mail.outbox), 0)
            self.assertEqual(len(logger_calls), 1)

    def _test_confirm_start(self):
        # Start by creating the email
        self.client.post('/password_reset/', {'email': 'staffmember@example.com'})
        self.assertEqual(len(mail.outbox), 1)
        return self._read_signup_email(mail.outbox[0])

    def _read_signup_email(self, email):
        urlmatch = re.search(r"https?://[^/]*(/.*reset/\S*)", email.body)
        self.assertIsNotNone(urlmatch, "No URL found in sent email")
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
        # Ensure that we get a 200 response for a non-existent user, not a 404
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

    def test_confirm_display_user_from_form(self):
        url, path = self._test_confirm_start()
        response = self.client.get(path)

        # #16919 -- The ``password_reset_confirm`` view should pass the user
        # object to the ``SetPasswordForm``, even on GET requests.
        # For this test, we render ``{{ form.user }}`` in the template
        # ``registration/password_reset_confirm.html`` so that we can test this.
        username = User.objects.get(email='staffmember@example.com').username
        self.assertContains(response, "Hello, %s." % username)

        # However, the view should NOT pass any user object on a form if the
        # password reset link was invalid.
        response = self.client.get('/reset/zzzzzzzzzzzzz/1-1/')
        self.assertContains(response, "Hello, .")


@override_settings(AUTH_USER_MODEL='auth.CustomUser')
class CustomUserPasswordResetTest(AuthViewsTestCase):
    fixtures = ['custom_user.json']
    user_email = 'staffmember@example.com'

    def _test_confirm_start(self):
        # Start by creating the email
        response = self.client.post('/password_reset/', {'email': self.user_email})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        return self._read_signup_email(mail.outbox[0])

    def _read_signup_email(self, email):
        urlmatch = re.search(r"https?://[^/]*(/.*reset/\S*)", email.body)
        self.assertIsNotNone(urlmatch, "No URL found in sent email")
        return urlmatch.group(), urlmatch.groups()[0]

    def test_confirm_valid_custom_user(self):
        url, path = self._test_confirm_start()
        response = self.client.get(path)
        # redirect to a 'complete' page:
        self.assertContains(response, "Please enter your new password")
        # then submit a new password
        response = self.client.post(path, {
            'new_password1': 'anewpassword',
            'new_password2': 'anewpassword',
        })
        self.assertRedirects(response, '/reset/done/')


@override_settings(AUTH_USER_MODEL='auth.UUIDUser')
class UUIDUserPasswordResetTest(CustomUserPasswordResetTest):
    fixtures = None

    def _test_confirm_start(self):
        # instead of fixture
        UUIDUser.objects.create_user(
            email=self.user_email,
            username='foo',
            password='foo',
        )
        return super(UUIDUserPasswordResetTest, self)._test_confirm_start()


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
        self.client.get('/logout/')

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
        self.client.post('/password_change/', {
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


@override_settings(MIDDLEWARE_CLASSES=list(settings.MIDDLEWARE_CLASSES) + [
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware'
])
class SessionAuthenticationTests(AuthViewsTestCase):
    def test_user_password_change_updates_session(self):
        """
        #21649 - Ensure contrib.auth.views.password_change updates the user's
        session auth hash after a password change so the session isn't logged out.
        """
        self.login()
        response = self.client.post('/password_change/', {
            'old_password': 'password',
            'new_password1': 'password1',
            'new_password2': 'password1',
        })
        # if the hash isn't updated, retrieving the redirection page will fail.
        self.assertRedirects(response, '/password_change/done/')


class LoginTest(AuthViewsTestCase):

    def test_current_site_in_context_after_login(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        if apps.is_installed('django.contrib.sites'):
            Site = apps.get_model('sites.Site')
            site = Site.objects.get_current()
            self.assertEqual(response.context['site'], site)
            self.assertEqual(response.context['site_name'], site.name)
        else:
            self.assertIsInstance(response.context['site'], RequestSite)
        self.assertIsInstance(response.context['form'], AuthenticationForm)

    def test_security_check(self, password='password'):
        login_url = reverse('login')

        # Those URLs should not pass the security check
        for bad_url in ('http://example.com',
                        'http:///example.com',
                        'https://example.com',
                        'ftp://exampel.com',
                        '///example.com',
                        '//example.com',
                        'javascript:alert("XSS")'):

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
            self.assertNotIn(bad_url, response.url,
                             "%s should be blocked" % bad_url)

        # These URLs *should* still pass the security check
        for good_url in ('/view/?param=http://example.com',
                         '/view/?param=https://example.com',
                         '/view?param=ftp://exampel.com',
                         'view/?param=//example.com',
                         'https://testserver/',
                         'HTTPS://testserver/',
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
            self.assertIn(good_url, response.url, "%s should be allowed" % good_url)

    def test_login_form_contains_request(self):
        # 15198
        self.client.post('/custom_requestauth_login/', {
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

        # Use POST request to log in
        SessionMiddleware().process_request(req)
        CsrfViewMiddleware().process_view(req, login_view, (), {})
        req.META["SERVER_NAME"] = "testserver"  # Required to have redirect work in login view
        req.META["SERVER_PORT"] = 80
        resp = login_view(req)
        resp2 = CsrfViewMiddleware().process_response(req, resp)
        csrf_cookie = resp2.cookies.get(settings.CSRF_COOKIE_NAME, None)
        token2 = csrf_cookie.coded_value

        # Check the CSRF token switched
        self.assertNotEqual(token1, token2)

    def test_session_key_flushed_on_login(self):
        """
        To avoid reusing another user's session, ensure a new, empty session is
        created if the existing session corresponds to a different authenticated
        user.
        """
        self.login()
        original_session_key = self.client.session.session_key

        self.login(username='staff')
        self.assertNotEqual(original_session_key, self.client.session.session_key)

    def test_session_key_flushed_on_login_after_password_change(self):
        """
        As above, but same user logging in after a password change.
        """
        self.login()
        original_session_key = self.client.session.session_key

        # If no password change, session key should not be flushed.
        self.login()
        self.assertEqual(original_session_key, self.client.session.session_key)

        user = User.objects.get(username='testclient')
        user.set_password('foobar')
        user.save()

        self.login(password='foobar')
        self.assertNotEqual(original_session_key, self.client.session.session_key)

    def test_login_session_without_hash_session_key(self):
        """
        Session without django.contrib.auth.HASH_SESSION_KEY should login
        without an exception.
        """
        user = User.objects.get(username='testclient')
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore()
        session[SESSION_KEY] = user.id
        session.save()
        original_session_key = session.session_key
        self.client.cookies[settings.SESSION_COOKIE_NAME] = original_session_key

        self.login()
        self.assertNotEqual(original_session_key, self.client.session.session_key)


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

    @override_settings(LOGIN_URL=reverse_lazy('login'))
    def test_lazy_login_url(self):
        self.assertLoginURLEquals('/login/?next=/login_required/')


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


class RedirectToLoginTests(AuthViewsTestCase):
    """Tests for the redirect_to_login view"""
    @override_settings(LOGIN_URL=reverse_lazy('login'))
    def test_redirect_to_login_with_lazy(self):
        login_redirect_response = redirect_to_login(next='/else/where/')
        expected = '/login/?next=/else/where/'
        self.assertEqual(expected, login_redirect_response.url)

    @override_settings(LOGIN_URL=reverse_lazy('login'))
    def test_redirect_to_login_with_lazy_and_unicode(self):
        login_redirect_response = redirect_to_login(next='/else/where/झ/')
        expected = '/login/?next=/else/where/%E0%A4%9D/'
        self.assertEqual(expected, login_redirect_response.url)


class LogoutTest(AuthViewsTestCase):

    def confirm_logged_out(self):
        self.assertNotIn(SESSION_KEY, self.client.session)

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
        self.assertIn('site', response.context)

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
                        'http:///example.com',
                        'https://example.com',
                        'ftp://exampel.com',
                        '///example.com',
                        '//example.com',
                        'javascript:alert("XSS")'):
            nasty_url = '%(url)s?%(next)s=%(bad_url)s' % {
                'url': logout_url,
                'next': REDIRECT_FIELD_NAME,
                'bad_url': urlquote(bad_url),
            }
            self.login()
            response = self.client.get(nasty_url)
            self.assertEqual(response.status_code, 302)
            self.assertNotIn(bad_url, response.url,
                             "%s should be blocked" % bad_url)
            self.confirm_logged_out()

        # These URLs *should* still pass the security check
        for good_url in ('/view/?param=http://example.com',
                         '/view/?param=https://example.com',
                         '/view?param=ftp://exampel.com',
                         'view/?param=//example.com',
                         'https://testserver/',
                         'HTTPS://testserver/',
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
            self.assertIn(good_url, response.url, "%s should be allowed" % good_url)
            self.confirm_logged_out()

    def test_logout_preserve_language(self):
        """Check that language stored in session is preserved after logout"""
        # Create a new session with language
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore()
        session[LANGUAGE_SESSION_KEY] = 'pl'
        session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key

        self.client.get('/logout/')
        self.assertEqual(self.client.session[LANGUAGE_SESSION_KEY], 'pl')


# Redirect in test_user_change_password will fail if session auth hash
# isn't updated after password change (#21649)
@modify_settings(MIDDLEWARE_CLASSES={
    'append': 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
})
@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.SHA1PasswordHasher'],
    ROOT_URLCONF='auth_tests.urls_admin',
)
class ChangelistTests(AuthViewsTestCase):

    def setUp(self):
        # Make me a superuser before logging in.
        User.objects.filter(username='testclient').update(is_staff=True, is_superuser=True)
        self.login()
        self.admin = User.objects.get(pk=1)

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
            'first_name': user.first_name,
            'last_name': user.last_name,
        }

    # #20078 - users shouldn't be allowed to guess password hashes via
    # repeated password__startswith queries.
    def test_changelist_disallows_password_lookups(self):
        # A lookup that tries to filter on password isn't OK
        with patch_logger('django.security.DisallowedModelAdminLookup', 'error') as logger_calls:
            response = self.client.get('/admin/auth/user/?password__startswith=sha1$')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(len(logger_calls), 1)

    def test_user_change_email(self):
        data = self.get_user_data(self.admin)
        data['email'] = 'new_' + data['email']
        response = self.client.post('/admin/auth/user/%s/' % self.admin.pk, data)
        self.assertRedirects(response, '/admin/auth/user/')
        row = LogEntry.objects.latest('id')
        self.assertEqual(row.change_message, 'Changed email.')

    def test_user_not_change(self):
        response = self.client.post('/admin/auth/user/%s/' % self.admin.pk,
            self.get_user_data(self.admin)
        )
        self.assertRedirects(response, '/admin/auth/user/')
        row = LogEntry.objects.latest('id')
        self.assertEqual(row.change_message, 'No fields changed.')

    def test_user_change_password(self):
        response = self.client.post('/admin/auth/user/%s/password/' % self.admin.pk, {
            'password1': 'password1',
            'password2': 'password1',
        })
        self.assertRedirects(response, '/admin/auth/user/%s/' % self.admin.pk)
        row = LogEntry.objects.latest('id')
        self.assertEqual(row.change_message, 'Changed password.')
        self.logout()
        self.login(password='password1')

    def test_user_change_different_user_password(self):
        u = User.objects.get(email='staffmember@example.com')
        response = self.client.post('/admin/auth/user/%s/password/' % u.pk, {
            'password1': 'password1',
            'password2': 'password1',
        })
        self.assertRedirects(response, '/admin/auth/user/%s/' % u.pk)
        row = LogEntry.objects.latest('id')
        self.assertEqual(row.user_id, self.admin.pk)
        self.assertEqual(row.object_id, str(u.pk))
        self.assertEqual(row.change_message, 'Changed password.')

    def test_password_change_bad_url(self):
        response = self.client.get(reverse('auth_test_admin:auth_user_password_change', args=('foobar',)))
        self.assertEqual(response.status_code, 404)


@override_settings(
    AUTH_USER_MODEL='auth.UUIDUser',
    ROOT_URLCONF='auth_tests.urls_custom_user_admin',
)
class UUIDUserTests(TestCase):

    def test_admin_password_change(self):
        u = UUIDUser.objects.create_superuser(username='uuid', email='foo@bar.com', password='test')
        self.assertTrue(self.client.login(username='uuid', password='test'))

        user_change_url = reverse('custom_user_admin:auth_uuiduser_change', args=(u.pk,))
        response = self.client.get(user_change_url)
        self.assertEqual(response.status_code, 200)

        password_change_url = reverse('custom_user_admin:auth_user_password_change', args=(u.pk,))
        response = self.client.get(password_change_url)
        self.assertEqual(response.status_code, 200)

        # A LogEntry is created with pk=1 which breaks a FK constraint on MySQL
        with connection.constraint_checks_disabled():
            response = self.client.post(password_change_url, {
                'password1': 'password1',
                'password2': 'password1',
            })
        self.assertRedirects(response, user_change_url)
        row = LogEntry.objects.latest('id')
        self.assertEqual(row.user_id, 1)  # harcoded in CustomUserAdmin.log_change()
        self.assertEqual(row.object_id, str(u.pk))
        self.assertEqual(row.change_message, 'Changed password.')
