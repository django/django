from __future__ import unicode_literals

from django.contrib.auth.handlers.modwsgi import check_password, groups_for_user
from django.contrib.auth.models import User, Group
from django.contrib.auth.tests.utils import skipIfCustomUser
from django.test import TransactionTestCase


class ModWsgiHandlerTestCase(TransactionTestCase):
    """
    Tests for the mod_wsgi authentication handler
    """

    def setUp(self):
        user1 = User.objects.create_user('test', 'test@example.com', 'test')
        User.objects.create_user('test1', 'test1@example.com', 'test1')
        group = Group.objects.create(name='test_group')
        user1.groups.add(group)

    def test_check_password(self):
        """
        Verify that check_password returns the correct values as per
        http://code.google.com/p/modwsgi/wiki/AccessControlMechanisms#Apache_Authentication_Provider

        because the custom user available in the test framework does not
        support the is_active attribute, we can't test this with a custom
        user.
        """

        # User not in database
        self.assertTrue(check_password({}, 'unknown', '') is None)

        # Valid user with correct password
        self.assertTrue(check_password({}, 'test', 'test'))

        # Valid user with incorrect password
        self.assertFalse(check_password({}, 'test', 'incorrect'))

    @skipIfCustomUser
    def test_groups_for_user(self):
        """
        Check that groups_for_user returns correct values as per
        http://code.google.com/p/modwsgi/wiki/AccessControlMechanisms#Apache_Group_Authorisation
        """

        # User not in database
        self.assertEqual(groups_for_user({}, 'unknown'), [])

        self.assertEqual(groups_for_user({}, 'test'), [b'test_group'])
        self.assertEqual(groups_for_user({}, 'test1'), [])
