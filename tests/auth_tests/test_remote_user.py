from datetime import datetime, timezone

from django.conf import settings
from django.contrib.auth import aauthenticate, authenticate
from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.contrib.auth.models import User
from django.middleware.csrf import _get_new_csrf_string, _mask_cipher_secret
from django.test import (
    AsyncClient,
    Client,
    TestCase,
    modify_settings,
    override_settings,
)


@override_settings(ROOT_URLCONF="auth_tests.urls")
class RemoteUserTest(TestCase):
    middleware = "django.contrib.auth.middleware.RemoteUserMiddleware"
    backend = "django.contrib.auth.backends.RemoteUserBackend"
    header = "REMOTE_USER"
    email_header = "REMOTE_EMAIL"

    # Usernames to be passed in REMOTE_USER for the test_known_user test case.
    known_user = "knownuser"
    known_user2 = "knownuser2"

    @classmethod
    def setUpClass(cls):
        cls.enterClassContext(
            modify_settings(
                AUTHENTICATION_BACKENDS={"append": cls.backend},
                MIDDLEWARE={"append": cls.middleware},
            )
        )
        super().setUpClass()

    def test_passing_explicit_none(self):
        msg = "get_response must be provided."
        with self.assertRaisesMessage(ValueError, msg):
            RemoteUserMiddleware(None)

    def test_no_remote_user(self):
        """Users are not created when remote user is not specified."""
        num_users = User.objects.count()

        response = self.client.get("/remote_user/")
        self.assertTrue(response.context["user"].is_anonymous)
        self.assertEqual(User.objects.count(), num_users)

        response = self.client.get("/remote_user/", **{self.header: None})
        self.assertTrue(response.context["user"].is_anonymous)
        self.assertEqual(User.objects.count(), num_users)

        response = self.client.get("/remote_user/", **{self.header: ""})
        self.assertTrue(response.context["user"].is_anonymous)
        self.assertEqual(User.objects.count(), num_users)

    async def test_no_remote_user_async(self):
        """See test_no_remote_user."""
        num_users = await User.objects.acount()

        response = await self.async_client.get("/remote_user/")
        self.assertTrue(response.context["user"].is_anonymous)
        self.assertEqual(await User.objects.acount(), num_users)

        response = await self.async_client.get("/remote_user/", **{self.header: ""})
        self.assertTrue(response.context["user"].is_anonymous)
        self.assertEqual(await User.objects.acount(), num_users)

    def test_csrf_validation_passes_after_process_request_login(self):
        """
        CSRF check must access the CSRF token from the session or cookie,
        rather than the request, as rotate_token() may have been called by an
        authentication middleware during the process_request() phase.
        """
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_secret = _get_new_csrf_string()
        csrf_token = _mask_cipher_secret(csrf_secret)
        csrf_token_form = _mask_cipher_secret(csrf_secret)
        headers = {self.header: "fakeuser"}
        data = {"csrfmiddlewaretoken": csrf_token_form}

        # Verify that CSRF is configured for the view
        csrf_client.cookies.load({settings.CSRF_COOKIE_NAME: csrf_token})
        response = csrf_client.post("/remote_user/", **headers)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"CSRF verification failed.", response.content)

        # This request will call django.contrib.auth.login() which will call
        # django.middleware.csrf.rotate_token() thus changing the value of
        # request.META['CSRF_COOKIE'] from the user submitted value set by
        # CsrfViewMiddleware.process_request() to the new csrftoken value set
        # by rotate_token(). Csrf validation should still pass when the view is
        # later processed by CsrfViewMiddleware.process_view()
        csrf_client.cookies.load({settings.CSRF_COOKIE_NAME: csrf_token})
        response = csrf_client.post("/remote_user/", data, **headers)
        self.assertEqual(response.status_code, 200)

    async def test_csrf_validation_passes_after_process_request_login_async(self):
        """See test_csrf_validation_passes_after_process_request_login."""
        csrf_client = AsyncClient(enforce_csrf_checks=True)
        csrf_secret = _get_new_csrf_string()
        csrf_token = _mask_cipher_secret(csrf_secret)
        csrf_token_form = _mask_cipher_secret(csrf_secret)
        headers = {self.header: "fakeuser"}
        data = {"csrfmiddlewaretoken": csrf_token_form}

        # Verify that CSRF is configured for the view
        csrf_client.cookies.load({settings.CSRF_COOKIE_NAME: csrf_token})
        response = await csrf_client.post("/remote_user/", **headers)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"CSRF verification failed.", response.content)

        # This request will call django.contrib.auth.alogin() which will call
        # django.middleware.csrf.rotate_token() thus changing the value of
        # request.META['CSRF_COOKIE'] from the user submitted value set by
        # CsrfViewMiddleware.process_request() to the new csrftoken value set
        # by rotate_token(). Csrf validation should still pass when the view is
        # later processed by CsrfViewMiddleware.process_view()
        csrf_client.cookies.load({settings.CSRF_COOKIE_NAME: csrf_token})
        response = await csrf_client.post("/remote_user/", data, **headers)
        self.assertEqual(response.status_code, 200)

    def test_unknown_user(self):
        """
        Tests the case where the username passed in the header does not exist
        as a User.
        """
        num_users = User.objects.count()
        response = self.client.get("/remote_user/", **{self.header: "newuser"})
        self.assertEqual(response.context["user"].username, "newuser")
        self.assertEqual(User.objects.count(), num_users + 1)
        User.objects.get(username="newuser")

        # Another request with same user should not create any new users.
        response = self.client.get("/remote_user/", **{self.header: "newuser"})
        self.assertEqual(User.objects.count(), num_users + 1)

    async def test_unknown_user_async(self):
        """See test_unknown_user."""
        num_users = await User.objects.acount()
        response = await self.async_client.get(
            "/remote_user/", **{self.header: "newuser"}
        )
        self.assertEqual(response.context["user"].username, "newuser")
        self.assertEqual(await User.objects.acount(), num_users + 1)
        await User.objects.aget(username="newuser")

        # Another request with same user should not create any new users.
        response = await self.async_client.get(
            "/remote_user/", **{self.header: "newuser"}
        )
        self.assertEqual(await User.objects.acount(), num_users + 1)

    def test_known_user(self):
        """
        Tests the case where the username passed in the header is a valid User.
        """
        User.objects.create(username="knownuser")
        User.objects.create(username="knownuser2")
        num_users = User.objects.count()
        response = self.client.get("/remote_user/", **{self.header: self.known_user})
        self.assertEqual(response.context["user"].username, "knownuser")
        self.assertEqual(User.objects.count(), num_users)
        # A different user passed in the headers causes the new user
        # to be logged in.
        response = self.client.get("/remote_user/", **{self.header: self.known_user2})
        self.assertEqual(response.context["user"].username, "knownuser2")
        self.assertEqual(User.objects.count(), num_users)

    async def test_known_user_async(self):
        """See test_known_user."""
        await User.objects.acreate(username="knownuser")
        await User.objects.acreate(username="knownuser2")
        num_users = await User.objects.acount()
        response = await self.async_client.get(
            "/remote_user/", **{self.header: self.known_user}
        )
        self.assertEqual(response.context["user"].username, "knownuser")
        self.assertEqual(await User.objects.acount(), num_users)
        # A different user passed in the headers causes the new user
        # to be logged in.
        response = await self.async_client.get(
            "/remote_user/", **{self.header: self.known_user2}
        )
        self.assertEqual(response.context["user"].username, "knownuser2")
        self.assertEqual(await User.objects.acount(), num_users)

    def test_last_login(self):
        """
        A user's last_login is set the first time they make a
        request but not updated in subsequent requests with the same session.
        """
        user = User.objects.create(username="knownuser")
        # Set last_login to something so we can determine if it changes.
        default_login = datetime(2000, 1, 1)
        if settings.USE_TZ:
            default_login = default_login.replace(tzinfo=timezone.utc)
        user.last_login = default_login
        user.save()

        response = self.client.get("/remote_user/", **{self.header: self.known_user})
        self.assertNotEqual(default_login, response.context["user"].last_login)

        user = User.objects.get(username="knownuser")
        user.last_login = default_login
        user.save()
        response = self.client.get("/remote_user/", **{self.header: self.known_user})
        self.assertEqual(default_login, response.context["user"].last_login)

    async def test_last_login_async(self):
        """See test_last_login."""
        user = await User.objects.acreate(username="knownuser")
        # Set last_login to something so we can determine if it changes.
        default_login = datetime(2000, 1, 1)
        if settings.USE_TZ:
            default_login = default_login.replace(tzinfo=timezone.utc)
        user.last_login = default_login
        await user.asave()

        response = await self.async_client.get(
            "/remote_user/", **{self.header: self.known_user}
        )
        self.assertNotEqual(default_login, response.context["user"].last_login)

        user = await User.objects.aget(username="knownuser")
        user.last_login = default_login
        await user.asave()
        response = await self.async_client.get(
            "/remote_user/", **{self.header: self.known_user}
        )
        self.assertEqual(default_login, response.context["user"].last_login)

    def test_header_disappears(self):
        """
        A logged in user is logged out automatically when
        the REMOTE_USER header disappears during the same browser session.
        """
        User.objects.create(username="knownuser")
        # Known user authenticates
        response = self.client.get("/remote_user/", **{self.header: self.known_user})
        self.assertEqual(response.context["user"].username, "knownuser")
        # During the session, the REMOTE_USER header disappears. Should trigger logout.
        response = self.client.get("/remote_user/")
        self.assertTrue(response.context["user"].is_anonymous)
        # verify the remoteuser middleware will not remove a user
        # authenticated via another backend
        User.objects.create_user(username="modeluser", password="foo")
        self.client.login(username="modeluser", password="foo")
        authenticate(username="modeluser", password="foo")
        response = self.client.get("/remote_user/")
        self.assertEqual(response.context["user"].username, "modeluser")

    async def test_header_disappears_async(self):
        """See test_header_disappears."""
        await User.objects.acreate(username="knownuser")
        # Known user authenticates
        response = await self.async_client.get(
            "/remote_user/", **{self.header: self.known_user}
        )
        self.assertEqual(response.context["user"].username, "knownuser")
        # During the session, the REMOTE_USER header disappears. Should trigger logout.
        response = await self.async_client.get("/remote_user/")
        self.assertTrue(response.context["user"].is_anonymous)
        # verify the remoteuser middleware will not remove a user
        # authenticated via another backend
        await User.objects.acreate_user(username="modeluser", password="foo")
        await self.async_client.alogin(username="modeluser", password="foo")
        await aauthenticate(username="modeluser", password="foo")
        response = await self.async_client.get("/remote_user/")
        self.assertEqual(response.context["user"].username, "modeluser")

    def test_user_switch_forces_new_login(self):
        """
        If the username in the header changes between requests
        that the original user is logged out
        """
        User.objects.create(username="knownuser")
        # Known user authenticates
        response = self.client.get("/remote_user/", **{self.header: self.known_user})
        self.assertEqual(response.context["user"].username, "knownuser")
        # During the session, the REMOTE_USER changes to a different user.
        response = self.client.get("/remote_user/", **{self.header: "newnewuser"})
        # The current user is not the prior remote_user.
        # In backends that create a new user, username is "newnewuser"
        # In backends that do not create new users, it is '' (anonymous user)
        self.assertNotEqual(response.context["user"].username, "knownuser")

    async def test_user_switch_forces_new_login_async(self):
        """See test_user_switch_forces_new_login."""
        await User.objects.acreate(username="knownuser")
        # Known user authenticates
        response = await self.async_client.get(
            "/remote_user/", **{self.header: self.known_user}
        )
        self.assertEqual(response.context["user"].username, "knownuser")
        # During the session, the REMOTE_USER changes to a different user.
        response = await self.async_client.get(
            "/remote_user/", **{self.header: "newnewuser"}
        )
        # The current user is not the prior remote_user.
        # In backends that create a new user, username is "newnewuser"
        # In backends that do not create new users, it is '' (anonymous user)
        self.assertNotEqual(response.context["user"].username, "knownuser")

    def test_inactive_user(self):
        User.objects.create(username="knownuser", is_active=False)
        response = self.client.get("/remote_user/", **{self.header: "knownuser"})
        self.assertTrue(response.context["user"].is_anonymous)

    async def test_inactive_user_async(self):
        await User.objects.acreate(username="knownuser", is_active=False)
        response = await self.async_client.get(
            "/remote_user/", **{self.header: "knownuser"}
        )
        self.assertTrue(response.context["user"].is_anonymous)


class RemoteUserNoCreateBackend(RemoteUserBackend):
    """Backend that doesn't create unknown users."""

    create_unknown_user = False


class RemoteUserNoCreateTest(RemoteUserTest):
    """
    Contains the same tests as RemoteUserTest, but using a custom auth backend
    class that doesn't create unknown users.
    """

    backend = "auth_tests.test_remote_user.RemoteUserNoCreateBackend"

    def test_unknown_user(self):
        num_users = User.objects.count()
        response = self.client.get("/remote_user/", **{self.header: "newuser"})
        self.assertTrue(response.context["user"].is_anonymous)
        self.assertEqual(User.objects.count(), num_users)

    async def test_unknown_user_async(self):
        num_users = await User.objects.acount()
        response = await self.async_client.get(
            "/remote_user/", **{self.header: "newuser"}
        )
        self.assertTrue(response.context["user"].is_anonymous)
        self.assertEqual(await User.objects.acount(), num_users)


class AllowAllUsersRemoteUserBackendTest(RemoteUserTest):
    """Backend that allows inactive users."""

    backend = "django.contrib.auth.backends.AllowAllUsersRemoteUserBackend"

    def test_inactive_user(self):
        user = User.objects.create(username="knownuser", is_active=False)
        response = self.client.get("/remote_user/", **{self.header: self.known_user})
        self.assertEqual(response.context["user"].username, user.username)

    async def test_inactive_user_async(self):
        user = await User.objects.acreate(username="knownuser", is_active=False)
        response = await self.async_client.get(
            "/remote_user/", **{self.header: self.known_user}
        )
        self.assertEqual(response.context["user"].username, user.username)


class CustomRemoteUserBackend(RemoteUserBackend):
    """
    Backend that overrides RemoteUserBackend methods.
    """

    def clean_username(self, username):
        """
        Grabs username before the @ character.
        """
        return username.split("@")[0]

    def configure_user(self, request, user, created=True):
        """
        Sets user's email address using the email specified in an HTTP header.
        Sets user's last name for existing users.
        """
        user.email = request.META.get(RemoteUserTest.email_header, "")
        if not created:
            user.last_name = user.username
        user.save()
        return user


class RemoteUserCustomTest(RemoteUserTest):
    """
    Tests a custom RemoteUserBackend subclass that overrides the clean_username
    and configure_user methods.
    """

    backend = "auth_tests.test_remote_user.CustomRemoteUserBackend"
    # REMOTE_USER strings with email addresses for the custom backend to
    # clean.
    known_user = "knownuser@example.com"
    known_user2 = "knownuser2@example.com"

    def test_known_user(self):
        """
        The strings passed in REMOTE_USER should be cleaned and the known users
        should not have been configured with an email address.
        """
        super().test_known_user()
        knownuser = User.objects.get(username="knownuser")
        knownuser2 = User.objects.get(username="knownuser2")
        self.assertEqual(knownuser.email, "")
        self.assertEqual(knownuser2.email, "")
        self.assertEqual(knownuser.last_name, "knownuser")
        self.assertEqual(knownuser2.last_name, "knownuser2")

    def test_unknown_user(self):
        """
        The unknown user created should be configured with an email address
        provided in the request header.
        """
        num_users = User.objects.count()
        response = self.client.get(
            "/remote_user/",
            **{
                self.header: "newuser",
                self.email_header: "user@example.com",
            },
        )
        self.assertEqual(response.context["user"].username, "newuser")
        self.assertEqual(response.context["user"].email, "user@example.com")
        self.assertEqual(response.context["user"].last_name, "")
        self.assertEqual(User.objects.count(), num_users + 1)
        newuser = User.objects.get(username="newuser")
        self.assertEqual(newuser.email, "user@example.com")


class CustomHeaderMiddleware(RemoteUserMiddleware):
    """
    Middleware that overrides custom HTTP auth user header.
    """

    header = "HTTP_AUTHUSER"


class CustomHeaderRemoteUserTest(RemoteUserTest):
    """
    Tests a custom RemoteUserMiddleware subclass with custom HTTP auth user
    header.
    """

    middleware = "auth_tests.test_remote_user.CustomHeaderMiddleware"
    header = "HTTP_AUTHUSER"


class PersistentRemoteUserTest(RemoteUserTest):
    """
    PersistentRemoteUserMiddleware keeps the user logged in even if the
    subsequent calls do not contain the header value.
    """

    middleware = "django.contrib.auth.middleware.PersistentRemoteUserMiddleware"
    require_header = False

    def test_header_disappears(self):
        """
        A logged in user is kept logged in even if the REMOTE_USER header
        disappears during the same browser session.
        """
        User.objects.create(username="knownuser")
        # Known user authenticates
        response = self.client.get("/remote_user/", **{self.header: self.known_user})
        self.assertEqual(response.context["user"].username, "knownuser")
        # Should stay logged in if the REMOTE_USER header disappears.
        response = self.client.get("/remote_user/")
        self.assertFalse(response.context["user"].is_anonymous)
        self.assertEqual(response.context["user"].username, "knownuser")

    async def test_header_disappears_async(self):
        """See test_header_disappears."""
        await User.objects.acreate(username="knownuser")
        # Known user authenticates
        response = await self.async_client.get(
            "/remote_user/", **{self.header: self.known_user}
        )
        self.assertEqual(response.context["user"].username, "knownuser")
        # Should stay logged in if the REMOTE_USER header disappears.
        response = await self.async_client.get("/remote_user/")
        self.assertFalse(response.context["user"].is_anonymous)
        self.assertEqual(response.context["user"].username, "knownuser")
