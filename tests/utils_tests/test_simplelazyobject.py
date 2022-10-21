import pickle

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.functional import SimpleLazyObject
from django.core.exceptions import SynchronousOnlyOperation
from inspect import iscoroutinefunction
from asgiref.sync import sync_to_async


class TestUtilsSimpleLazyObjectDjangoTestCase(TestCase):
    def test_pickle(self):
        user = User.objects.create_user("johndoe", "john@example.com", "pass")
        x = SimpleLazyObject(lambda: user)
        pickle.dumps(x)
        # Try the variant protocol levels.
        pickle.dumps(x, 0)
        pickle.dumps(x, 1)
        pickle.dumps(x, 2)

    async def test_async_retrieval(self):
        """
        Test SimpleLazyObject behavior when used from an async coroutine.
        """

        async def get_user_async():
            return await sync_to_async(User.objects.get)(username="johndoe")

        def get_user_sync():
            return User.objects.get(username="johndoe")

        # Create user for test purpose
        await sync_to_async(User.objects.create_user)("johndoe", "john@example.com", "pass")

        # Test simple lazy object with async method as parameter
        lazy_user_async = SimpleLazyObject(get_user_async)

        self.assertIs(iscoroutinefunction(lazy_user_async), True)
        self.assertEqual((await lazy_user_async).username, "johndoe")

        # Test awaiting for an already resolved object with async coroutine
        self.assertEqual((await lazy_user_async).username, "johndoe")

        # Test simple lazy object with sync function as parameter
        lazy_user_sync = SimpleLazyObject(get_user_sync)

        # Ensure sync function can't be called from a coroutine
        with self.assertRaises(SynchronousOnlyOperation):
            print(lazy_user_sync.username)

        # Test awaiting for simple lazy object with sync function as parameter 
        self.assertEqual((await lazy_user_sync).username, "johndoe")

        # Test awaiting for an already resolved object with sync function
        self.assertEqual((await lazy_user_sync).username, "johndoe")
