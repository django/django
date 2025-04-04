import datetime
import itertools
import re
from importlib import import_module
from unittest import mock
from urllib.parse import quote, urljoin

from django.apps import apps
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth import BACKEND_SESSION_KEY, REDIRECT_FIELD_NAME, SESSION_KEY
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    SetPasswordForm,
)
from django.contrib.auth.models import Permission, User
from django.contrib.auth.views import (
    INTERNAL_RESET_SESSION_TOKEN,
    LoginView,
    RedirectURLMixin,
    logout_then_login,
    redirect_to_login,
)
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import Message
from django.contrib.messages.test import MessagesTestMixin
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sites.requests import RequestSite
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.middleware.csrf import CsrfViewMiddleware, get_token
from django.test import Client, TestCase, modify_settings, override_settings
from django.test.client import RedirectCycleError
from django.urls import NoReverseMatch, reverse, reverse_lazy
from django.utils.http import urlsafe_base64_encode

from .client import PasswordResetConfirmClient
from .models import CustomUser, UUIDUser
from .settings import AUTH_TEMPLATES


class RedirectURLMixinTests(TestCase):
    @override_settings(ROOT_URLCONF="auth_tests.urls")
    def test_get_default_redirect_url_next_page(self):
        class RedirectURLView(RedirectURLMixin):
            next_page = "/custom/"

        self.assertEqual(RedirectURLView().get_default_redirect_url(), "/custom/")

    def test_get_default_redirect_url_no_next_page(self):
        msg = "No URL to redirect to. Provide a next_page."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            RedirectURLMixin().get_default_redirect_url()


@override_settings(
    LANGUAGES=[("en", "English")],
    LANGUAGE_CODE="en",
    TEMPLATES=AUTH_TEMPLATES,
    ROOT_URLCONF="auth_tests.urls",
)
class AuthViewsTestCase(TestCase):
    """
    Helper base class for the test classes that follow.
    """

    @classmethod
    def setUpTestData(cls):
        cls.u1 = User.objects.create_user(
            username="testclient", password="password", email="testclient@example.com"
        )
        cls.u3 = User.objects.create_user(
            username="staff", password="password", email="staffmember@example.com"
        )

    def login(self, username="testclient", password="password", url="/login/"):
        response = self.client.post(
            url,
            {
                "username": username,
                "password": password,
            },
        )
        self.assertIn(SESSION_KEY, self.client.session)
        return response

    def logout(self):
        response = self.client.post("/admin/logout/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def assertFormError(self, response, error):
        """Assert that error is found in response.context['form'] errors"""
        form_errors = list(itertools.chain(*response.context["form"].errors.values()))
        self.assertIn(str(error), form_errors)


@override_settings(ROOT_URLCONF="django.contrib.auth.urls")
class AuthViewNamedURLTests(AuthViewsTestCase):
    def test_named_urls(self):
        "Named URLs should be reversible"
        expected_named_urls = [
            ("login", [], {}),
            ("logout", [], {}),
            ("password_change", [], {}),
            ("password_change_done", [], {}),
            ("password_reset", [], {}),
            ("password_reset_done", [], {}),
            (
                "password_reset_confirm",
                [],
                {
                    "uidb64": "aaaaaaa",
                    "token": "1111-aaaaa",
                },
            ),
            ("password_reset_complete", [], {}),
        ]
        for name, args, kwargs in expected_named_urls:
            with self.subTest(name=name):
                try:
                    reverse(name, args=args, kwargs=kwargs)
                except NoReverseMatch:
                    self.fail(
                        "Reversal of url named '%s' failed with NoReverseMatch" % name
                    )


class PasswordResetTest(AuthViewsTestCase):
    def setUp(self):
        self.client = PasswordResetConfirmClient()

    def test_email_not_found(self):
        """If the provided email is not registered, don't raise any error but
        also don't send any email."""
        response = self.client.get("/password_reset/")
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            "/password_reset/", {"email": "not_a_real_email@email.com"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_found(self):
        "Email is sent if a valid email address is provided for password reset"
        response = self.client.post(
            "/password_reset/", {"email": "staffmember@example.com"}
        )
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
            "/password_reset_extra_email_context/",
            {"email": "staffmember@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Email email context: "Hello!"', mail.outbox[0].body)
        self.assertIn("http://custom.example.com/reset/", mail.outbox[0].body)

    def test_html_mail_template(self):
        """
        A multipart email with text/plain and text/html is sent
        if the html_email_template parameter is passed to the view
        """
        response = self.client.post(
            "/password_reset/html_email_template/", {"email": "staffmember@example.com"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0].message()
        self.assertEqual(len(message.get_payload()), 2)
        self.assertTrue(message.is_multipart())
        self.assertEqual(message.get_payload(0).get_content_type(), "text/plain")
        self.assertEqual(message.get_payload(1).get_content_type(), "text/html")
        self.assertNotIn("<html>", message.get_payload(0).get_payload())
        self.assertIn("<html>", message.get_payload(1).get_payload())

    def test_email_found_custom_from(self):
        """
        Email is sent if a valid email address is provided for password reset
        when a custom from_email is provided.
        """
        response = self.client.post(
            "/password_reset_from_email/", {"email": "staffmember@example.com"}
        )
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
        with self.assertLogs("django.security.DisallowedHost", "ERROR"):
            response = self.client.post(
                "/password_reset/",
                {"email": "staffmember@example.com"},
                headers={"host": "www.example:dr.frankenstein@evil.tld"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    # Skip any 500 handler action (like sending more mail...)
    @override_settings(DEBUG_PROPAGATE_EXCEPTIONS=True)
    def test_poisoned_http_host_admin_site(self):
        "Poisoned HTTP_HOST headers can't be used for reset emails on admin views"
        with self.assertLogs("django.security.DisallowedHost", "ERROR"):
            response = self.client.post(
                "/admin_password_reset/",
                {"email": "staffmember@example.com"},
                headers={"host": "www.example:dr.frankenstein@evil.tld"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def _test_confirm_start(self):
        # Start by creating the email
        self.client.post("/password_reset/", {"email": "staffmember@example.com"})
        self.assertEqual(len(mail.outbox), 1)
        return self._read_signup_email(mail.outbox[0])

    def _read_signup_email(self, email):
        urlmatch = re.search(r"https?://[^/]*(/.*reset/\S*)", email.body)
        self.assertIsNotNone(urlmatch, "No URL found in sent email")
        return urlmatch[0], urlmatch[1]

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
        # A nonexistent user returns a 200 response, not a 404.
        response = self.client.get("/reset/123456/1-1/")
        self.assertContains(response, "The password reset link was invalid")

    def test_confirm_overflow_user(self):
        # A base36 user id that overflows int returns a 200 response.
        response = self.client.get("/reset/zzzzzzzzzzzzz/1-1/")
        self.assertContains(response, "The password reset link was invalid")

    def test_confirm_invalid_post(self):
        # Same as test_confirm_invalid, but trying to do a POST instead.
        url, path = self._test_confirm_start()
        path = path[:-5] + ("0" * 4) + path[-1]

        self.client.post(
            path,
            {
                "new_password1": "anewpassword",
                "new_password2": " anewpassword",
            },
        )
        # Check the password has not been changed
        u = User.objects.get(email="staffmember@example.com")
        self.assertTrue(not u.check_password("anewpassword"))

    def test_confirm_invalid_hash(self):
        """A POST with an invalid token is rejected."""
        u = User.objects.get(email="staffmember@example.com")
        original_password = u.password
        url, path = self._test_confirm_start()
        path_parts = path.split("-")
        path_parts[-1] = ("0") * 20 + "/"
        path = "-".join(path_parts)

        response = self.client.post(
            path,
            {
                "new_password1": "anewpassword",
                "new_password2": "anewpassword",
            },
        )
        self.assertIs(response.context["validlink"], False)
        u.refresh_from_db()
        self.assertEqual(original_password, u.password)  # password hasn't changed

    def test_confirm_complete(self):
        url, path = self._test_confirm_start()
        response = self.client.post(
            path, {"new_password1": "anewpassword", "new_password2": "anewpassword"}
        )
        # Check the password has been changed
        u = User.objects.get(email="staffmember@example.com")
        self.assertTrue(u.check_password("anewpassword"))
        # The reset token is deleted from the session.
        self.assertNotIn(INTERNAL_RESET_SESSION_TOKEN, self.client.session)

        # Check we can't use the link again
        response = self.client.get(path)
        self.assertContains(response, "The password reset link was invalid")

    def test_confirm_different_passwords(self):
        url, path = self._test_confirm_start()
        response = self.client.post(
            path, {"new_password1": "anewpassword", "new_password2": "x"}
        )
        self.assertFormError(
            response, SetPasswordForm.error_messages["password_mismatch"]
        )

    def test_reset_redirect_default(self):
        response = self.client.post(
            "/password_reset/", {"email": "staffmember@example.com"}
        )
        self.assertRedirects(
            response, "/password_reset/done/", fetch_redirect_response=False
        )

    def test_reset_custom_redirect(self):
        response = self.client.post(
            "/password_reset/custom_redirect/", {"email": "staffmember@example.com"}
        )
        self.assertRedirects(response, "/custom/", fetch_redirect_response=False)

    def test_reset_custom_redirect_named(self):
        response = self.client.post(
            "/password_reset/custom_redirect/named/",
            {"email": "staffmember@example.com"},
        )
        self.assertRedirects(
            response, "/password_reset/", fetch_redirect_response=False
        )

    def test_confirm_redirect_default(self):
        url, path = self._test_confirm_start()
        response = self.client.post(
            path, {"new_password1": "anewpassword", "new_password2": "anewpassword"}
        )
        self.assertRedirects(response, "/reset/done/", fetch_redirect_response=False)

    def test_confirm_redirect_custom(self):
        url, path = self._test_confirm_start()
        path = path.replace("/reset/", "/reset/custom/")
        response = self.client.post(
            path, {"new_password1": "anewpassword", "new_password2": "anewpassword"}
        )
        self.assertRedirects(response, "/custom/", fetch_redirect_response=False)

    def test_confirm_redirect_custom_named(self):
        url, path = self._test_confirm_start()
        path = path.replace("/reset/", "/reset/custom/named/")
        response = self.client.post(
            path, {"new_password1": "anewpassword", "new_password2": "anewpassword"}
        )
        self.assertRedirects(
            response, "/password_reset/", fetch_redirect_response=False
        )

    def test_confirm_custom_reset_url_token(self):
        url, path = self._test_confirm_start()
        path = path.replace("/reset/", "/reset/custom/token/")
        self.client.reset_url_token = "set-passwordcustom"
        response = self.client.post(
            path,
            {"new_password1": "anewpassword", "new_password2": "anewpassword"},
        )
        self.assertRedirects(response, "/reset/done/", fetch_redirect_response=False)

    def test_confirm_login_post_reset(self):
        url, path = self._test_confirm_start()
        path = path.replace("/reset/", "/reset/post_reset_login/")
        response = self.client.post(
            path, {"new_password1": "anewpassword", "new_password2": "anewpassword"}
        )
        self.assertRedirects(response, "/reset/done/", fetch_redirect_response=False)
        self.assertIn(SESSION_KEY, self.client.session)

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.ModelBackend",
            "django.contrib.auth.backends.AllowAllUsersModelBackend",
        ]
    )
    def test_confirm_login_post_reset_custom_backend(self):
        # This backend is specified in the URL pattern.
        backend = "django.contrib.auth.backends.AllowAllUsersModelBackend"
        url, path = self._test_confirm_start()
        path = path.replace("/reset/", "/reset/post_reset_login_custom_backend/")
        response = self.client.post(
            path, {"new_password1": "anewpassword", "new_password2": "anewpassword"}
        )
        self.assertRedirects(response, "/reset/done/", fetch_redirect_response=False)
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertEqual(self.client.session[BACKEND_SESSION_KEY], backend)

    def test_confirm_login_post_reset_already_logged_in(self):
        url, path = self._test_confirm_start()
        path = path.replace("/reset/", "/reset/post_reset_login/")
        self.login()
        response = self.client.post(
            path, {"new_password1": "anewpassword", "new_password2": "anewpassword"}
        )
        self.assertRedirects(response, "/reset/done/", fetch_redirect_response=False)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_confirm_display_user_from_form(self):
        url, path = self._test_confirm_start()
        response = self.client.get(path)
        # The password_reset_confirm() view passes the user object to the
        # SetPasswordForm``, even on GET requests (#16919). For this test,
        # {{ form.user }}`` is rendered in the template
        # registration/password_reset_confirm.html.
        username = User.objects.get(email="staffmember@example.com").username
        self.assertContains(response, "Hello, %s." % username)
        # However, the view should NOT pass any user object on a form if the
        # password reset link was invalid.
        response = self.client.get("/reset/zzzzzzzzzzzzz/1-1/")
        self.assertContains(response, "Hello, .")

    def test_confirm_link_redirects_to_set_password_page(self):
        url, path = self._test_confirm_start()
        # Don't use PasswordResetConfirmClient (self.client) here which
        # automatically fetches the redirect page.
        client = Client()
        response = client.get(path)
        token = response.resolver_match.kwargs["token"]
        uuidb64 = response.resolver_match.kwargs["uidb64"]
        self.assertRedirects(response, "/reset/%s/set-password/" % uuidb64)
        self.assertEqual(client.session["_password_reset_token"], token)

    def test_confirm_custom_reset_url_token_link_redirects_to_set_password_page(self):
        url, path = self._test_confirm_start()
        path = path.replace("/reset/", "/reset/custom/token/")
        client = Client()
        response = client.get(path)
        token = response.resolver_match.kwargs["token"]
        uuidb64 = response.resolver_match.kwargs["uidb64"]
        self.assertRedirects(
            response, "/reset/custom/token/%s/set-passwordcustom/" % uuidb64
        )
        self.assertEqual(client.session["_password_reset_token"], token)

    def test_invalid_link_if_going_directly_to_the_final_reset_password_url(self):
        url, path = self._test_confirm_start()
        _, uuidb64, _ = path.strip("/").split("/")
        response = Client().get("/reset/%s/set-password/" % uuidb64)
        self.assertContains(response, "The password reset link was invalid")

    def test_missing_kwargs(self):
        msg = "The URL path must contain 'uidb64' and 'token' parameters."
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.client.get("/reset/missing_parameters/")

    @modify_settings(
        MIDDLEWARE={"append": "django.contrib.auth.middleware.LoginRequiredMiddleware"}
    )
    def test_access_under_login_required_middleware(self):
        reset_urls = [
            reverse("password_reset"),
            reverse("password_reset_done"),
            reverse("password_reset_confirm", kwargs={"uidb64": "abc", "token": "def"}),
            reverse("password_reset_complete"),
        ]

        for url in reset_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/password_reset/", {"email": "staffmember@example.com"}
        )
        self.assertRedirects(
            response, "/password_reset/done/", fetch_redirect_response=False
        )


@override_settings(AUTH_USER_MODEL="auth_tests.CustomUser")
class CustomUserPasswordResetTest(AuthViewsTestCase):
    user_email = "staffmember@example.com"

    @classmethod
    def setUpTestData(cls):
        cls.u1 = CustomUser.custom_objects.create(
            email="staffmember@example.com",
            date_of_birth=datetime.date(1976, 11, 8),
        )
        cls.u1.set_password("password")
        cls.u1.save()

    def setUp(self):
        self.client = PasswordResetConfirmClient()

    def _test_confirm_start(self):
        # Start by creating the email
        response = self.client.post("/password_reset/", {"email": self.user_email})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        return self._read_signup_email(mail.outbox[0])

    def _read_signup_email(self, email):
        urlmatch = re.search(r"https?://[^/]*(/.*reset/\S*)", email.body)
        self.assertIsNotNone(urlmatch, "No URL found in sent email")
        return urlmatch[0], urlmatch[1]

    def test_confirm_valid_custom_user(self):
        url, path = self._test_confirm_start()
        response = self.client.get(path)
        # redirect to a 'complete' page:
        self.assertContains(response, "Please enter your new password")
        # then submit a new password
        response = self.client.post(
            path,
            {
                "new_password1": "anewpassword",
                "new_password2": "anewpassword",
            },
        )
        self.assertRedirects(response, "/reset/done/")


@override_settings(AUTH_USER_MODEL="auth_tests.UUIDUser")
class UUIDUserPasswordResetTest(CustomUserPasswordResetTest):
    def _test_confirm_start(self):
        # instead of fixture
        UUIDUser.objects.create_user(
            email=self.user_email,
            username="foo",
            password="foo",
        )
        return super()._test_confirm_start()

    def test_confirm_invalid_uuid(self):
        """A uidb64 that decodes to a non-UUID doesn't crash."""
        _, path = self._test_confirm_start()
        invalid_uidb64 = urlsafe_base64_encode(b"INVALID_UUID")
        first, _uuidb64_, second = path.strip("/").split("/")
        response = self.client.get(
            "/" + "/".join((first, invalid_uidb64, second)) + "/"
        )
        self.assertContains(response, "The password reset link was invalid")


class ChangePasswordTest(AuthViewsTestCase):
    def fail_login(self):
        response = self.client.post(
            "/login/",
            {
                "username": "testclient",
                "password": "password",
            },
        )
        self.assertFormError(
            response,
            AuthenticationForm.error_messages["invalid_login"]
            % {"username": User._meta.get_field("username").verbose_name},
        )

    def logout(self):
        self.client.post("/logout/")

    def test_password_change_fails_with_invalid_old_password(self):
        self.login()
        response = self.client.post(
            "/password_change/",
            {
                "old_password": "donuts",
                "new_password1": "password1",
                "new_password2": "password1",
            },
        )
        self.assertFormError(
            response, PasswordChangeForm.error_messages["password_incorrect"]
        )

    def test_password_change_fails_with_mismatched_passwords(self):
        self.login()
        response = self.client.post(
            "/password_change/",
            {
                "old_password": "password",
                "new_password1": "password1",
                "new_password2": "donuts",
            },
        )
        self.assertFormError(
            response, SetPasswordForm.error_messages["password_mismatch"]
        )

    def test_password_change_succeeds(self):
        self.login()
        self.client.post(
            "/password_change/",
            {
                "old_password": "password",
                "new_password1": "password1",
                "new_password2": "password1",
            },
        )
        self.fail_login()
        self.login(password="password1")

    def test_password_change_done_succeeds(self):
        self.login()
        response = self.client.post(
            "/password_change/",
            {
                "old_password": "password",
                "new_password1": "password1",
                "new_password2": "password1",
            },
        )
        self.assertRedirects(
            response, "/password_change/done/", fetch_redirect_response=False
        )

    @override_settings(LOGIN_URL="/login/")
    def test_password_change_done_fails(self):
        response = self.client.get("/password_change/done/")
        self.assertRedirects(
            response,
            "/login/?next=/password_change/done/",
            fetch_redirect_response=False,
        )

    def test_password_change_redirect_default(self):
        self.login()
        response = self.client.post(
            "/password_change/",
            {
                "old_password": "password",
                "new_password1": "password1",
                "new_password2": "password1",
            },
        )
        self.assertRedirects(
            response, "/password_change/done/", fetch_redirect_response=False
        )

    def test_password_change_redirect_custom(self):
        self.login()
        response = self.client.post(
            "/password_change/custom/",
            {
                "old_password": "password",
                "new_password1": "password1",
                "new_password2": "password1",
            },
        )
        self.assertRedirects(response, "/custom/", fetch_redirect_response=False)

    def test_password_change_redirect_custom_named(self):
        self.login()
        response = self.client.post(
            "/password_change/custom/named/",
            {
                "old_password": "password",
                "new_password1": "password1",
                "new_password2": "password1",
            },
        )
        self.assertRedirects(
            response, "/password_reset/", fetch_redirect_response=False
        )

    @modify_settings(
        MIDDLEWARE={"append": "django.contrib.auth.middleware.LoginRequiredMiddleware"}
    )
    def test_access_under_login_required_middleware(self):
        response = self.client.post(
            "/password_change/",
            {
                "old_password": "password",
                "new_password1": "password1",
                "new_password2": "password1",
            },
        )
        self.assertRedirects(
            response,
            settings.LOGIN_URL + "?next=/password_change/",
            fetch_redirect_response=False,
        )

        self.login()

        response = self.client.post(
            "/password_change/",
            {
                "old_password": "password",
                "new_password1": "password1",
                "new_password2": "password1",
            },
        )
        self.assertRedirects(
            response, "/password_change/done/", fetch_redirect_response=False
        )


class SessionAuthenticationTests(AuthViewsTestCase):
    def test_user_password_change_updates_session(self):
        """
        #21649 - Ensure contrib.auth.views.password_change updates the user's
        session auth hash after a password change so the session isn't logged out.
        """
        self.login()
        original_session_key = self.client.session.session_key
        response = self.client.post(
            "/password_change/",
            {
                "old_password": "password",
                "new_password1": "password1",
                "new_password2": "password1",
            },
        )
        # if the hash isn't updated, retrieving the redirection page will fail.
        self.assertRedirects(response, "/password_change/done/")
        # The session key is rotated.
        self.assertNotEqual(original_session_key, self.client.session.session_key)


class LoginTest(AuthViewsTestCase):
    def test_current_site_in_context_after_login(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        if apps.is_installed("django.contrib.sites"):
            Site = apps.get_model("sites.Site")
            site = Site.objects.get_current()
            self.assertEqual(response.context["site"], site)
            self.assertEqual(response.context["site_name"], site.name)
        else:
            self.assertIsInstance(response.context["site"], RequestSite)
        self.assertIsInstance(response.context["form"], AuthenticationForm)

    def test_security_check(self):
        login_url = reverse("login")

        # These URLs should not pass the security check.
        bad_urls = (
            "http://example.com",
            "http:///example.com",
            "https://example.com",
            "ftp://example.com",
            "///example.com",
            "//example.com",
            'javascript:alert("XSS")',
        )
        for bad_url in bad_urls:
            with self.subTest(bad_url=bad_url):
                nasty_url = "%(url)s?%(next)s=%(bad_url)s" % {
                    "url": login_url,
                    "next": REDIRECT_FIELD_NAME,
                    "bad_url": quote(bad_url),
                }
                response = self.client.post(
                    nasty_url,
                    {
                        "username": "testclient",
                        "password": "password",
                    },
                )
                self.assertEqual(response.status_code, 302)
                self.assertNotIn(
                    bad_url, response.url, "%s should be blocked" % bad_url
                )

        # These URLs should pass the security check.
        good_urls = (
            "/view/?param=http://example.com",
            "/view/?param=https://example.com",
            "/view?param=ftp://example.com",
            "view/?param=//example.com",
            "https://testserver/",
            "HTTPS://testserver/",
            "//testserver/",
            "/url%20with%20spaces/",
        )
        for good_url in good_urls:
            with self.subTest(good_url=good_url):
                safe_url = "%(url)s?%(next)s=%(good_url)s" % {
                    "url": login_url,
                    "next": REDIRECT_FIELD_NAME,
                    "good_url": quote(good_url),
                }
                response = self.client.post(
                    safe_url,
                    {
                        "username": "testclient",
                        "password": "password",
                    },
                )
                self.assertEqual(response.status_code, 302)
                self.assertIn(good_url, response.url, "%s should be allowed" % good_url)

    def test_security_check_https(self):
        login_url = reverse("login")
        non_https_next_url = "http://testserver/path"
        not_secured_url = "%(url)s?%(next)s=%(next_url)s" % {
            "url": login_url,
            "next": REDIRECT_FIELD_NAME,
            "next_url": quote(non_https_next_url),
        }
        post_data = {
            "username": "testclient",
            "password": "password",
        }
        response = self.client.post(not_secured_url, post_data, secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, non_https_next_url)
        self.assertEqual(response.url, settings.LOGIN_REDIRECT_URL)

    def test_login_form_contains_request(self):
        # The custom authentication form for this login requires a request to
        # initialize it.
        response = self.client.post(
            "/custom_request_auth_login/",
            {
                "username": "testclient",
                "password": "password",
            },
        )
        # The login was successful.
        self.assertRedirects(
            response, settings.LOGIN_REDIRECT_URL, fetch_redirect_response=False
        )

    def test_login_csrf_rotate(self):
        """
        Makes sure that a login rotates the currently-used CSRF token.
        """

        def get_response(request):
            return HttpResponse()

        # Do a GET to establish a CSRF token
        # The test client isn't used here as it's a test for middleware.
        req = HttpRequest()
        CsrfViewMiddleware(get_response).process_view(req, LoginView.as_view(), (), {})
        # get_token() triggers CSRF token inclusion in the response
        get_token(req)
        resp = CsrfViewMiddleware(LoginView.as_view())(req)
        csrf_cookie = resp.cookies.get(settings.CSRF_COOKIE_NAME, None)
        token1 = csrf_cookie.coded_value

        # Prepare the POST request
        req = HttpRequest()
        req.COOKIES[settings.CSRF_COOKIE_NAME] = token1
        req.method = "POST"
        req.POST = {
            "username": "testclient",
            "password": "password",
            "csrfmiddlewaretoken": token1,
        }

        # Use POST request to log in
        SessionMiddleware(get_response).process_request(req)
        CsrfViewMiddleware(get_response).process_view(req, LoginView.as_view(), (), {})
        req.META["SERVER_NAME"] = (
            "testserver"  # Required to have redirect work in login view
        )
        req.META["SERVER_PORT"] = 80
        resp = CsrfViewMiddleware(LoginView.as_view())(req)
        csrf_cookie = resp.cookies.get(settings.CSRF_COOKIE_NAME, None)
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

        self.login(username="staff")
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

        user = User.objects.get(username="testclient")
        user.set_password("foobar")
        user.save()

        self.login(password="foobar")
        self.assertNotEqual(original_session_key, self.client.session.session_key)

    def test_login_session_without_hash_session_key(self):
        """
        Session without django.contrib.auth.HASH_SESSION_KEY should login
        without an exception.
        """
        user = User.objects.get(username="testclient")
        engine = import_module(settings.SESSION_ENGINE)
        session = engine.SessionStore()
        session[SESSION_KEY] = user.id
        session.save()
        original_session_key = session.session_key
        self.client.cookies[settings.SESSION_COOKIE_NAME] = original_session_key

        self.login()
        self.assertNotEqual(original_session_key, self.client.session.session_key)

    def test_login_get_default_redirect_url(self):
        response = self.login(url="/login/get_default_redirect_url/")
        self.assertRedirects(response, "/custom/", fetch_redirect_response=False)

    def test_login_next_page(self):
        response = self.login(url="/login/next_page/")
        self.assertRedirects(response, "/somewhere/", fetch_redirect_response=False)

    def test_login_named_next_page_named(self):
        response = self.login(url="/login/next_page/named/")
        self.assertRedirects(
            response, "/password_reset/", fetch_redirect_response=False
        )

    @override_settings(LOGIN_REDIRECT_URL="/custom/")
    def test_login_next_page_overrides_login_redirect_url_setting(self):
        response = self.login(url="/login/next_page/")
        self.assertRedirects(response, "/somewhere/", fetch_redirect_response=False)

    def test_login_redirect_url_overrides_next_page(self):
        response = self.login(url="/login/next_page/?next=/test/")
        self.assertRedirects(response, "/test/", fetch_redirect_response=False)

    def test_login_redirect_url_overrides_get_default_redirect_url(self):
        response = self.login(url="/login/get_default_redirect_url/?next=/test/")
        self.assertRedirects(response, "/test/", fetch_redirect_response=False)

    @modify_settings(
        MIDDLEWARE={"append": "django.contrib.auth.middleware.LoginRequiredMiddleware"}
    )
    def test_access_under_login_required_middleware(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)


class LoginURLSettings(AuthViewsTestCase):
    """Tests for settings.LOGIN_URL."""

    def assertLoginURLEquals(self, url):
        response = self.client.get("/login_required/")
        self.assertRedirects(response, url, fetch_redirect_response=False)

    @override_settings(LOGIN_URL="/login/")
    def test_standard_login_url(self):
        self.assertLoginURLEquals("/login/?next=/login_required/")

    @override_settings(LOGIN_URL="login")
    def test_named_login_url(self):
        self.assertLoginURLEquals("/login/?next=/login_required/")

    @override_settings(LOGIN_URL="http://remote.example.com/login")
    def test_remote_login_url(self):
        quoted_next = quote("http://testserver/login_required/")
        expected = "http://remote.example.com/login?next=%s" % quoted_next
        self.assertLoginURLEquals(expected)

    @override_settings(LOGIN_URL="https:///login/")
    def test_https_login_url(self):
        quoted_next = quote("http://testserver/login_required/")
        expected = "https:///login/?next=%s" % quoted_next
        self.assertLoginURLEquals(expected)

    @override_settings(LOGIN_URL="/login/?pretty=1")
    def test_login_url_with_querystring(self):
        self.assertLoginURLEquals("/login/?pretty=1&next=/login_required/")

    @override_settings(LOGIN_URL="http://remote.example.com/login/?next=/default/")
    def test_remote_login_url_with_next_querystring(self):
        quoted_next = quote("http://testserver/login_required/")
        expected = "http://remote.example.com/login/?next=%s" % quoted_next
        self.assertLoginURLEquals(expected)

    @override_settings(LOGIN_URL=reverse_lazy("login"))
    def test_lazy_login_url(self):
        self.assertLoginURLEquals("/login/?next=/login_required/")


class LoginRedirectUrlTest(AuthViewsTestCase):
    """Tests for settings.LOGIN_REDIRECT_URL."""

    def assertLoginRedirectURLEqual(self, url):
        response = self.login()
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_default(self):
        self.assertLoginRedirectURLEqual("/accounts/profile/")

    @override_settings(LOGIN_REDIRECT_URL="/custom/")
    def test_custom(self):
        self.assertLoginRedirectURLEqual("/custom/")

    @override_settings(LOGIN_REDIRECT_URL="password_reset")
    def test_named(self):
        self.assertLoginRedirectURLEqual("/password_reset/")

    @override_settings(LOGIN_REDIRECT_URL="http://remote.example.com/welcome/")
    def test_remote(self):
        self.assertLoginRedirectURLEqual("http://remote.example.com/welcome/")


class RedirectToLoginTests(AuthViewsTestCase):
    """Tests for the redirect_to_login view"""

    @override_settings(LOGIN_URL=reverse_lazy("login"))
    def test_redirect_to_login_with_lazy(self):
        login_redirect_response = redirect_to_login(next="/else/where/")
        expected = "/login/?next=/else/where/"
        self.assertEqual(expected, login_redirect_response.url)

    @override_settings(LOGIN_URL=reverse_lazy("login"))
    def test_redirect_to_login_with_lazy_and_unicode(self):
        login_redirect_response = redirect_to_login(next="/else/where/झ/")
        expected = "/login/?next=/else/where/%E0%A4%9D/"
        self.assertEqual(expected, login_redirect_response.url)


class LogoutThenLoginTests(AuthViewsTestCase):
    """Tests for the logout_then_login view"""

    def confirm_logged_out(self):
        self.assertNotIn(SESSION_KEY, self.client.session)

    @override_settings(LOGIN_URL="/login/")
    def test_default_logout_then_login(self):
        self.login()
        req = HttpRequest()
        req.method = "POST"
        csrf_token = get_token(req)
        req.COOKIES[settings.CSRF_COOKIE_NAME] = csrf_token
        req.POST = {"csrfmiddlewaretoken": csrf_token}
        req.META["SERVER_NAME"] = "testserver"
        req.META["SERVER_PORT"] = 80
        req.session = self.client.session
        response = logout_then_login(req)
        self.confirm_logged_out()
        self.assertRedirects(response, "/login/", fetch_redirect_response=False)

    def test_logout_then_login_with_custom_login(self):
        self.login()
        req = HttpRequest()
        req.method = "POST"
        csrf_token = get_token(req)
        req.COOKIES[settings.CSRF_COOKIE_NAME] = csrf_token
        req.POST = {"csrfmiddlewaretoken": csrf_token}
        req.META["SERVER_NAME"] = "testserver"
        req.META["SERVER_PORT"] = 80
        req.session = self.client.session
        response = logout_then_login(req, login_url="/custom/")
        self.confirm_logged_out()
        self.assertRedirects(response, "/custom/", fetch_redirect_response=False)

    @override_settings(LOGIN_URL="/login/")
    def test_default_logout_then_login_get(self):
        self.login()
        req = HttpRequest()
        req.method = "GET"
        req.META["SERVER_NAME"] = "testserver"
        req.META["SERVER_PORT"] = 80
        req.session = self.client.session
        response = logout_then_login(req)
        self.assertEqual(response.status_code, 405)


class LoginRedirectAuthenticatedUser(AuthViewsTestCase):
    dont_redirect_url = "/login/redirect_authenticated_user_default/"
    do_redirect_url = "/login/redirect_authenticated_user/"

    def test_default(self):
        """Stay on the login page by default."""
        self.login()
        response = self.client.get(self.dont_redirect_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["next"], "")

    def test_guest(self):
        """If not logged in, stay on the same page."""
        response = self.client.get(self.do_redirect_url)
        self.assertEqual(response.status_code, 200)

    def test_redirect(self):
        """If logged in, go to default redirected URL."""
        self.login()
        response = self.client.get(self.do_redirect_url)
        self.assertRedirects(
            response, "/accounts/profile/", fetch_redirect_response=False
        )

    @override_settings(LOGIN_REDIRECT_URL="/custom/")
    def test_redirect_url(self):
        """If logged in, go to custom redirected URL."""
        self.login()
        response = self.client.get(self.do_redirect_url)
        self.assertRedirects(response, "/custom/", fetch_redirect_response=False)

    def test_redirect_param(self):
        """If next is specified as a GET parameter, go there."""
        self.login()
        url = self.do_redirect_url + "?next=/custom_next/"
        response = self.client.get(url)
        self.assertRedirects(response, "/custom_next/", fetch_redirect_response=False)

    def test_redirect_loop(self):
        """
        Detect a redirect loop if LOGIN_REDIRECT_URL is not correctly set,
        with and without custom parameters.
        """
        self.login()
        msg = (
            "Redirection loop for authenticated user detected. Check that "
            "your LOGIN_REDIRECT_URL doesn't point to a login page."
        )
        with self.settings(LOGIN_REDIRECT_URL=self.do_redirect_url):
            with self.assertRaisesMessage(ValueError, msg):
                self.client.get(self.do_redirect_url)

            url = self.do_redirect_url + "?bla=2"
            with self.assertRaisesMessage(ValueError, msg):
                self.client.get(url)

    def test_permission_required_not_logged_in(self):
        # Not logged in ...
        with self.settings(LOGIN_URL=self.do_redirect_url):
            # redirected to login.
            response = self.client.get("/permission_required_redirect/", follow=True)
            self.assertEqual(response.status_code, 200)
            # exception raised.
            response = self.client.get("/permission_required_exception/", follow=True)
            self.assertEqual(response.status_code, 403)
            # redirected to login.
            response = self.client.get(
                "/login_and_permission_required_exception/", follow=True
            )
            self.assertEqual(response.status_code, 200)

    def test_permission_required_logged_in(self):
        self.login()
        # Already logged in...
        with self.settings(LOGIN_URL=self.do_redirect_url):
            # redirect loop encountered.
            with self.assertRaisesMessage(
                RedirectCycleError, "Redirect loop detected."
            ):
                self.client.get("/permission_required_redirect/", follow=True)
            # exception raised.
            response = self.client.get("/permission_required_exception/", follow=True)
            self.assertEqual(response.status_code, 403)
            # exception raised.
            response = self.client.get(
                "/login_and_permission_required_exception/", follow=True
            )
            self.assertEqual(response.status_code, 403)


class LoginSuccessURLAllowedHostsTest(AuthViewsTestCase):
    def test_success_url_allowed_hosts_same_host(self):
        response = self.client.post(
            "/login/allowed_hosts/",
            {
                "username": "testclient",
                "password": "password",
                "next": "https://testserver/home",
            },
        )
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertRedirects(
            response, "https://testserver/home", fetch_redirect_response=False
        )

    def test_success_url_allowed_hosts_safe_host(self):
        response = self.client.post(
            "/login/allowed_hosts/",
            {
                "username": "testclient",
                "password": "password",
                "next": "https://otherserver/home",
            },
        )
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertRedirects(
            response, "https://otherserver/home", fetch_redirect_response=False
        )

    def test_success_url_allowed_hosts_unsafe_host(self):
        response = self.client.post(
            "/login/allowed_hosts/",
            {
                "username": "testclient",
                "password": "password",
                "next": "https://evil/home",
            },
        )
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertRedirects(
            response, "/accounts/profile/", fetch_redirect_response=False
        )


class LogoutTest(AuthViewsTestCase):
    def confirm_logged_out(self):
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_default(self):
        "Logout without next_page option renders the default template"
        self.login()
        response = self.client.post("/logout/")
        self.assertContains(response, "Logged out")
        self.confirm_logged_out()

    def test_logout_with_post(self):
        self.login()
        response = self.client.post("/logout/")
        self.assertContains(response, "Logged out")
        self.confirm_logged_out()

    def test_14377(self):
        # Bug 14377
        self.login()
        response = self.client.post("/logout/")
        self.assertIn("site", response.context)

    def test_logout_doesnt_cache(self):
        """
        The logout() view should send "no-cache" headers for reasons described
        in #25490.
        """
        response = self.client.post("/logout/")
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_logout_with_overridden_redirect_url(self):
        # Bug 11223
        self.login()
        response = self.client.post("/logout/next_page/")
        self.assertRedirects(response, "/somewhere/", fetch_redirect_response=False)

        response = self.client.post("/logout/next_page/?next=/login/")
        self.assertRedirects(response, "/login/", fetch_redirect_response=False)

        self.confirm_logged_out()

    def test_logout_with_next_page_specified(self):
        "Logout with next_page option given redirects to specified resource"
        self.login()
        response = self.client.post("/logout/next_page/")
        self.assertRedirects(response, "/somewhere/", fetch_redirect_response=False)
        self.confirm_logged_out()

    def test_logout_with_redirect_argument(self):
        "Logout with query string redirects to specified resource"
        self.login()
        response = self.client.post("/logout/?next=/login/")
        self.assertRedirects(response, "/login/", fetch_redirect_response=False)
        self.confirm_logged_out()

    def test_logout_with_custom_redirect_argument(self):
        "Logout with custom query string redirects to specified resource"
        self.login()
        response = self.client.post("/logout/custom_query/?follow=/somewhere/")
        self.assertRedirects(response, "/somewhere/", fetch_redirect_response=False)
        self.confirm_logged_out()

    def test_logout_with_named_redirect(self):
        "Logout resolves names or URLs passed as next_page."
        self.login()
        response = self.client.post("/logout/next_page/named/")
        self.assertRedirects(
            response, "/password_reset/", fetch_redirect_response=False
        )
        self.confirm_logged_out()

    def test_success_url_allowed_hosts_same_host(self):
        self.login()
        response = self.client.post("/logout/allowed_hosts/?next=https://testserver/")
        self.assertRedirects(
            response, "https://testserver/", fetch_redirect_response=False
        )
        self.confirm_logged_out()

    def test_success_url_allowed_hosts_safe_host(self):
        self.login()
        response = self.client.post("/logout/allowed_hosts/?next=https://otherserver/")
        self.assertRedirects(
            response, "https://otherserver/", fetch_redirect_response=False
        )
        self.confirm_logged_out()

    def test_success_url_allowed_hosts_unsafe_host(self):
        self.login()
        response = self.client.post("/logout/allowed_hosts/?next=https://evil/")
        self.assertRedirects(
            response, "/logout/allowed_hosts/", fetch_redirect_response=False
        )
        self.confirm_logged_out()

    def test_security_check(self):
        logout_url = reverse("logout")

        # These URLs should not pass the security check.
        bad_urls = (
            "http://example.com",
            "http:///example.com",
            "https://example.com",
            "ftp://example.com",
            "///example.com",
            "//example.com",
            'javascript:alert("XSS")',
        )
        for bad_url in bad_urls:
            with self.subTest(bad_url=bad_url):
                nasty_url = "%(url)s?%(next)s=%(bad_url)s" % {
                    "url": logout_url,
                    "next": REDIRECT_FIELD_NAME,
                    "bad_url": quote(bad_url),
                }
                self.login()
                response = self.client.post(nasty_url)
                self.assertEqual(response.status_code, 302)
                self.assertNotIn(
                    bad_url, response.url, "%s should be blocked" % bad_url
                )
                self.confirm_logged_out()

        # These URLs should pass the security check.
        good_urls = (
            "/view/?param=http://example.com",
            "/view/?param=https://example.com",
            "/view?param=ftp://example.com",
            "view/?param=//example.com",
            "https://testserver/",
            "HTTPS://testserver/",
            "//testserver/",
            "/url%20with%20spaces/",
        )
        for good_url in good_urls:
            with self.subTest(good_url=good_url):
                safe_url = "%(url)s?%(next)s=%(good_url)s" % {
                    "url": logout_url,
                    "next": REDIRECT_FIELD_NAME,
                    "good_url": quote(good_url),
                }
                self.login()
                response = self.client.post(safe_url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(good_url, response.url, "%s should be allowed" % good_url)
                self.confirm_logged_out()

    def test_security_check_https(self):
        logout_url = reverse("logout")
        non_https_next_url = "http://testserver/"
        url = "%(url)s?%(next)s=%(next_url)s" % {
            "url": logout_url,
            "next": REDIRECT_FIELD_NAME,
            "next_url": quote(non_https_next_url),
        }
        self.login()
        response = self.client.post(url, secure=True)
        self.assertRedirects(response, logout_url, fetch_redirect_response=False)
        self.confirm_logged_out()

    def test_logout_preserve_language(self):
        """Language is preserved after logout."""
        self.login()
        self.client.post("/setlang/", {"language": "pl"})
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, "pl")
        self.client.post("/logout/")
        self.assertEqual(self.client.cookies[settings.LANGUAGE_COOKIE_NAME].value, "pl")

    @override_settings(LOGOUT_REDIRECT_URL="/custom/")
    def test_logout_redirect_url_setting(self):
        self.login()
        response = self.client.post("/logout/")
        self.assertRedirects(response, "/custom/", fetch_redirect_response=False)

    @override_settings(LOGOUT_REDIRECT_URL="/custom/")
    def test_logout_redirect_url_setting_allowed_hosts_unsafe_host(self):
        self.login()
        response = self.client.post("/logout/allowed_hosts/?next=https://evil/")
        self.assertRedirects(response, "/custom/", fetch_redirect_response=False)

    @override_settings(LOGOUT_REDIRECT_URL="logout")
    def test_logout_redirect_url_named_setting(self):
        self.login()
        response = self.client.post("/logout/")
        self.assertContains(response, "Logged out")
        self.confirm_logged_out()

    @modify_settings(
        MIDDLEWARE={"append": "django.contrib.auth.middleware.LoginRequiredMiddleware"}
    )
    def test_access_under_login_required_middleware(self):
        response = self.client.post("/logout/")
        self.assertRedirects(
            response,
            settings.LOGIN_URL + "?next=/logout/",
            fetch_redirect_response=False,
        )

        self.login()

        response = self.client.post("/logout/")
        self.assertEqual(response.status_code, 200)


def get_perm(Model, perm):
    ct = ContentType.objects.get_for_model(Model)
    return Permission.objects.get(content_type=ct, codename=perm)


# Redirect in test_user_change_password will fail if session auth hash
# isn't updated after password change (#21649)
@override_settings(
    ROOT_URLCONF="auth_tests.urls_admin",
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class ChangelistTests(MessagesTestMixin, AuthViewsTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Make me a superuser before logging in.
        User.objects.filter(username="testclient").update(
            is_staff=True, is_superuser=True
        )

    def setUp(self):
        self.login()
        # Get the latest last_login value.
        self.admin = User.objects.get(pk=self.u1.pk)

    def get_user_data(self, user):
        return {
            "username": user.username,
            "password": user.password,
            "email": user.email,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "last_login_0": user.last_login.strftime("%Y-%m-%d"),
            "last_login_1": user.last_login.strftime("%H:%M:%S"),
            "initial-last_login_0": user.last_login.strftime("%Y-%m-%d"),
            "initial-last_login_1": user.last_login.strftime("%H:%M:%S"),
            "date_joined_0": user.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1": user.date_joined.strftime("%H:%M:%S"),
            "initial-date_joined_0": user.date_joined.strftime("%Y-%m-%d"),
            "initial-date_joined_1": user.date_joined.strftime("%H:%M:%S"),
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

    # #20078 - users shouldn't be allowed to guess password hashes via
    # repeated password__startswith queries.
    def test_changelist_disallows_password_lookups(self):
        # A lookup that tries to filter on password isn't OK
        with self.assertLogs("django.security.DisallowedModelAdminLookup", "ERROR"):
            response = self.client.get(
                reverse("auth_test_admin:auth_user_changelist")
                + "?password__startswith=sha1$"
            )
        self.assertEqual(response.status_code, 400)

    def test_user_change_email(self):
        data = self.get_user_data(self.admin)
        data["email"] = "new_" + data["email"]
        response = self.client.post(
            reverse("auth_test_admin:auth_user_change", args=(self.admin.pk,)), data
        )
        self.assertRedirects(response, reverse("auth_test_admin:auth_user_changelist"))
        row = LogEntry.objects.latest("id")
        self.assertEqual(row.get_change_message(), "Changed Email address.")

    def test_user_not_change(self):
        response = self.client.post(
            reverse("auth_test_admin:auth_user_change", args=(self.admin.pk,)),
            self.get_user_data(self.admin),
        )
        self.assertRedirects(response, reverse("auth_test_admin:auth_user_changelist"))
        row = LogEntry.objects.latest("id")
        self.assertEqual(row.get_change_message(), "No fields changed.")

    def test_user_with_usable_password_change_password(self):
        user_change_url = reverse(
            "auth_test_admin:auth_user_change", args=(self.admin.pk,)
        )
        password_change_url = reverse(
            "auth_test_admin:auth_user_password_change", args=(self.admin.pk,)
        )

        response = self.client.get(user_change_url)
        # Test the link inside password field help_text.
        rel_link = re.search(
            r'<a class="button" href="([^"]*)">Reset password</a>',
            response.text,
        )[1]
        self.assertEqual(urljoin(user_change_url, rel_link), password_change_url)

        response = self.client.get(password_change_url)
        # Test the form title with original (usable) password
        self.assertContains(
            response, f"<h1>Change password: {self.admin.username}</h1>"
        )
        # Breadcrumb.
        self.assertContains(
            response, f"{self.admin.username}</a>\n&rsaquo; Change password"
        )
        # Submit buttons
        self.assertContains(response, '<input type="submit" name="set-password"')
        self.assertContains(response, '<input type="submit" name="unset-password"')

        # Password change.
        response = self.client.post(
            password_change_url,
            {
                "password1": "password1",
                "password2": "password1",
            },
        )
        self.assertRedirects(response, user_change_url)
        self.assertMessages(
            response, [Message(level=25, message="Password changed successfully.")]
        )
        row = LogEntry.objects.latest("id")
        self.assertEqual(row.get_change_message(), "Changed password.")
        self.logout()
        self.login(password="password1")

        # Disable password-based authentication without proper submit button.
        response = self.client.post(
            password_change_url,
            {
                "password1": "password1",
                "password2": "password1",
                "usable_password": "false",
            },
        )
        self.assertRedirects(response, password_change_url)
        self.assertMessages(
            response,
            [
                Message(
                    level=40,
                    message="Conflicting form data submitted. Please try again.",
                )
            ],
        )
        # No password change yet.
        self.login(password="password1")

        # Disable password-based authentication with proper submit button.
        response = self.client.post(
            password_change_url,
            {
                "password1": "password1",
                "password2": "password1",
                "usable_password": "false",
                "unset-password": 1,
            },
        )
        self.assertRedirects(response, user_change_url)
        self.assertMessages(
            response,
            [Message(level=25, message="Password-based authentication was disabled.")],
        )
        row = LogEntry.objects.latest("id")
        self.assertEqual(row.get_change_message(), "Changed password.")
        self.logout()
        # Password-based authentication was disabled.
        with self.assertRaises(AssertionError):
            self.login(password="password1")
        self.admin.refresh_from_db()
        self.assertIs(self.admin.has_usable_password(), False)

    def test_user_with_unusable_password_change_password(self):
        # Test for title with unusable password with a test user
        test_user = User.objects.get(email="staffmember@example.com")
        test_user.set_unusable_password()
        test_user.save()
        user_change_url = reverse(
            "auth_test_admin:auth_user_change", args=(test_user.pk,)
        )
        password_change_url = reverse(
            "auth_test_admin:auth_user_password_change", args=(test_user.pk,)
        )

        response = self.client.get(user_change_url)
        # Test the link inside password field help_text.
        rel_link = re.search(
            r'<a class="button" href="([^"]*)">Set password</a>',
            response.text,
        )[1]
        self.assertEqual(urljoin(user_change_url, rel_link), password_change_url)

        response = self.client.get(password_change_url)
        # Test the form title with original (usable) password
        self.assertContains(response, f"<h1>Set password: {test_user.username}</h1>")
        # Breadcrumb.
        self.assertContains(
            response, f"{test_user.username}</a>\n&rsaquo; Set password"
        )
        # Submit buttons
        self.assertContains(response, '<input type="submit" name="set-password"')
        self.assertNotContains(response, '<input type="submit" name="unset-password"')

        response = self.client.post(
            password_change_url,
            {
                "password1": "password1",
                "password2": "password1",
            },
        )
        self.assertRedirects(response, user_change_url)
        self.assertMessages(
            response, [Message(level=25, message="Password changed successfully.")]
        )
        row = LogEntry.objects.latest("id")
        self.assertEqual(row.get_change_message(), "Changed password.")

    def test_user_change_different_user_password(self):
        u = User.objects.get(email="staffmember@example.com")
        response = self.client.post(
            reverse("auth_test_admin:auth_user_password_change", args=(u.pk,)),
            {
                "password1": "password1",
                "password2": "password1",
            },
        )
        self.assertRedirects(
            response, reverse("auth_test_admin:auth_user_change", args=(u.pk,))
        )
        row = LogEntry.objects.latest("id")
        self.assertEqual(row.user_id, self.admin.pk)
        self.assertEqual(row.object_id, str(u.pk))
        self.assertEqual(row.get_change_message(), "Changed password.")

    def test_password_change_bad_url(self):
        response = self.client.get(
            reverse("auth_test_admin:auth_user_password_change", args=("foobar",))
        )
        self.assertEqual(response.status_code, 404)

    @mock.patch("django.contrib.auth.admin.UserAdmin.has_change_permission")
    def test_user_change_password_passes_user_to_has_change_permission(
        self, has_change_permission
    ):
        url = reverse(
            "auth_test_admin:auth_user_password_change", args=(self.admin.pk,)
        )
        self.client.post(url, {"password1": "password1", "password2": "password1"})
        (_request, user), _kwargs = has_change_permission.call_args
        self.assertEqual(user.pk, self.admin.pk)

    def test_view_user_password_is_readonly(self):
        u = User.objects.get(username="testclient")
        u.is_superuser = False
        u.save()
        original_password = u.password
        u.user_permissions.add(get_perm(User, "view_user"))
        response = self.client.get(
            reverse("auth_test_admin:auth_user_change", args=(u.pk,)),
        )
        algo, salt, hash_string = u.password.split("$")
        self.assertContains(response, '<div class="readonly">testclient</div>')
        # ReadOnlyPasswordHashWidget is used to render the field.
        self.assertContains(
            response,
            "<strong>algorithm</strong>: <bdi>%s</bdi>\n\n"
            "<strong>salt</strong>: <bdi>%s********************</bdi>\n\n"
            "<strong>hash</strong>: <bdi>%s**************************</bdi>\n\n"
            % (
                algo,
                salt[:2],
                hash_string[:6],
            ),
            html=True,
        )
        # Value in POST data is ignored.
        data = self.get_user_data(u)
        data["password"] = "shouldnotchange"
        change_url = reverse("auth_test_admin:auth_user_change", args=(u.pk,))
        response = self.client.post(change_url, data)
        self.assertEqual(response.status_code, 403)
        u.refresh_from_db()
        self.assertEqual(u.password, original_password)


@override_settings(
    AUTH_USER_MODEL="auth_tests.UUIDUser",
    ROOT_URLCONF="auth_tests.urls_custom_user_admin",
)
class UUIDUserTests(TestCase):
    def test_admin_password_change(self):
        u = UUIDUser.objects.create_superuser(
            username="uuid", email="foo@bar.com", password="test"
        )
        self.assertTrue(self.client.login(username="uuid", password="test"))

        user_change_url = reverse(
            "custom_user_admin:auth_tests_uuiduser_change", args=(u.pk,)
        )
        response = self.client.get(user_change_url)
        self.assertEqual(response.status_code, 200)

        password_change_url = reverse(
            "custom_user_admin:auth_user_password_change", args=(u.pk,)
        )
        response = self.client.get(password_change_url)
        # The action attribute is omitted.
        self.assertContains(response, '<form method="post" id="uuiduser_form">')

        # A LogEntry is created with pk=1 which breaks a FK constraint on MySQL
        with connection.constraint_checks_disabled():
            response = self.client.post(
                password_change_url,
                {
                    "password1": "password1",
                    "password2": "password1",
                },
            )
        self.assertRedirects(response, user_change_url)
        row = LogEntry.objects.latest("id")
        self.assertEqual(row.user_id, 1)  # hardcoded in CustomUserAdmin.log_change()
        self.assertEqual(row.object_id, str(u.pk))
        self.assertEqual(row.get_change_message(), "Changed password.")

        # The LogEntry.user column isn't altered to a UUID type so it's set to
        # an integer manually in CustomUserAdmin to avoid an error. To avoid a
        # constraint error, delete the entry before constraints are checked
        # after the test.
        row.delete()
