from django.contrib.auth import authenticate
from django.contrib.auth.context_processors import PermLookupDict, PermWrapper
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.test import TestCase, override_settings

from .settings import AUTH_MIDDLEWARE_CLASSES, AUTH_TEMPLATES


class MockUser(object):
    def has_module_perms(self, perm):
        if perm == 'mockapp':
            return True
        return False

    def has_perm(self, perm):
        if perm == 'mockapp.someperm':
            return True
        return False


class PermWrapperTests(TestCase):
    """
    Test some details of the PermWrapper implementation.
    """
    class EQLimiterObject(object):
        """
        This object makes sure __eq__ will not be called endlessly.
        """
        def __init__(self):
            self.eq_calls = 0

        def __eq__(self, other):
            if self.eq_calls > 0:
                return True
            self.eq_calls += 1
            return False

    def test_permwrapper_in(self):
        """
        Test that 'something' in PermWrapper works as expected.
        """
        perms = PermWrapper(MockUser())
        # Works for modules and full permissions.
        self.assertIn('mockapp', perms)
        self.assertNotIn('nonexisting', perms)
        self.assertIn('mockapp.someperm', perms)
        self.assertNotIn('mockapp.nonexisting', perms)

    def test_permlookupdict_in(self):
        """
        No endless loops if accessed with 'in' - refs #18979.
        """
        pldict = PermLookupDict(MockUser(), 'mockapp')
        with self.assertRaises(TypeError):
            self.EQLimiterObject() in pldict


@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.SHA1PasswordHasher'],
    ROOT_URLCONF='auth_tests.urls',
    TEMPLATES=AUTH_TEMPLATES,
    USE_TZ=False,                           # required for loading the fixture
)
class AuthContextProcessorTests(TestCase):
    """
    Tests for the ``django.contrib.auth.context_processors.auth`` processor
    """
    fixtures = ['context-processors-users.xml']

    @override_settings(MIDDLEWARE_CLASSES=AUTH_MIDDLEWARE_CLASSES)
    def test_session_not_accessed(self):
        """
        Tests that the session is not accessed simply by including
        the auth context processor
        """
        response = self.client.get('/auth_processor_no_attr_access/')
        self.assertContains(response, "Session not accessed")

    @override_settings(MIDDLEWARE_CLASSES=AUTH_MIDDLEWARE_CLASSES)
    def test_session_is_accessed(self):
        """
        Tests that the session is accessed if the auth context processor
        is used and relevant attributes accessed.
        """
        response = self.client.get('/auth_processor_attr_access/')
        self.assertContains(response, "Session accessed")

    def test_perms_attrs(self):
        u = User.objects.create_user(username='normal', password='secret')
        u.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Permission),
                codename='add_permission'))
        self.client.login(username='normal', password='secret')
        response = self.client.get('/auth_processor_perms/')
        self.assertContains(response, "Has auth permissions")
        self.assertContains(response, "Has auth.add_permission permissions")
        self.assertNotContains(response, "nonexisting")

    def test_perm_in_perms_attrs(self):
        u = User.objects.create_user(username='normal', password='secret')
        u.user_permissions.add(
            Permission.objects.get(
                content_type=ContentType.objects.get_for_model(Permission),
                codename='add_permission'))
        self.client.login(username='normal', password='secret')
        response = self.client.get('/auth_processor_perm_in_perms/')
        self.assertContains(response, "Has auth permissions")
        self.assertContains(response, "Has auth.add_permission permissions")
        self.assertNotContains(response, "nonexisting")

    def test_message_attrs(self):
        self.client.login(username='super', password='secret')
        response = self.client.get('/auth_processor_messages/')
        self.assertContains(response, "Message 1")

    def test_user_attrs(self):
        """
        Test that the lazy objects returned behave just like the wrapped objects.
        """
        # These are 'functional' level tests for common use cases.  Direct
        # testing of the implementation (SimpleLazyObject) is in the 'utils'
        # tests.
        self.client.login(username='super', password='secret')
        user = authenticate(username='super', password='secret')
        response = self.client.get('/auth_processor_user/')
        self.assertContains(response, "unicode: super")
        self.assertContains(response, "id: 100")
        self.assertContains(response, "username: super")
        # bug #12037 is tested by the {% url %} in the template:
        self.assertContains(response, "url: /userpage/super/")

        # See if this object can be used for queries where a Q() comparing
        # a user can be used with another Q() (in an AND or OR fashion).
        # This simulates what a template tag might do with the user from the
        # context. Note that we don't need to execute a query, just build it.
        #
        # The failure case (bug #12049) on Python 2.4 with a LazyObject-wrapped
        # User is a fatal TypeError: "function() takes at least 2 arguments
        # (0 given)" deep inside deepcopy().
        #
        # Python 2.5 and 2.6 succeeded, but logged internally caught exception
        # spew:
        #
        #    Exception RuntimeError: 'maximum recursion depth exceeded while
        #    calling a Python object' in <type 'exceptions.AttributeError'>
        #    ignored"
        Q(user=response.context['user']) & Q(someflag=True)

        # Tests for user equality.  This is hard because User defines
        # equality in a non-duck-typing way
        # See bug #12060
        self.assertEqual(response.context['user'], user)
        self.assertEqual(user, response.context['user'])
