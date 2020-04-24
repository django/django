import base64
import os
import shutil
import string
import tempfile
import unittest
from datetime import timedelta
from http import cookies
from pathlib import Path
from django import VERSION

from django.conf import settings
from django.contrib.sessions.backends.base import (
    SESSION_HASHING_ALGORITHM, SESSION_KEY_DELIMITER, UpdateError, SESSION_HASHED_KEY_PREFIX
)
from django.contrib.sessions.backends.cache import (
    KEY_PREFIX as CACHE_KEY_PREFIX, SessionStore as CacheSession
)
from django.contrib.sessions.backends.cached_db import (
    KEY_PREFIX as CACHEDB_KEY_PREFIX, SessionStore as CacheDBSession, get_cache_store
)
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession
from django.contrib.sessions.backends.file import SessionStore as FileSession
from django.contrib.sessions.backends.signed_cookies import (
    SessionStore as CookieSession,
)
from django.contrib.sessions.exceptions import InvalidSessionKey
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.models import Session
from django.contrib.sessions.serializers import (
    JSONSerializer, PickleSerializer,
)
from django.core import management
from django.core.cache import caches
from django.core.cache.backends.base import InvalidCacheBackendError
from django.core.exceptions import ImproperlyConfigured, SuspiciousOperation
from django.http import HttpResponse
from django.test import (
    RequestFactory, TestCase, ignore_warnings, override_settings,
)
from django.utils import timezone
from django.utils.deprecation import RemovedInDjango40Warning

from .models import SessionStore as CustomDatabaseSession

class SettingsTests(TestCase):
    def test_store_key_hash_must_be_true_when_hashing_required(self):
        self.assertTrue(settings.SESSION_STORE_KEY_HASH or not settings.SESSION_REQUIRE_KEY_HASH)

    def test_default_require_key_hash_value(self):
        is_v4_or_later = VERSION >= (4,0)
        self.assertEqual(settings.SESSION_REQUIRE_KEY_HASH, is_v4_or_later)
    
class SessionTestsMixin:
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
        self.assertIs(self.session.modified, False)
        self.assertIs(self.session.accessed, False)

    def test_get_empty(self):
        self.assertIsNone(self.session.get('cat'))

    def test_store(self):
        self.session['cat'] = "dog"
        self.assertIs(self.session.modified, True)
        self.assertEqual(self.session.pop('cat'), 'dog')

    def test_pop(self):
        self.session['some key'] = 'exists'
        # Need to reset these to pretend we haven't accessed it:
        self.accessed = False
        self.modified = False

        self.assertEqual(self.session.pop('some key'), 'exists')
        self.assertIs(self.session.accessed, True)
        self.assertIs(self.session.modified, True)
        self.assertIsNone(self.session.get('some key'))

    def test_pop_default(self):
        self.assertEqual(self.session.pop('some key', 'does not exist'),
                         'does not exist')
        self.assertIs(self.session.accessed, True)
        self.assertIs(self.session.modified, False)

    def test_pop_default_named_argument(self):
        self.assertEqual(self.session.pop('some key', default='does not exist'), 'does not exist')
        self.assertIs(self.session.accessed, True)
        self.assertIs(self.session.modified, False)

    def test_pop_no_default_keyerror_raised(self):
        with self.assertRaises(KeyError):
            self.session.pop('some key')

    def test_setdefault(self):
        self.assertEqual(self.session.setdefault('foo', 'bar'), 'bar')
        self.assertEqual(self.session.setdefault('foo', 'baz'), 'bar')
        self.assertIs(self.session.accessed, True)
        self.assertIs(self.session.modified, True)

    def test_update(self):
        self.session.update({'update key': 1})
        self.assertIs(self.session.accessed, True)
        self.assertIs(self.session.modified, True)
        self.assertEqual(self.session.get('update key', None), 1)

    def test_has_key(self):
        self.session['some key'] = 1
        self.session.modified = False
        self.session.accessed = False
        self.assertIn('some key', self.session)
        self.assertIs(self.session.accessed, True)
        self.assertIs(self.session.modified, False)

    def test_values(self):
        self.assertEqual(list(self.session.values()), [])
        self.assertIs(self.session.accessed, True)
        self.session['some key'] = 1
        self.session.modified = False
        self.session.accessed = False
        self.assertEqual(list(self.session.values()), [1])
        self.assertIs(self.session.accessed, True)
        self.assertIs(self.session.modified, False)

    def test_keys(self):
        self.session['x'] = 1
        self.session.modified = False
        self.session.accessed = False
        self.assertEqual(list(self.session.keys()), ['x'])
        self.assertIs(self.session.accessed, True)
        self.assertIs(self.session.modified, False)

    def test_items(self):
        self.session['x'] = 1
        self.session.modified = False
        self.session.accessed = False
        self.assertEqual(list(self.session.items()), [('x', 1)])
        self.assertIs(self.session.accessed, True)
        self.assertIs(self.session.modified, False)

    def test_clear(self):
        self.session['x'] = 1
        self.session.modified = False
        self.session.accessed = False
        self.assertEqual(list(self.session.items()), [('x', 1)])
        self.session.clear()
        self.assertEqual(list(self.session.items()), [])
        self.assertIs(self.session.accessed, True)
        self.assertIs(self.session.modified, True)

    def test_save(self):
        self.session.save()
        self.assertIs(self.session.exists(self.session.frontend_key), True)

    def test_delete(self):
        self.session.save()
        self.session.delete(self.session.frontend_key)
        self.assertIs(self.session.exists(self.session.frontend_key), False)

    def test_flush(self):
        self.session['foo'] = 'bar'
        self.session.save()
        prev_key = self.session.frontend_key
        self.session.flush()
        self.assertIs(self.session.exists(prev_key), False)
        self.assertNotEqual(self.session.frontend_key, prev_key)
        self.assertIsNone(self.session.frontend_key)
        self.assertIs(self.session.modified, True)
        self.assertIs(self.session.accessed, True)

    def test_cycle(self):
        self.session['a'], self.session['b'] = 'c', 'd'
        self.session.save()
        prev_key = self.session.frontend_key
        prev_data = list(self.session.items())
        self.session.cycle_key()
        self.assertIs(self.session.exists(prev_key), False)
        self.assertNotEqual(self.session.frontend_key, prev_key)
        self.assertEqual(list(self.session.items()), prev_data)

    def test_cycle_with_no_session_cache(self):
        self.session['a'], self.session['b'] = 'c', 'd'
        self.session.save()
        prev_data = self.session.items()
        self.session = self.backend(self.session.frontend_key)
        self.assertIs(hasattr(self.session, '_session_cache'), False)
        self.session.cycle_key()
        self.assertCountEqual(self.session.items(), prev_data)

    def test_save_doesnt_clear_data(self):
        self.session['a'] = 'b'
        self.session.save()
        self.assertEqual(self.session['a'], 'b')

    def test_invalid_key(self):
        # Submitting an invalid session key (either by guessing, or if the db has
        # removed the key) results in a new key being generated.
        try:
            session = self.backend('1')
            session.save()
            self.assertNotEqual(session.frontend_key, '1')
            self.assertIsNone(session.get('cat'))
            session.delete()
        finally:
            # Some backends leave a stale cache entry for the invalid
            # session key; make sure that entry is manually deleted
            session.delete('1')

    def test_frontend_key_empty_string_invalid(self):
        """Falsey values (Such as an empty string) are rejected."""
        self.session._frontend_key = ''
        self.assertIsNone(self.session.frontend_key)

    def test_frontend_key_too_short_invalid(self):
        """Strings shorter than 8 characters are rejected."""
        self.session._frontend_key = '1234567'
        self.assertIsNone(self.session.frontend_key)

    @override_settings(SESSION_STORE_KEY_HASH=True, SESSION_REQUIRE_KEY_HASH=False)
    def test_frontend_key_valid_string_saved(self):
        """Strings of length 8 and up are accepted and stored."""
        self.session._frontend_key = '12345678'
        self.assertEqual(self.session.frontend_key, '12345678')

    def test_frontend_key_is_read_only(self):
        def set_frontend_key(session):
            session.frontend_key = session._get_new_frontend_key()
        with self.assertRaises(AttributeError):
            set_frontend_key(self.session)

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
            self.assertIs(self.session.get_expire_at_browser_close(), False)

            self.session.set_expiry(0)
            self.assertIs(self.session.get_expire_at_browser_close(), True)

            self.session.set_expiry(None)
            self.assertIs(self.session.get_expire_at_browser_close(), False)

        with override_settings(SESSION_EXPIRE_AT_BROWSER_CLOSE=True):
            self.session.set_expiry(10)
            self.assertIs(self.session.get_expire_at_browser_close(), False)

            self.session.set_expiry(0)
            self.assertIs(self.session.get_expire_at_browser_close(), True)

            self.session.set_expiry(None)
            self.assertIs(self.session.get_expire_at_browser_close(), True)

    def test_decode(self):
        # Ensure we can decode what we encode
        data = {'a test key': 'a test value'}
        encoded = self.session.encode(data)
        self.assertEqual(self.session.decode(encoded), data)

    @override_settings(SECRET_KEY='django_tests_secret_key')
    def test_decode_legacy(self):
        # RemovedInDjango40Warning: pre-Django 3.1 sessions will be invalid.
        legacy_encoded = (
            'OWUzNTNmNWQxNTBjOWExZmM4MmQ3NzNhMDRmMjU4NmYwNDUyNGI2NDp7ImEgdGVzd'
            'CBrZXkiOiJhIHRlc3QgdmFsdWUifQ=='
        )
        self.assertEqual(
            self.session.decode(legacy_encoded),
            {'a test key': 'a test value'},
        )

    def test_decode_failure_logged_to_security(self):
        bad_encode = base64.b64encode(b'flaskdj:alkdjf').decode('ascii')
        with self.assertLogs('django.security.SuspiciousSession', 'WARNING') as cm:
            self.assertEqual({}, self.session.decode(bad_encode))
        # The failed decode is logged.
        self.assertIn('corrupted', cm.output[0])

    def test_actual_expiry(self):
        # this doesn't work with JSONSerializer (serializing timedelta)
        with override_settings(SESSION_SERIALIZER='django.contrib.sessions.serializers.PickleSerializer'):
            self.session = self.backend()  # reinitialize after overriding settings

            # Regression test for #19200
            old_frontend_key = None
            new_frontend_key = None
            try:
                self.session['foo'] = 'bar'
                self.session.set_expiry(-timedelta(seconds=10))
                self.session.save()
                old_frontend_key = self.session.frontend_key
                # With an expiry date in the past, the session expires instantly.
                new_session = self.backend(self.session.frontend_key)
                new_frontend_key = new_session.frontend_key
                self.assertNotIn('foo', new_session)
            finally:
                self.session.delete(old_frontend_key)
                self.session.delete(new_frontend_key)

    def test_session_load_does_not_create_record(self):
        """
        Loading an unknown session key does not create a session record.

        Creating session records on load is a DOS vulnerability.
        """
        session = self.backend('someunknownkey')
        session.load()

        self.assertIsNone(session.frontend_key)
        self.assertIs(session.exists(session.frontend_key), False)
        # provided unknown key was cycled, not reused
        self.assertNotEqual(session.frontend_key, 'someunknownkey')

    def test_session_save_does_not_resurrect_session_logged_out_in_other_context(self):
        """
        Sessions shouldn't be resurrected by a concurrent request.
        """
        # Create new session.
        s1 = self.backend()
        s1['test_data'] = 'value1'
        s1.save(must_create=True)

        # Logout in another context.
        s2 = self.backend(s1.frontend_key)
        s2.delete()

        # Modify session in first context.
        s1['test_data'] = 'value2'
        with self.assertRaises(UpdateError):
            # This should throw an exception as the session is deleted, not
            # resurrect the session.
            s1.save()

        self.assertEqual(s1.load(), {})

    def test_delimiter_not_directory_component(self):
        """
        The SESSION_KEY_DELIMITER cannot be a file directory component.
        """
        file_directory_components = ['/', '\\', '>', '<', ':', '"', '|', '?', '*', '.']
        self.assertNotIn(SESSION_KEY_DELIMITER, file_directory_components)

    def test_delimiter_single_character(self):
        """
        The SESSION_KEY_DELIMITER can only be a single character.
        """
        self.assertEqual(len(SESSION_KEY_DELIMITER), 1)


@override_settings(SESSION_STORE_KEY_HASH=False)
class DatabaseSessionTests(SessionTestsMixin, TestCase):

    backend = DatabaseSession
    session_engine = 'django.contrib.sessions.backends.db'

    @property
    def model(self):
        return self.backend.get_model_class()

    def test_session_str(self):
        "Session repr should be the backend key."
        self.session['x'] = 1
        self.session.save()

        backend_key = self.session.get_backend_key(self.session.frontend_key)
        s = self.model.objects.get(session_key=backend_key)

        self.assertEqual(str(s), backend_key)

    def test_session_get_decoded(self):
        """
        Test we can use Session.get_decoded to retrieve data stored
        in normal way
        """
        self.session['x'] = 1
        self.session.save()

        backend_key = self.session.get_backend_key(self.session.frontend_key)
        s = self.model.objects.get(session_key=backend_key)

        self.assertEqual(s.get_decoded(), {'x': 1})

    def test_sessionmanager_save(self):
        """
        Test SessionManager.save method
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        backend_key = self.session.get_backend_key(self.session.frontend_key)
        s = self.model.objects.get(session_key=backend_key)
        # Change it
        self.model.objects.save(s.session_key, {'y': 2}, s.expire_date)
        # Clear cache, so that it will be retrieved from DB
        del self.session._session_cache
        self.assertEqual(self.session['y'], 2)

    def test_clearsessions_command(self):
        """
        Test clearsessions command for clearing expired sessions.
        """
        self.assertEqual(0, self.model.objects.count())

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
        self.assertEqual(2, self.model.objects.count())
        with override_settings(SESSION_ENGINE=self.session_engine):
            management.call_command('clearsessions')
        # ... and one is deleted.
        self.assertEqual(1, self.model.objects.count())

@override_settings(SESSION_STORE_KEY_HASH=False, SESSION_REQUIRE_KEY_HASH=False)
class DatabaseSessionWithoutHashingTests(DatabaseSessionTests):

    def test_cookie_sessionid_same_as_db_session_key(self):
        """
        A frontend_key should be the same as the db session_key.
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        db_session_key = self.model.objects.get(
            session_key=self.session.frontend_key).session_key
        self.assertEqual(db_session_key, self.session.frontend_key)


@override_settings(USE_TZ=True)
class DatabaseSessionWithTimeZoneTests(DatabaseSessionTests):
    pass


@override_settings(SESSION_STORE_KEY_HASH=True)
class DatabaseSessionWithHashingTests(DatabaseSessionTests):

    def test_frontend_key_correct_format(self):
        """
        A frontend_key should contain the algorithm, delimiter,
        and the unhashed frontend_key.
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        frontend_key = self.session.frontend_key
        algorithm, key = frontend_key.split(SESSION_KEY_DELIMITER)

        self.assertEqual(algorithm, SESSION_HASHING_ALGORITHM)
        self.assertEqual(len(key), 32)

    def test_frontend_key_not_db_session_key(self):
        """
        A frontend_key should differ from the db session_key.
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        with self.assertRaises(self.model.DoesNotExist):
            self.model.objects.get(session_key=self.session.frontend_key)

    def test_backend_key_correct(self):
        """
        A session key should be stored as a sha256 hash by default.
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        backend_key = self.session.get_backend_key(self.session.frontend_key)
        self.assertEqual(len(backend_key), 64)

    def test_backend_key_gets_session(self):
        """
        A session backend should be directly accessible via hashed lookup.
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        backend_key = self.session.get_backend_key(self.session.frontend_key)
        results = self.model.objects.get(session_key=backend_key)
        self.assertIsNotNone(results)

@override_settings(SESSION_REQUIRE_KEY_HASH=False)
class DatabaseSessionWithHashingNotRequiredTests(DatabaseSessionWithHashingTests):

    def test_insecure_bypass_when_hashing_not_required(self):
        """
        A session backend should be directly accessible via hashed lookup.
        """
        # Create new session.
        s1 = self.backend()
        s1['test_data'] = 'value1'
        s1.save(must_create=True)

        # Login with hashed value in another context.
        backend_key = s1.get_backend_key(s1.frontend_key)
        s2 = self.backend(backend_key)
        self.assertEqual(s2.get('test_data'), 'value1')

        s2['test_data'] = 'value2'
        s2.save()
        del s1._session_cache
        self.assertEqual(s1.get('test_data'), 'value2')

@override_settings(SESSION_REQUIRE_KEY_HASH=True)
class DatabaseSessionWithHashingRequiredTests(DatabaseSessionWithHashingTests):

    def test_insecure_bypass_when_hashing_required(self):
        """
        A session backend should not be directly accessible via hashed lookup.
        """
        # Create new session.
        s1 = self.backend()
        s1['test_data'] = 'value1'
        s1.save(must_create=True)

        # Login with hashed value in another context.
        backend_key = s1.get_backend_key(s1.frontend_key)
        s2 = self.backend(backend_key)
        s2['test_data'] = 'value2'
        s2.save()
        del s1._session_cache
        self.assertEqual(s1.get('test_data'), 'value1')

    def test_frontend_key_invalid(self):
        """Inproperly formated strings are not accepted."""
        self.session._frontend_key = '123456789'
        self.assertIsNone(self.session.frontend_key)

    def test_frontend_key_valid_string_saved(self):
        """Properly formatted strings are accepted and stored."""
        self.session._frontend_key = 'sha256$12345678912345678912345678912345'
        self.assertEqual(self.session.frontend_key, 'sha256$12345678912345678912345678912345')


@override_settings(USE_TZ=True, SESSION_STORE_KEY_HASH=True)
class DatabaseSessionWithHashingWithTimeZoneTests(DatabaseSessionTests):
    pass


@override_settings(USE_TZ=True, SESSION_STORE_KEY_HASH=True,
                   SESSION_REQUIRE_KEY_HASH=True)
class DatabaseSessionWithHashingRequiredWithTimeZoneTests(DatabaseSessionTests):
    pass


class CustomDatabaseSessionTests(DatabaseSessionTests):
    backend = CustomDatabaseSession
    session_engine = 'sessions_tests.models'
    custom_session_cookie_age = 60 * 60 * 24  # One day.

    def test_extra_session_field(self):
        # Set the account ID to be picked up by a custom session storage
        # and saved to a custom session model database column.
        self.session['_auth_user_id'] = 42
        self.session.save()

        # Make sure that the customized create_model_instance() was called.
        backend_key = self.session.get_backend_key(self.session.frontend_key)
        s = self.model.objects.get(session_key=backend_key)
        self.assertEqual(s.account_id, 42)

        # Make the session "anonymous".
        self.session.pop('_auth_user_id')
        self.session.save()

        # Make sure that save() on an existing session did the right job.
        backend_key = self.session.get_backend_key(self.session.frontend_key)
        s = self.model.objects.get(session_key=backend_key)
        self.assertIsNone(s.account_id)

    def test_custom_expiry_reset(self):
        self.session.set_expiry(None)
        self.session.set_expiry(10)
        self.session.set_expiry(None)
        self.assertEqual(self.session.get_expiry_age(), self.custom_session_cookie_age)

    def test_default_expiry(self):
        self.assertEqual(self.session.get_expiry_age(), self.custom_session_cookie_age)
        self.session.set_expiry(0)
        self.assertEqual(self.session.get_expiry_age(), self.custom_session_cookie_age)


@override_settings(SESSION_STORE_KEY_HASH=True)
class CustomDatabaseSessionTestsWithHashingTests(CustomDatabaseSessionTests):
    pass


@override_settings(SESSION_STORE_KEY_HASH=False)
class CacheDBSessionTests(SessionTestsMixin, TestCase):

    backend = CacheDBSession
    session_engine = 'django.contrib.sessions.backends.cache_db'

    @property
    def model(self):
        return self.backend.get_model_class()

    def test_exists_searches_cache_first(self):
        self.session.save()
        with self.assertNumQueries(0):
            self.assertIs(self.session.exists(self.session.frontend_key), True)

    # Some backends might issue a warning
    @ignore_warnings(module="django.core.cache.backends.base")
    def test_load_overlong_key(self):
        s = self.backend(SESSION_HASHED_KEY_PREFIX+(string.ascii_letters + string.digits) * 20)
        cache_key = s._get_cache_key(s.get_backend_key(s.frontend_key))
        # pre-populate cache with value
        self.backend._set_cache(cache_key, {'a': 'c'})
        # verify pre-populated value is loaded
        self.assertEqual(s.load(), {'a': 'c'})
        s.delete()

    @override_settings(SESSION_CACHE_ALIAS='sessions')
    def test_non_default_cache(self):
        # 21000 - CacheDB backend should respect SESSION_CACHE_ALIAS.
        with self.assertRaises(InvalidCacheBackendError):
            get_cache_store()

    def test_loads_from_cache_if_present(self):
        s = self.backend(SESSION_HASHED_KEY_PREFIX+'foobar1234')
        cache_key = s._get_cache_key(s.get_backend_key(s.frontend_key))
        self.backend._set_cache(cache_key, {'a':'b'})
        self.assertEqual(self.backend._get_cache(cache_key), {'a': 'b'})        
        self.assertEqual(s.load(), {'a': 'b'})
        s.delete()


@override_settings(SESSION_REQUIRE_KEY_HASH=False)
class CacheDBSessionWithoutHashingTests(CacheDBSessionTests):

    def test_frontend_key_same_as_session_key(self):
        """
        A frontend_key should be the same as the db session_key.
        """

        # Create a session
        self.session['y'] = 1
        self.session.save()

        db_session_key = self.model.objects.get(
            session_key=self.session.frontend_key).session_key
        self.assertEqual(db_session_key, self.session.frontend_key)
        self.assertIsNotNone(caches['default'].get(self.session.cache_key))
        self.assertEqual(self.session.frontend_key,
                         self.session.cache_key[len(CACHEDB_KEY_PREFIX):])


@override_settings(USE_TZ=True)
class CacheDBSessionWithTimeZoneTests(CacheDBSessionTests):
    pass


@override_settings(SESSION_STORE_KEY_HASH=True)
class CacheDBSessionWithHashingTests(CacheDBSessionTests):

    def test_frontend_key_correct_format(self):
        """
        A frontend_key should contain the algorithm, delimiter,
        and the unhashed frontend_key.
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        frontend_key = self.session.frontend_key
        algorithm, key = frontend_key.split(SESSION_KEY_DELIMITER)

        self.assertEqual(algorithm, SESSION_HASHING_ALGORITHM)
        self.assertEqual(len(key), 32)

    def test_frontend_key_not_db_session_key(self):
        """
        A frontend_key should differ from the db session_key.
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        self.assertTrue(self.session.exists(self.session.frontend_key))
        with self.assertRaises(self.model.DoesNotExist):
            self.session.get_model().objects.get(session_key=self.session.frontend_key)
        self.assertTrue(self.session.get_model().objects.get(
            session_key=self.session.get_backend_key(self.session.frontend_key))
        )
        self.assertIsNotNone(caches['default'].get(self.session.cache_key))
        self.assertNotEqual(self.session.frontend_key,
                            self.session.cache_key[len(CACHEDB_KEY_PREFIX):])


@override_settings(SESSION_REQUIRE_KEY_HASH=False)
class CacheDBSessionWithHashingNotRequiredTests(CacheDBSessionWithHashingTests):

    def test_insecure_bypass_when_hashing_not_required(self):
        """
        A session backend should be directly accessible via hashed lookup.
        """
        # Create new session.
        s1 = self.backend()
        s1['test_data'] = 'value1'
        s1.save(must_create=True)

        # Login with hashed value in another context.
        backend_key = s1.get_backend_key(s1.frontend_key)
        s2 = self.backend(backend_key)
        self.assertEqual(s2.get('test_data'), 'value1')
        s2['test_data'] = 'value2'
        s2.save()
        del s1._session_cache
        self.assertEqual(s1.get('test_data'), 'value2')


@override_settings(SESSION_REQUIRE_KEY_HASH=True)
class CacheDBSessionWithHashingRequiredTests(CacheDBSessionWithHashingTests):

    def test_insecure_bypass_when_hashing_required(self):
        """
        A session backend should not be directly accessible via hashed lookup.
        """
        # Create new session.
        s1 = self.backend()
        s1['test_data'] = 'value1'
        s1.save(must_create=True)

        # Login with hashed value in another context.
        backend_key = s1.get_backend_key(s1.frontend_key)
        s2 = self.backend(backend_key)
        s2['test_data'] = 'value2'
        s2.save()
        del s1._session_cache
        self.assertEqual(s1.get('test_data'), 'value1')

    def test_frontend_key_invalid(self):
        """Inproperly formated strings are not accepted."""
        self.session._frontend_key = '123456789'
        self.assertIsNone(self.session.frontend_key)

    def test_session_key_valid_string_saved(self):
        """Properly formatted strings are accepted and stored."""
        self.session._frontend_key = 'sha256$12345678912345678912345678912345'
        self.assertEqual(self.session.frontend_key, 'sha256$12345678912345678912345678912345')


@override_settings(SESSION_STORE_KEY_HASH=True)
class CacheDBSessionWithTimeZoneWithHashingTests(CacheDBSessionWithTimeZoneTests):
    pass


@override_settings(SESSION_REQUIRE_KEY_HASH=True)
class CacheDBSessionWithTimeZoneWithHashingRequiredTests(CacheDBSessionWithTimeZoneWithHashingTests):
    pass


@override_settings(SESSION_STORE_KEY_HASH=False)
class FileSessionTests(SessionTestsMixin, TestCase):

    backend = FileSession

    def setUp(self):
        # Do file session tests in an isolated directory, and kill it after we're done.
        self.original_session_file_path = settings.SESSION_FILE_PATH
        self.temp_session_store = settings.SESSION_FILE_PATH = self.mkdtemp()
        # Reset the file session backend's internal caches
        if hasattr(self.backend, '_storage_path'):
            del self.backend._storage_path
        super().setUp()

    def tearDown(self):
        super().tearDown()
        settings.SESSION_FILE_PATH = self.original_session_file_path
        if len(os.listdir(self.temp_session_store)) > 0:
            shutil.rmtree(self.temp_session_store)

    def mkdtemp(self):
        return tempfile.mkdtemp()

    @classmethod
    def _frontend_key_to_file(cls, frontend_key):
        return cls.backend._backend_key_to_file(cls.backend.get_backend_key(frontend_key))

    @override_settings(
        SESSION_FILE_PATH='/if/this/directory/exists/you/have/a/weird/computer',
    )
    def test_configuration_check(self):
        if hasattr(self.backend, '_storage_path'):
            del self.backend._storage_path

        s = self.backend()
        # Make sure the file backend checks for a good storage dir
        with self.assertRaises(ImproperlyConfigured):
            s.save()

    def test_invalid_key_backslash(self):
        # Ensure we don't allow directory-traversal.
        # This is tested directly on _backend_key_to_file, as load() will swallow
        # a SuspiciousOperation in the same way as an OSError - by creating
        # a new session, making it unclear whether the slashes were detected.
        with self.assertRaises(InvalidSessionKey):
            self.backend._backend_key_to_file(self.backend.get_backend_key("a\\b\\c"))

    def test_invalid_key_forwardslash(self):
        # Ensure we don't allow directory-traversal
        with self.assertRaises(InvalidSessionKey):
            self._frontend_key_to_file("a/b/c")

    @override_settings(
        SESSION_ENGINE="django.contrib.sessions.backends.file",
        SESSION_COOKIE_AGE=0,
    )
    def test_clearsessions_command(self):
        """
        Test clearsessions command for clearing expired sessions.
        """
        storage_path = self.backend._get_storage_path()
        file_prefix = settings.SESSION_COOKIE_NAME

        def count_sessions():
            return len([
                session_file for session_file in os.listdir(storage_path)
                if session_file.startswith(file_prefix)
            ])

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

        # One object in the present without an expiry (should be deleted since
        # its modification time + SESSION_COOKIE_AGE will be in the past when
        # clearsessions runs).
        other_session2 = self.backend()
        other_session2['foo'] = 'bar'
        other_session2.save()

        # Three sessions are in the filesystem before clearsessions...
        self.assertEqual(3, count_sessions())
        management.call_command('clearsessions')
        # ... and two are deleted.
        self.assertEqual(1, count_sessions())


class FileSessionPathLibTests(FileSessionTests):
    def mkdtemp(self):
        tmp_dir = super().mkdtemp()
        return Path(tmp_dir)


@override_settings(SESSION_REQUIRE_KEY_HASH=False)
class FileSessionWithoutHashingTests(FileSessionTests):
    def test_file_key_same_as_backend_key(self):
        """
        Check that frontend_key and file key are the same.
        """
        # create session
        self.session['y'] = 1
        self.session.save()

        file_path = self._frontend_key_to_file(self.session._get_or_create_frontend_key())
        path_start = os.path.join(self.backend._get_storage_path(), self.backend._get_file_prefix())
        self.assertTrue(file_path.startswith(path_start))

        path_rest = file_path[len(path_start):]
        self.assertEqual(path_rest, self.session.get_backend_key(self.session.frontend_key))


@override_settings(SESSION_STORE_KEY_HASH=True)
class FileSessionWithHashingTests(FileSessionTests):
    def test_file_key_same_as_frontend_key(self):
        """
        Check that frontend_key and file key differ.
        """
        # create session
        self.session['y'] = 1
        self.session.save()

        file_path = self._frontend_key_to_file(self.session._get_or_create_frontend_key())

        file_path_start = os.path.join(self.backend()._get_storage_path(), self.backend()._get_file_prefix())       
        self.assertTrue(file_path.startswith(file_path_start))

        file_key = file_path[len(file_path_start):]
        self.assertNotEqual(file_key, self.session.frontend_key)
        self.assertEqual(file_key, self.session.get_backend_key(self.session.frontend_key))


@override_settings(SESSION_REQUIRE_KEY_HASH=False)
class FileSessionWithHashingNotRequiredTests(FileSessionWithHashingTests):

    @override_settings(SESSION_REQUIRE_KEY_HASH=False)
    def test_insecure_bypass_when_hashing_not_required(self):
        """
        A session backend should be directly accessible via hashed lookup.
        """
        # Create new session.
        s1 = self.backend()
        s1['test_data'] = 'value1'
        s1.save(must_create=True)

        # Login with hashed value in another context.
        backend_key = s1.get_backend_key(s1.frontend_key)
        s2 = self.backend(backend_key)
        s2['test_data'] = 'value2'
        s2.save()
        del s1._session_cache
        self.assertEqual(s1.get('test_data'), 'value2')


@override_settings(SESSION_REQUIRE_KEY_HASH=True)
class FileSessionWithHashingRequiredTests(FileSessionWithHashingTests):

    def test_insecure_bypass_when_hashing_required(self):
        """
        A session backend should not be directly accessible via hashed lookup.
        """
        # Create new session.
        s1 = self.backend()
        s1['test_data'] = 'value1'
        s1.save(must_create=True)

        # Login with hashed value in another context.
        backend_key = s1.get_backend_key(s1.frontend_key)
        s2 = self.backend(backend_key)
        s2['test_data'] = 'value2'
        s2.save()
        del s1._session_cache
        self.assertEqual(s1.get('test_data'), 'value1')

    def test_frontend_key_invalid(self):
        """Inproperly formated strings are not accepted."""
        self.session._frontend_key = '123456789'
        self.assertIsNone(self.session.frontend_key)

    def test_frontend_key_valid_string_saved(self):
        """Properly formatted strings are accepted and stored."""
        self.session._frontend_key = 'sha256$12345678912345678912345678912345'
        self.assertEqual(self.session.frontend_key, 'sha256$12345678912345678912345678912345')



@override_settings(SESSION_STORE_KEY_HASH=False)
class CacheSessionTests(SessionTestsMixin, TestCase):

    backend = CacheSession

    @staticmethod
    def temp_cache_store_overwrite(store):
        class TempCacheStoreOverwrite:
            def __init__(self, store):
                self.store = store

            def __enter__(self):
                self._original_store = CacheSession._cache
                CacheSession._cache = self.store

            def __exit__(self, exc_type, exc_val, exc_tb):
                CacheSession._cache = self._original_store
        return TempCacheStoreOverwrite(store)

    # Some backends might issue a warning
    @ignore_warnings(module="django.core.cache.backends.base")
    def test_load_overlong_key(self):
        self.session._frontend_key = (string.ascii_letters + string.digits) * 20
        self.assertEqual(self.session.load(), {})

    def test_default_cache(self):
        self.session.save()
        self.assertIsNotNone(caches['default'].get(self.session.cache_key))

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        },
        'sessions': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'session',
        },
    }, SESSION_CACHE_ALIAS='sessions')
    def test_non_default_cache(self):
        # Re-initialize the session backend to make use of overridden settings.
        with self.temp_cache_store_overwrite(caches['sessions']):
            self.session = self.backend()
            self.session.save()
            self.assertIsNone(caches['default'].get(self.session.cache_key))
            self.assertIsNotNone(caches['sessions'].get(self.session.cache_key))
            self.session.delete()

    def test_create_and_save(self):
        self.session = self.backend()
        self.session.create()
        self.session.save()
        self.assertIsNotNone(caches['default'].get(self.session.cache_key))

@override_settings(SESSION_REQUIRE_KEY_HASH=False)
class CacheSessionWithoutHashingTests(CacheSessionTests):

    def test_frontend_key_same_as_cache_key(self):
        """
        A frontend_key should be the same as the cache key.
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        self.assertIsNotNone(caches['default'].get(self.session.cache_key))
        self.assertEqual(self.session.get_backend_key(self.session.frontend_key),
                         self.session.cache_key[len(CACHE_KEY_PREFIX):])


@override_settings(SESSION_STORE_KEY_HASH=True)
class CacheSessionWithHashingTests(CacheDBSessionTests):

    def test_frontend_key_correct_format(self):
        """
        A frontend_key should contain the algorithm, delimiter,
        and the unhashed session_key.
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        frontend_key = self.session.frontend_key
        algorithm, key = frontend_key.split(SESSION_KEY_DELIMITER)

        self.assertEqual(algorithm, SESSION_HASHING_ALGORITHM)
        self.assertEqual(len(key), 32)

    def test_fronent_key_not_cache_key(self):
        """
        A frontend_key should differ from the cache_key.
        """
        # Create a session
        self.session['y'] = 1
        self.session.save()

        self.assertTrue(self.session.exists(self.session.frontend_key))
        self.assertEqual(caches['default'].get(self.session.cache_key), {'y': 1})
        self.assertNotEqual(self.session.frontend_key,
                            self.session.cache_key[len(CACHE_KEY_PREFIX):])


@override_settings(SESSION_REQUIRE_KEY_HASH=False)
class CacheSessionWithHashingNotRequiredTests(CacheSessionWithHashingTests):

    def test_insecure_bypass_when_hashing_not_required(self):
        """
        A session backend should be directly accessible via hashed lookup.
        """
        # Create new session.
        s1 = self.backend()
        s1['test_data'] = 'value1'
        s1.save(must_create=True)

        # Login with hashed value in another context.
        backend_key = s1.get_backend_key(s1.frontend_key)
        s2 = self.backend(backend_key)
        s2['test_data'] = 'value2'
        s2.save()
        del s1._session_cache
        self.assertEqual(s1.get('test_data'), 'value2')


@override_settings(SESSION_REQUIRE_KEY_HASH=True)
class CacheSessionWithHashingRequiredTests(CacheSessionWithHashingTests):

    def test_insecure_bypass_when_hashing_required(self):
        """
        A session backend should not be directly accessible via hashed lookup.
        """
        # Create new session.
        s1 = self.backend()
        s1['test_data'] = 'value1'
        s1.save(must_create=True)

        # Login with hashed value in another context.
        backend_key = s1.get_backend_key(s1.frontend_key)
        s2 = self.backend(backend_key)
        s2['test_data'] = 'value2'
        s2.save()
        del s1._session_cache
        self.assertEqual(s1.get('test_data'), 'value1')

    def test_frontend_key_invalid(self):
        """Inproperly formated strings are not accepted."""
        self.session._frontend_key = '123456789'
        self.assertIsNone(self.session.frontend_key)

    def test_frontend_key_valid_string_saved(self):
        """Properly formatted strings are accepted and stored."""
        self.session._frontend_key = 'sha256$12345678912345678912345678912345'
        self.assertEqual(self.session.frontend_key, 'sha256$12345678912345678912345678912345')


class SessionMiddlewareTests(TestCase):
    request_factory = RequestFactory()

    @staticmethod
    def get_response_touching_session(request):
        request.session['hello'] = 'world'
        return HttpResponse('Session test')

    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_secure_session_cookie(self):
        request = self.request_factory.get('/')
        middleware = SessionMiddleware(self.get_response_touching_session)

        # Handle the response through the middleware
        response = middleware(request)
        self.assertIs(response.cookies[settings.SESSION_COOKIE_NAME]['secure'], True)

    @override_settings(SESSION_COOKIE_HTTPONLY=True)
    def test_httponly_session_cookie(self):
        request = self.request_factory.get('/')
        middleware = SessionMiddleware(self.get_response_touching_session)

        # Handle the response through the middleware
        response = middleware(request)
        self.assertIs(response.cookies[settings.SESSION_COOKIE_NAME]['httponly'], True)
        self.assertIn(
            cookies.Morsel._reserved['httponly'],
            str(response.cookies[settings.SESSION_COOKIE_NAME])
        )

    @override_settings(SESSION_COOKIE_SAMESITE='Strict')
    def test_samesite_session_cookie(self):
        request = self.request_factory.get('/')
        middleware = SessionMiddleware(self.get_response_touching_session)
        response = middleware(request)
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_NAME]['samesite'], 'Strict')

    @override_settings(SESSION_COOKIE_HTTPONLY=False)
    def test_no_httponly_session_cookie(self):
        request = self.request_factory.get('/')
        middleware = SessionMiddleware(self.get_response_touching_session)
        response = middleware(request)
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_NAME]['httponly'], '')
        self.assertNotIn(
            cookies.Morsel._reserved['httponly'],
            str(response.cookies[settings.SESSION_COOKIE_NAME])
        )

    def test_session_save_on_500(self):
        def response_500(requset):
            response = HttpResponse('Horrible error')
            response.status_code = 500
            request.session['hello'] = 'world'
            return response

        request = self.request_factory.get('/')
        SessionMiddleware(response_500)(request)

        # The value wasn't saved above.
        self.assertNotIn('hello', request.session.load())

    def test_session_update_error_redirect(self):
        def response_delete_session(request):
            request.session = DatabaseSession()
            request.session.save(must_create=True)
            request.session.delete()
            return HttpResponse()

        request = self.request_factory.get('/foo/')
        middleware = SessionMiddleware(response_delete_session)

        msg = (
            "The request's session was deleted before the request completed. "
            "The user may have logged out in a concurrent request, for example."
        )
        with self.assertRaisesMessage(SuspiciousOperation, msg):
            # Handle the response through the middleware. It will try to save
            # the deleted session which will cause an UpdateError that's caught
            # and raised as a SuspiciousOperation.
            middleware(request)

    def test_session_delete_on_end(self):
        def response_ending_session(request):
            request.session.flush()
            return HttpResponse('Session test')

        request = self.request_factory.get('/')
        middleware = SessionMiddleware(response_ending_session)

        # Before deleting, there has to be an existing cookie
        request.COOKIES[settings.SESSION_COOKIE_NAME] = 'abc'

        # Handle the response through the middleware
        response = middleware(request)

        # The cookie was deleted, not recreated.
        # A deleted cookie header looks like:
        #  Set-Cookie: sessionid=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; Path=/
        self.assertEqual(
            'Set-Cookie: {}=""; expires=Thu, 01 Jan 1970 00:00:00 GMT; '
            'Max-Age=0; Path=/'.format(
                settings.SESSION_COOKIE_NAME,
            ),
            str(response.cookies[settings.SESSION_COOKIE_NAME])
        )
        # SessionMiddleware sets 'Vary: Cookie' to prevent the 'Set-Cookie'
        # from being cached.
        self.assertEqual(response['Vary'], 'Cookie')

    @override_settings(SESSION_COOKIE_DOMAIN='.example.local', SESSION_COOKIE_PATH='/example/')
    def test_session_delete_on_end_with_custom_domain_and_path(self):
        def response_ending_session(request):
            request.session.flush()
            return HttpResponse('Session test')

        request = self.request_factory.get('/')
        middleware = SessionMiddleware(response_ending_session)

        # Before deleting, there has to be an existing cookie
        request.COOKIES[settings.SESSION_COOKIE_NAME] = 'abc'

        # Handle the response through the middleware
        response = middleware(request)

        # The cookie was deleted, not recreated.
        # A deleted cookie header with a custom domain and path looks like:
        #  Set-Cookie: sessionid=; Domain=.example.local;
        #              expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0;
        #              Path=/example/
        self.assertEqual(
            'Set-Cookie: {}=""; Domain=.example.local; expires=Thu, '
            '01 Jan 1970 00:00:00 GMT; Max-Age=0; Path=/example/'.format(
                settings.SESSION_COOKIE_NAME,
            ),
            str(response.cookies[settings.SESSION_COOKIE_NAME])
        )

    def test_flush_empty_without_session_cookie_doesnt_set_cookie(self):
        def response_ending_session(request):
            request.session.flush()
            return HttpResponse('Session test')

        request = self.request_factory.get('/')
        middleware = SessionMiddleware(response_ending_session)

        # Handle the response through the middleware
        response = middleware(request)

        # A cookie should not be set.
        self.assertEqual(response.cookies, {})
        # The session is accessed so "Vary: Cookie" should be set.
        self.assertEqual(response['Vary'], 'Cookie')

    def test_empty_session_saved(self):
        """
        If a session is emptied of data but still has a key, it should still
        be updated.
        """
        def response_set_session(request):
            # Set a session key and some data.
            request.session['foo'] = 'bar'
            return HttpResponse('Session test')

        request = self.request_factory.get('/')
        middleware = SessionMiddleware(response_set_session)

        # Handle the response through the middleware.
        response = middleware(request)
        self.assertEqual(tuple(request.session.items()), (('foo', 'bar'),))
        # A cookie should be set, along with Vary: Cookie.
        self.assertIn(
            'Set-Cookie: sessionid=%s' % request.session.frontend_key,
            str(response.cookies)
        )
        self.assertEqual(response['Vary'], 'Cookie')

        # Empty the session data.
        del request.session['foo']
        # Handle the response through the middleware.
        response = HttpResponse('Session test')
        response = middleware.process_response(request, response)
        self.assertEqual(dict(request.session.values()), {})

        frontend_key = request.session.get_backend_key(request.session.frontend_key)
        session = Session.objects.get(session_key=frontend_key)
        self.assertEqual(session.get_decoded(), {})
        # While the session is empty, it hasn't been flushed so a cookie should
        # still be set, along with Vary: Cookie.
        self.assertGreater(len(request.session.frontend_key), 8)
        self.assertIn(
            'Set-Cookie: sessionid=%s' % request.session.frontend_key,
            str(response.cookies)
        )
        self.assertEqual(response['Vary'], 'Cookie')

    def test_deprecation_warning_for_non_hashing_custom_backends(self):
        original_engine = settings.SESSION_ENGINE

        settings.SESSION_ENGINE = 'tests.sessions_tests.deprecated_engine'
        with self.assertRaises(RemovedInDjango40Warning):
            SessionMiddleware(self.get_response_touching_session)

        settings.SESSION_ENGINE = original_engine


# Don't need DB flushing for these tests, so can use unittest.TestCase as base class
class CookieSessionTests(SessionTestsMixin, unittest.TestCase):

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
        super().test_actual_expiry()

    def test_unpickling_exception(self):
        # signed_cookies backend should handle unpickle exceptions gracefully
        # by creating a new session
        self.assertEqual(self.session.serializer, JSONSerializer)
        self.session.save()

        self.session.serializer = PickleSerializer
        self.session.load()

    @unittest.skip("Cookie backend doesn't have an external store to create records in.")
    def test_session_load_does_not_create_record(self):
        pass

    @unittest.skip("CookieSession is stored in the client and there is no way to query it.")
    def test_session_save_does_not_resurrect_session_logged_out_in_other_context(self):
        pass

