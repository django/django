try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.contrib.auth.management import create_permissions
from django.contrib.auth import models as auth_models
from django.contrib.contenttypes import models as contenttypes_models
from django.core.management import call_command
from django.test import TestCase


class TestAuthPermissions(TestCase):
    def test_permission_register_order(self):
        """Test that the order of registered permissions doesn't break"""
        # Changeset 14413 introduced a regression in the ordering of
        # newly created permissions for objects. When loading a fixture
        # after the initial creation (such as during unit tests), the
        # expected IDs for the permissions may not match up, leading to
        # SQL errors. This is ticket 14731

        # Start with a clean slate and build the permissions as we
        # expect to see them in the fixtures.
        auth_models.Permission.objects.all().delete()
        contenttypes_models.ContentType.objects.all().delete()
        create_permissions(auth_models, [], verbosity=0)
        create_permissions(contenttypes_models, [], verbosity=0)

        stderr = StringIO()
        call_command('loaddata', 'test_permissions.json',
                     verbosity=0, commit=False, stderr=stderr)
        self.assertEqual(stderr.getvalue(), '')
