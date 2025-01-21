from django.contrib.auth import (
    aauthenticate,
    aget_user,
    alogin,
    alogout,
    aupdate_session_auth_hash,
)
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest
from django.test import TestCase, override_settings
from django.utils.deprecation import RemovedInDjango61Warning


class AsyncAuthTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create_user(
            "testuser", "test@example.com", "testpw"
        )

    async def test_aauthenticate(self):
        user = await aauthenticate(username="testuser", password="testpw")
        self.assertIsInstance(user, User)
        self.assertEqual(user.username, self.test_user.username)
        user.is_active = False
        await user.asave()
        self.assertIsNone(await aauthenticate(username="testuser", password="testpw"))

    async def test_alogin(self):
        request = HttpRequest()
        request.session = await self.client.asession()
        await alogin(request, self.test_user)
        user = await aget_user(request)
        self.assertIsInstance(user, User)
        self.assertEqual(user.username, self.test_user.username)

    async def test_changed_password_invalidates_aget_user(self):
        request = HttpRequest()
        request.session = await self.client.asession()
        await alogin(request, self.test_user)

        self.test_user.set_password("new_password")
        await self.test_user.asave()

        user = await aget_user(request)

        self.assertIsNotNone(user)
        self.assertTrue(user.is_anonymous)
        # Session should be flushed.
        self.assertIsNone(request.session.session_key)

    async def test_alogin_new_user(self):
        request = HttpRequest()
        request.session = await self.client.asession()
        await alogin(request, self.test_user)
        second_user = await User.objects.acreate_user(
            "testuser2", "test2@example.com", "testpw2"
        )
        await alogin(request, second_user)
        user = await aget_user(request)
        self.assertIsInstance(user, User)
        self.assertEqual(user.username, second_user.username)

    # RemovedInDjango61Warning: When the deprecation ends, replace with:
    # async def test_alogin_without_user(self):
    async def test_alogin_without_user_no_request_user(self):
        request = HttpRequest()
        request.session = await self.client.asession()
        # RemovedInDjango61Warning: When the deprecation ends, replace with:
        # with self.assertRaisesMessage(
        #     AttributeError,
        #     "'NoneType' object has no attribute 'get_session_auth_hash'",
        # ):
        #     await alogin(request, None)
        with (
            self.assertRaisesMessage(
                AttributeError,
                "'HttpRequest' object has no attribute 'auser'",
            ),
            self.assertWarnsMessage(
                RemovedInDjango61Warning,
                "Fallback to request.user when user is None will be removed.",
            ),
        ):
            await alogin(request, None)

    # RemovedInDjango61Warning: When the deprecation ends, remove completely.
    async def test_alogin_without_user_anonymous_request(self):
        async def auser():
            return AnonymousUser()

        request = HttpRequest()
        request.user = AnonymousUser()
        request.auser = auser
        request.session = await self.client.asession()
        with (
            self.assertRaisesMessage(
                AttributeError,
                "'AnonymousUser' object has no attribute '_meta'",
            ),
            self.assertWarnsMessage(
                RemovedInDjango61Warning,
                "Fallback to request.user when user is None will be removed.",
            ),
        ):
            await alogin(request, None)

    # RemovedInDjango61Warning: When the deprecation ends, remove completely.
    async def test_alogin_without_user_authenticated_request(self):
        async def auser():
            return self.test_user

        request = HttpRequest()
        request.user = self.test_user
        request.auser = auser
        request.session = await self.client.asession()
        with self.assertWarnsMessage(
            RemovedInDjango61Warning,
            "Fallback to request.user when user is None will be removed.",
        ):
            await alogin(request, None)
        user = await aget_user(request)
        self.assertIsInstance(user, User)
        self.assertEqual(user.username, self.test_user.username)

    async def test_alogout(self):
        await self.client.alogin(username="testuser", password="testpw")
        request = HttpRequest()
        request.session = await self.client.asession()
        await alogout(request)
        user = await aget_user(request)
        self.assertIsInstance(user, AnonymousUser)

    async def test_client_alogout(self):
        await self.client.alogin(username="testuser", password="testpw")
        request = HttpRequest()
        request.session = await self.client.asession()
        await self.client.alogout()
        user = await aget_user(request)
        self.assertIsInstance(user, AnonymousUser)

    async def test_change_password(self):
        await self.client.alogin(username="testuser", password="testpw")
        request = HttpRequest()
        request.session = await self.client.asession()
        request.user = self.test_user
        await aupdate_session_auth_hash(request, self.test_user)
        user = await aget_user(request)
        self.assertIsInstance(user, User)

    async def test_invalid_login(self):
        self.assertEqual(
            await self.client.alogin(username="testuser", password=""), False
        )

    async def test_client_aforce_login(self):
        await self.client.aforce_login(self.test_user)
        request = HttpRequest()
        request.session = await self.client.asession()
        user = await aget_user(request)
        self.assertEqual(user.username, self.test_user.username)

    @override_settings(
        AUTHENTICATION_BACKENDS=[
            "django.contrib.auth.backends.ModelBackend",
            "django.contrib.auth.backends.AllowAllUsersModelBackend",
        ]
    )
    async def test_client_aforce_login_backend(self):
        self.test_user.is_active = False
        await self.test_user.asave()
        await self.client.aforce_login(
            self.test_user,
            backend="django.contrib.auth.backends.AllowAllUsersModelBackend",
        )
        request = HttpRequest()
        request.session = await self.client.asession()
        user = await aget_user(request)
        self.assertEqual(user.username, self.test_user.username)
