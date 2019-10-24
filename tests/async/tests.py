import sys
from unittest import skipIf

from asgiref.sync import async_to_sync

from django.core.exceptions import SynchronousOnlyOperation
from django.test import SimpleTestCase
from django.utils.asyncio import async_unsafe

from .models import SimpleModel


@skipIf(sys.platform == 'win32' and (3, 8, 0) < sys.version_info < (3, 8, 1), 'https://bugs.python.org/issue38563')
class DatabaseConnectionTest(SimpleTestCase):
    """A database connection cannot be used in an async context."""
    @async_to_sync
    async def test_get_async_connection(self):
        with self.assertRaises(SynchronousOnlyOperation):
            list(SimpleModel.objects.all())


@skipIf(sys.platform == 'win32' and (3, 8, 0) < sys.version_info < (3, 8, 1), 'https://bugs.python.org/issue38563')
class AsyncUnsafeTest(SimpleTestCase):
    """
    async_unsafe decorator should work correctly and returns the correct
    message.
    """
    @async_unsafe
    def dangerous_method(self):
        return True

    @async_to_sync
    async def test_async_unsafe(self):
        # async_unsafe decorator catches bad access and returns the right
        # message.
        msg = (
            'You cannot call this from an async context - use a thread or '
            'sync_to_async.'
        )
        with self.assertRaisesMessage(SynchronousOnlyOperation, msg):
            self.dangerous_method()
