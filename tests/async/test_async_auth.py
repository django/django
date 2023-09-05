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

    async def test_alogin_without_user(self):
        request = HttpRequest()
        request.user = self.test_user
        request.session = await self.client.asession()
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
