from datetime import timedelta
import os
import shutil
import string
import tempfile
import warnings

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession
from django.contrib.sessions.backends.cache import SessionStore as CacheSession
from django.contrib.sessions.backends.cached_db import SessionStore as CacheDBSession
from django.contrib.sessions.backends.file import SessionStore as FileSession
from django.contrib.sessions.backends.signed_cookies import SessionStore as CookieSession
from django.contrib.sessions.models import Session
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import get_cache
from django.core import management
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.http import HttpResponse
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from django.utils import six
from django.utils import timezone
from django.utils import unittest


class SessionTestsMixin(object):
    # This does not inherit from TestCase to avoid any tests being run with this
    # class, which wouldn't work, and to allow different TestCase subclasses to
    # be used.

    backend = None  # subclasses must specify

    def setUp(self):
        self.session = self.backend()

    def tearDown(self):
        # NB: be careful to delete any sessions created; stale sessions fill up
        # the /tmp (with some backends) and eventually overwhelm it after lots
        # of runs (think buildbots)
        self.session.delete()

    def test_new_session(self):
        self.assertFalse(self.session.modified)
        self.assertFalse(self.session.accessed)

    def test_get_empty(self):
        self.assertEqual(self.session.get('cat'), None)

    def test_store(self):
        self.session['cat'] = "dog"
        self.assertTrue(self.session.modified)
        self.assertEqual(self.session.pop('cat'), 'dog')

    def test_pop(self):
        self.session['some key'] = 'exists'
        # Need to reset these to pretend we haven't accessed it:
        self.accessed = False
        self.modified = False

        self.assertEqual(self.session.pop('some key'), 'exists')
        self.assertTrue(self.session.accessed)
        self.assertTrue(self.session.modified)
        self.assertEqual(self.session.get('some key'), None)

    def test_pop_default(self):
        self.assertEqual(self.session.pop('some key', 'does not exist'),
                         'does not exist')
        self.assertTrue(self.session.accessed)
        self.assertFalse(self.session.modified)

    def test_setdefault(self):
        self.assertEqual(self.session.setdefault('foo', 'bar'), 'bar')
        self.assertEqual(self.session.setdefault('foo', 'baz'), 'bar')
        self.assertTrue(self.session.accessed)
        self.assertTrue(self.session.modified)

    def test_update(self):
        self.session.update({'update key': 1})
        self.assertTrue(self.session.accessed)
        self.assertTrue(self.session.modified)
        self.assertEqual(self.session.get('update key', None), 1)

    def test_has_key(self):
        self.session['some key'] = 1
        self.session.modified = False
        self.session.accessed = False
        self.assertIn('some key', self.session)
        self.assertTrue(self.session.accessed)
        self.assertFalse(self.session.modified)

    def test_values(self):
        self.assertEqual(list(self.session.values()), [])
        self.assertTrue(self.session.accessed)
        self.session['some key'] = 1
        self.assertEqual(list(self.session.values()), [1])

    def test_iterkeys(self):
        self.session['x'] = 1
        self.session.modified = False
        self.session.accessed = False
        i = six.iterkeys(self.session)
        self.assertTrue(hasattr(i, '__iter__'))
        self.assertTrue(self.session.accessed)
        self.assertFalse(self.session.modified)
        self.assertEqual(list(i), ['x'])

    def test_itervalues(self):
        self.session['x'] = 1
        self.session.modified = False
        self.session.accessed = False
        i = six.itervalues(self.session)
        self.assertTrue(hasattr(i, '__iter__'))
        self.assertTrue(self.session.accessed)
        self.assertFalse(self.session.modified)
        self.assertEqual(list(i), [1])

    def test_iteritems(self):
        self.session['x'] = 1
        self.session.modified = False
        self.session.accessed = False
        i = six.iteritems(self.session)
        self.assertTrue(hasattr(i, '__iter__'))
        self.assertTrue(self.session.accessed)
        self.assertFalse(self.session.modified)
        self.assertEqual(list(i), [('x', 1)])

    def test_clear(self):
        self.session['x'] = 1
        self.session.modified = False
        self.session.accessed = False
        self.assertEqual(list(self.session.items()), [('x', 1)])
        self.session.clear()
        self.assertEqual(list(self.session.items()), [])
        self.assertTrue(self.session.accessed)
        self.assertTrue(self.session.modified)

    def test_save(self):
        if (hasattr(self.session, '_cache') and'DummyCache' in
            settings.CACHES[settings.SESSION_CACHE_ALIAS]['BACKEND']):
            raise unittest.SkipTest("Session saving tests require a real cache backend")
        self.session.save()
        self.assertTrue(self.session.exists(self.session.session_key))

    def test_delete(self):
        self.session.save()
        self.session.delete(self.session.session_key)
        self.assertFalse(self.session.exists(self.session.session_key))

    def test_flush(self):
        self.session['foo'] = 'bar'
        self.session.save()
        prev_key = self.session.session_key
        self.session.flush()
        self.assertFalse(self.session.exists(prev_key))
        self.assertNotEqual(self.session.session_key, prev_key)
        self.assertTrue(self.session.modified)
        self.assertTrue(self.session.accessed)

    def test_cycle(self):
        self.session['a'], self.session['b'] = 'c', 'd'
        self.session.save()
        prev_key = self.session.session_key
        prev_data = list(self.session.items())
        self.session.cycle_key()
        self.assertNotEqual(self.session.session_key, prev_key)
        self.assertEqual(list(self.session.items()), prev_data)

    def test_invalid_key(self):
        # Submitting an invalid session key (either by guessing, or if the db has
        # removed the key) results in a new key being generated.
        try:
            session = self.backend('1')
            try:
                session.save()
            except AttributeError:
                self.fail("The session object did not save properly.  Middleware may be saving cache items without namespaces.")
            self.assertNotEqual(session.session_key, '1')
            self.assertEqual(session.get('cat'), None)
            session.delete()
        finally:
            # Some backends leave a stale cache entry for the invalid
            # session key; make sure that entry is manually deleted
            session.delete('1')

    def test_session_key_is_read_only(self):
        def set_session_key(session):
            session.session_key = session._get_new_session_key()
        self.assertRaises(AttributeError, set_session_key, self.session)

    # Custom session expiry
    def test_default_expiry(self):
        # A normal session has a max age equal to settings
        self.assertEqual(self.session.get_expiry_age(), settings.SESSION_COOKIE_AGE)

        # So does a custom session with an idle expiration time of 0 (but it'll
        # expire at browser close)
        self.session.set_expiry(0)
        self.assertEqual(self.session.get_expiry_age(), settings.SESSION_COOKIE_AGE)

    def test_custom_expiry_seconds(self):
        modification = timezone.now()

        self.session.set_expiry(10)

        date = self.session.get_expiry_date(modification=modification)
        self.assertEqual(date, modification + timedelta(seconds=10))

        age = self.session.get_expiry_age(modification=modification)
        self.assertEqual(age, 10)

    def test_custom_expiry_timedelta(self):
        modification = timezone.now()

        # Mock timezone.now, because set_expiry calls it on this code path.
        original_now = timezone.now
        try:
            timezone.now = lambda: modification
            self.session.set_expiry(timedelta(seconds=10))
        finally:
            timezone.now = original_now

        date = self.session.get_expiry_date(modification=modification)
        self.assertEqual(date, modification + timedelta(seconds=10))

        age = self.session.get_expiry_age(modification=modification)
        self.assertEqual(age, 10)

    def test_custom_expiry_datetime(self):
        modification = timezone.now()

        self.session.set_expiry(modification + timedelta(seconds=10))

        date = self.session.get_expiry_date(modification=modification)
        self.assertEqual(date, modification + timedelta(seconds=10))

        age = self.session.get_expiry_age(modification=modification)
        self.assertEqual(age, 10)

    def test_custom_expiry_reset(self):
        self.session.set_expiry(None)
        self.session.set_expiry(10)
        self.session.set_expiry(None)
        self.assertEqual(self.session.get_expiry_age(), settings.SESSION_COOKIE_AGE)

    def test_get_expire_at_browser_close(self):
        # Tests get_expire_at_browser_close with different settings and different
        # set_expiry calls
        with override_settings(SESSION_EXPIRE_AT_BROWSER_CLOSE=False):
            self.session.set_expiry(10)
            self.assertFalse(self.session.get_expire_at_browser_close())

            self.session.set_expiry(0)
            self.assertTrue(self.session.get_expire_at_browser_close())

            self.session.set_expiry(None)
            self.assertFalse(self.session.get_expire_at_browser_close())

        with override_settings(SESSION_EXPIRE_AT_BROWSER_CLOSE=True):
            self.session.set_expiry(10)
            self.assertFalse(self.session.get_expire_at_browser_close())

            self.session.set_expiry(0)
            self.assertTrue(self.session.get_expire_at_browser_close())

            self.session.set_expiry(None)
            self.assertTrue(self.session.get_expire_at_browser_close())

    def test_decode(self):
        # Ensure we can decode what we encode
        data = {'a test key': 'a test value'}
        encoded = self.session.encode(data)
        self.assertEqual(self.session.decode(encoded), data)

    def test_actual_expiry(self):
        # Regression test for #19200
        old_session_key = None
        new_session_key = None
        try:
            self.session['foo'] = 'bar'
            self.session.set_expiry(-timedelta(seconds=10))
            self.session.save()
            old_session_key = self.session.session_key
            # With an expiry date in the past, the session expires instantly.
            new_session = self.backend(self.session.session_key)
            new_session_key = new_session.session_key
            self.assertNotIn('foo', new_session)
        finally:
            self.session.delete(old_session_key)
            self.session.delete(new_session_key)


class DatabaseSessionTests(SessionTestsMixin, TestCase):

    backend = DatabaseSession

    def test_session_get_decoded(self):
        """
        Test we can use Session.get_decoded to retrieve data stored
        in normal way
        """
        self.session['x'] = 1
        self.session.save()

        s = Session.objects.get(session_key=self.session.session_key)

        self.assertEqual(s.get_decoded(), {'x': 1})

    def test_sessionmanager_save(self):
        """
        Test SessionManager.save method
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        s = Session.objects.get(session_key=self.session.session_key)
        # Change it
        Session.objects.save(s.session_key, {'y': 2}, s.expire_date)
        # Clear cache, so that it will be retrieved from DB
        del self.session._session_cache
        self.assertEqual(self.session['y'], 2)

    @override_settings(SESSION_ENGINE="django.contrib.sessions.backends.db")
    def test_clearsessions_command(self):
        """
        Test clearsessions command for clearing expired sessions.
        """
        self.assertEqual(0, Session.objects.count())

        # One object in the future
        self.session['foo'] = 'bar'
        self.session.set_expiry(3600)
        self.session.save()

        # One object in the past
        other_session = self.backend()
        other_session['foo'] = 'bar'
        other_session.set_expiry(-3600)
        other_session.save()

        # Two sessions are in the database before clearsessions...
        self.assertEqual(2, Session.objects.count())
        management.call_command('clearsessions')
        # ... and one is deleted.
        self.assertEqual(1, Session.objects.count())


@override_settings(USE_TZ=True)
class DatabaseSessionWithTimeZoneTests(DatabaseSessionTests):
    pass


class CacheDBSessionTests(SessionTestsMixin, TestCase):

    backend = CacheDBSession

    @unittest.skipIf('DummyCache' in
        settings.CACHES[settings.SESSION_CACHE_ALIAS]['BACKEND'],
        "Session saving tests require a real cache backend")
    def test_exists_searches_cache_first(self):
        self.session.save()
        with self.assertNumQueries(0):
            self.assertTrue(self.session.exists(self.session.session_key))

    def test_load_overlong_key(self):
        # Some backends might issue a warning
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.session._session_key = (string.ascii_letters + string.digits) * 20
            self.assertEqual(self.session.load(), {})


@override_settings(USE_TZ=True)
class CacheDBSessionWithTimeZoneTests(CacheDBSessionTests):
    pass


# Don't need DB flushing for these tests, so can use unittest.TestCase as base class
class FileSessionTests(SessionTestsMixin, unittest.TestCase):

    backend = FileSession

    def setUp(self):
        # Do file session tests in an isolated directory, and kill it after we're done.
        self.original_session_file_path = settings.SESSION_FILE_PATH
        self.temp_session_store = settings.SESSION_FILE_PATH = tempfile.mkdtemp()
        # Reset the file session backend's internal caches
        if hasattr(self.backend, '_storage_path'):
            del self.backend._storage_path
        super(FileSessionTests, self).setUp()

    def tearDown(self):
        super(FileSessionTests, self).tearDown()
        settings.SESSION_FILE_PATH = self.original_session_file_path
        shutil.rmtree(self.temp_session_store)

    @override_settings(
        SESSION_FILE_PATH="/if/this/directory/exists/you/have/a/weird/computer")
    def test_configuration_check(self):
        del self.backend._storage_path
        # Make sure the file backend checks for a good storage dir
        self.assertRaises(ImproperlyConfigured, self.backend)

    def test_invalid_key_backslash(self):
        # Ensure we don't allow directory-traversal
        self.assertRaises(SuspiciousOperation,
                          self.backend("a\\b\\c").load)

    def test_invalid_key_forwardslash(self):
        # Ensure we don't allow directory-traversal
        self.assertRaises(SuspiciousOperation,
                          self.backend("a/b/c").load)

    @override_settings(SESSION_ENGINE="django.contrib.sessions.backends.file")
    def test_clearsessions_command(self):
        """
        Test clearsessions command for clearing expired sessions.
        """
        storage_path = self.backend._get_storage_path()
        file_prefix = settings.SESSION_COOKIE_NAME

        def count_sessions():
            return len([session_file for session_file in os.listdir(storage_path)
                                     if session_file.startswith(file_prefix)])

        self.assertEqual(0, count_sessions())

        # One object in the future
        self.session['foo'] = 'bar'
        self.session.set_expiry(3600)
        self.session.save()

        # One object in the past
        other_session = self.backend()
        other_session['foo'] = 'bar'
        other_session.set_expiry(-3600)
        other_session.save()

        # Two sessions are in the filesystem before clearsessions...
        self.assertEqual(2, count_sessions())
        management.call_command('clearsessions')
        # ... and one is deleted.
        self.assertEqual(1, count_sessions())


class CacheSessionTests(SessionTestsMixin, unittest.TestCase):

    backend = CacheSession

    def test_load_overlong_key(self):
        # Some backends might issue a warning
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.session._session_key = (string.ascii_letters + string.digits) * 20
            self.assertEqual(self.session.load(), {})

    def test_default_cache(self):
        self.session.save()
        self.assertNotEqual(get_cache('default').get(self.session.cache_key), None)

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        },
        'sessions': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        },
    }, SESSION_CACHE_ALIAS='sessions')
    def test_non_default_cache(self):
        self.session.save()
        self.assertEqual(get_cache('default').get(self.session.cache_key), None)
        self.assertNotEqual(get_cache('sessions').get(self.session.cache_key), None)


class SessionMiddlewareTests(unittest.TestCase):

    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_secure_session_cookie(self):
        request = RequestFactory().get('/')
        response = HttpResponse('Session test')
        middleware = SessionMiddleware()

        # Simulate a request the modifies the session
        middleware.process_request(request)
        request.session['hello'] = 'world'

        # Handle the response through the middleware
        response = middleware.process_response(request, response)
        self.assertTrue(
            response.cookies[settings.SESSION_COOKIE_NAME]['secure'])

    @override_settings(SESSION_COOKIE_HTTPONLY=True)
    def test_httponly_session_cookie(self):
        request = RequestFactory().get('/')
        response = HttpResponse('Session test')
        middleware = SessionMiddleware()

        # Simulate a request the modifies the session
        middleware.process_request(request)
        request.session['hello'] = 'world'

        # Handle the response through the middleware
        response = middleware.process_response(request, response)
        self.assertTrue(
            response.cookies[settings.SESSION_COOKIE_NAME]['httponly'])
        self.assertIn('httponly',
            str(response.cookies[settings.SESSION_COOKIE_NAME]))

    @override_settings(SESSION_COOKIE_HTTPONLY=False)
    def test_no_httponly_session_cookie(self):
        request = RequestFactory().get('/')
        response = HttpResponse('Session test')
        middleware = SessionMiddleware()

        # Simulate a request the modifies the session
        middleware.process_request(request)
        request.session['hello'] = 'world'

        # Handle the response through the middleware
        response = middleware.process_response(request, response)
        self.assertFalse(response.cookies[settings.SESSION_COOKIE_NAME]['httponly'])

        self.assertNotIn('httponly',
                         str(response.cookies[settings.SESSION_COOKIE_NAME]))

    def test_session_save_on_500(self):
        request = RequestFactory().get('/')
        response = HttpResponse('Horrible error')
        response.status_code = 500
        middleware = SessionMiddleware()

        # Simulate a request the modifies the session
        middleware.process_request(request)
        request.session['hello'] = 'world'

        # Handle the response through the middleware
        response = middleware.process_response(request, response)

        # Check that the value wasn't saved above.
        self.assertNotIn('hello', request.session.load())


class CookieSessionTests(SessionTestsMixin, TestCase):

    backend = CookieSession

    def test_save(self):
        """
        This test tested exists() in the other session backends, but that
        doesn't make sense for us.
        """
        pass

    def test_cycle(self):
        """
        This test tested cycle_key() which would create a new session
        key for the same session data. But we can't invalidate previously
        signed cookies (other than letting them expire naturally) so
        testing for this behavior is meaningless.
        """
        pass

    @unittest.expectedFailure
    def test_actual_expiry(self):
        # The cookie backend doesn't handle non-default expiry dates, see #19201
        super(CookieSessionTests, self).test_actual_expiry()
