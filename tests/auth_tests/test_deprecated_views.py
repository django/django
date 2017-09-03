# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import itertools
import re

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordChangeForm, SetPasswordForm,
)
from django.contrib.auth.models import User
from django.contrib.auth.views import login, logout
from django.core import mail
from django.http import QueryDict
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import ignore_warnings, patch_logger
from django.utils.deprecation import RemovedInDjango21Warning
from django.utils.encoding import force_text
from django.utils.six.moves.urllib.parse import ParseResult, urlparse

from .models import CustomUser, UUIDUser
from .settings import AUTH_TEMPLATES


@override_settings(
    LANGUAGES=[('en', 'English')],
    LANGUAGE_CODE='en',
    TEMPLATES=AUTH_TEMPLATES,
    ROOT_URLCONF='auth_tests.urls_deprecated',
)
class AuthViewsTestCase(TestCase):
    """
    Helper base class for all the follow test cases.
    """

    @classmethod
    def setUpTestData(cls):
        cls.u1 = User.objects.create_user(username='testclient', password='password', email='testclient@example.com')
        cls.u3 = User.objects.create_user(username='staff', password='password', email='staffmember@example.com')

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


@ignore_warnings(category=RemovedInDjango21Warning)
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

    def test_extra_email_context(self):
        """
        extra_email_context should be available in the email template context.
        """
        response = self.client.post(
            '/password_reset_extra_email_context/',
            {'email': 'staffmember@example.com'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Email email context: "Hello!"', mail.outbox[0].body)

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
        # We get a 200 response for a non-existent user, not a 404
        response = self.client.get('/reset/123456/1-1/')
        self.assertContains(response, "The password reset link was invalid")

    def test_confirm_overflow_user(self):
        # We get a 200 response for a base36 user id that overflows int
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
        response = self.client.post(path, {'new_password1': 'anewpassword', 'new_password2': 'anewpassword'})
        # Check the password has been changed
        u = User.objects.get(email='staffmember@example.com')
        self.assertTrue(u.check_password("anewpassword"))

        # Check we can't use the link again
        response = self.client.get(path)
        self.assertContains(response, "The password reset link was invalid")

    def test_confirm_different_passwords(self):
        url, path = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword', 'new_password2': 'x'})
        self.assertFormError(response, SetPasswordForm.error_messages['password_mismatch'])

    def test_reset_redirect_default(self):
        response = self.client.post('/password_reset/', {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/password_reset/done/')

    def test_reset_custom_redirect(self):
        response = self.client.post('/password_reset/custom_redirect/', {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/custom/')

    def test_reset_custom_redirect_named(self):
        response = self.client.post('/password_reset/custom_redirect/named/', {'email': 'staffmember@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/password_reset/')

    def test_confirm_redirect_default(self):
        url, path = self._test_confirm_start()
        response = self.client.post(path, {'new_password1': 'anewpassword', 'new_password2': 'anewpassword'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/reset/done/')

    def test_confirm_redirect_custom(self):
        url, path = self._test_confirm_start()
        path = path.replace('/reset/', '/reset/custom/')
        response = self.client.post(path, {'new_password1': 'anewpassword', 'new_password2': 'anewpassword'})
        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, '/custom/')

    def test_confirm_redirect_custom_named(self):
        url, path = self._test_confirm_start()
        path = path.replace('/reset/', '/reset/custom/named/')
        response = self.client.post(path, {'new_password1': 'anewpassword', 'new_password2': 'anewpassword'})
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


@ignore_warnings(category=RemovedInDjango21Warning)
@override_settings(AUTH_USER_MODEL='auth_tests.CustomUser')
class CustomUserPasswordResetTest(AuthViewsTestCase):
    user_email = 'staffmember@example.com'

    @classmethod
    def setUpTestData(cls):
        cls.u1 = CustomUser.custom_objects.create(
            email='staffmember@example.com',
            date_of_birth=datetime.date(1976, 11, 8),
        )
        cls.u1.set_password('password')
        cls.u1.save()

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


@ignore_warnings(category=RemovedInDjango21Warning)
@override_settings(AUTH_USER_MODEL='auth_tests.UUIDUser')
class UUIDUserPasswordResetTest(CustomUserPasswordResetTest):

    def _test_confirm_start(self):
        # instead of fixture
        UUIDUser.objects.create_user(
            email=self.user_email,
            username='foo',
            password='foo',
        )
        return super(UUIDUserPasswordResetTest, self)._test_confirm_start()


@ignore_warnings(category=RemovedInDjango21Warning)
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


@ignore_warnings(category=RemovedInDjango21Warning)
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


@ignore_warnings(category=RemovedInDjango21Warning)
class TestLogin(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')

    def test_template_name(self):
        response = login(self.request, 'template.html')
        self.assertEqual(response.template_name, ['template.html'])

    def test_form_class(self):
        class NewForm(AuthenticationForm):
            def confirm_login_allowed(self, user):
                pass
        response = login(self.request, 'template.html', None, NewForm)
        self.assertEqual(response.context_data['form'].__class__.__name__, 'NewForm')

    def test_extra_context(self):
        extra_context = {'fake_context': 'fake_context'}
        response = login(self.request, 'template.html', None, AuthenticationForm, extra_context)
        self.assertEqual(response.resolve_context('fake_context'), 'fake_context')


@ignore_warnings(category=RemovedInDjango21Warning)
class TestLogout(AuthViewsTestCase):
    def setUp(self):
        self.login()
        self.factory = RequestFactory()
        self.request = self.factory.post('/')
        self.request.session = self.client.session

    def test_template_name(self):
        response = logout(self.request, None, 'template.html')
        self.assertEqual(response.template_name, ['template.html'])

    def test_next_page(self):
        response = logout(self.request, 'www.next_page.com')
        self.assertEqual(response.url, 'www.next_page.com')

    def test_extra_context(self):
        extra_context = {'fake_context': 'fake_context'}
        response = logout(self.request, None, 'template.html', None, extra_context)
        self.assertEqual(response.resolve_context('fake_context'), 'fake_context')
