import os

from django.conf import global_settings
from django.contrib.auth import authenticate
from django.db.models import Q
from django.template import context
from django.test import TestCase
from django.test.utils import override_settings


@override_settings(
    TEMPLATE_DIRS=(
            os.path.join(os.path.dirname(__file__), 'templates'),
        ),
    USE_TZ=False,                           # required for loading the fixture
)
class AuthContextProcessorTests(TestCase):
    """
    Tests for the ``django.contrib.auth.context_processors.auth`` processor
    """
    urls = 'django.contrib.auth.tests.urls'
    fixtures = ['context-processors-users.xml']

    @override_settings(
        MIDDLEWARE_CLASSES=global_settings.MIDDLEWARE_CLASSES,
        TEMPLATE_CONTEXT_PROCESSORS=global_settings.TEMPLATE_CONTEXT_PROCESSORS,
    )
    def test_session_not_accessed(self):
        """
        Tests that the session is not accessed simply by including
        the auth context processor
        """
        response = self.client.get('/auth_processor_no_attr_access/')
        self.assertContains(response, "Session not accessed")

    @override_settings(
        MIDDLEWARE_CLASSES=global_settings.MIDDLEWARE_CLASSES,
        TEMPLATE_CONTEXT_PROCESSORS=global_settings.TEMPLATE_CONTEXT_PROCESSORS,
    )
    def test_session_is_accessed(self):
        """
        Tests that the session is accessed if the auth context processor
        is used and relevant attributes accessed.
        """
        response = self.client.get('/auth_processor_attr_access/')
        self.assertContains(response, "Session accessed")

    def test_perms_attrs(self):
        self.client.login(username='super', password='secret')
        response = self.client.get('/auth_processor_perms/')
        self.assertContains(response, "Has auth permissions")

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
        query = Q(user=response.context['user']) & Q(someflag=True)

        # Tests for user equality.  This is hard because User defines
        # equality in a non-duck-typing way
        # See bug #12060
        self.assertEqual(response.context['user'], user)
        self.assertEqual(user, response.context['user'])
