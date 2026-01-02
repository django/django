from asgiref.sync import sync_to_async

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.test import Client, TestCase, override_settings


class PermissionOnlyBackend(BaseBackend):
    """
    A backend that inherits from BaseBackend but cannot handle users.
    Mimics libraries like django-rules.
    """

    def has_perm(self, user_obj, perm, obj=None):
        return False


@override_settings(
    AUTHENTICATION_BACKENDS=[
        "auth_tests.test_ticket_36837.PermissionOnlyBackend",
        "django.contrib.auth.backends.ModelBackend",
    ]
)
class ForceLoginBackendTests(TestCase):
    def test_force_login_skips_permission_only_backend(self):
        """
        Client.force_login() should skip backends that inherit from BaseBackend
        but return None for get_user().
        """
        User = get_user_model()
        user = User.objects.create_user(
            username="force_login_test", password="password"
        )

        client = Client()
        client.force_login(user)

        # Sync test is fine to access session directly
        self.assertEqual(
            client.session["_auth_user_backend"],
            "django.contrib.auth.backends.ModelBackend",
        )

    async def test_aforce_login_skips_permission_only_backend(self):
        """
        AsyncClient.aforce_login() should also skip broken backends.
        """
        from django.test import AsyncClient

        User = get_user_model()
        user = await User.objects.acreate_user(
            username="aforce_login_test", password="password"
        )

        client = AsyncClient()
        await client.aforce_login(user)

        session = await client.asession()

        # We must access the session data in a sync_to_async wrapper
        # because checking the key triggers a database load.
        backend_used = await sync_to_async(lambda: session["_auth_user_backend"])()

        self.assertEqual(backend_used, "django.contrib.auth.backends.ModelBackend")
