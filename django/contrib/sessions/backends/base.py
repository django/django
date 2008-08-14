import base64
import os
import random
import sys
import time
from datetime import datetime, timedelta
try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.utils.hashcompat import md5_constructor

# Use the system (hardware-based) random number generator if it exists.
if hasattr(random, 'SystemRandom'):
    randint = random.SystemRandom().randint
else:
    randint = random.randint
MAX_SESSION_KEY = 18446744073709551616L     # 2 << 63

class CreateError(Exception):
    """
    Used internally as a consistent exception type to catch from save (see the
    docstring for SessionBase.save() for details).
    """
    pass

class SessionBase(object):
    """
    Base class for all Session classes.
    """
    TEST_COOKIE_NAME = 'testcookie'
    TEST_COOKIE_VALUE = 'worked'

    def __init__(self, session_key=None):
        self._session_key = session_key
        self.accessed = False
        self.modified = False

    def __contains__(self, key):
        return key in self._session

    def __getitem__(self, key):
        return self._session[key]

    def __setitem__(self, key, value):
        self._session[key] = value
        self.modified = True

    def __delitem__(self, key):
        del self._session[key]
        self.modified = True

    def keys(self):
        return self._session.keys()

    def items(self):
        return self._session.items()

    def get(self, key, default=None):
        return self._session.get(key, default)

    def pop(self, key, *args):
        self.modified = self.modified or key in self._session
        return self._session.pop(key, *args)

    def setdefault(self, key, value):
        if key in self._session:
            return self._session[key]
        else:
            self.modified = True
            self._session[key] = value
            return value

    def set_test_cookie(self):
        self[self.TEST_COOKIE_NAME] = self.TEST_COOKIE_VALUE

    def test_cookie_worked(self):
        return self.get(self.TEST_COOKIE_NAME) == self.TEST_COOKIE_VALUE

    def delete_test_cookie(self):
        del self[self.TEST_COOKIE_NAME]

    def encode(self, session_dict):
        "Returns the given session dictionary pickled and encoded as a string."
        pickled = pickle.dumps(session_dict, pickle.HIGHEST_PROTOCOL)
        pickled_md5 = md5_constructor(pickled + settings.SECRET_KEY).hexdigest()
        return base64.encodestring(pickled + pickled_md5)

    def decode(self, session_data):
        encoded_data = base64.decodestring(session_data)
        pickled, tamper_check = encoded_data[:-32], encoded_data[-32:]
        if md5_constructor(pickled + settings.SECRET_KEY).hexdigest() != tamper_check:
            raise SuspiciousOperation("User tampered with session cookie.")
        try:
            return pickle.loads(pickled)
        # Unpickling can cause a variety of exceptions. If something happens,
        # just return an empty dictionary (an empty session).
        except:
            return {}

    def update(self, dict_):
        self._session.update(dict_)
        self.modified = True

    def has_key(self, key):
        return self._session.has_key(key)

    def values(self):
        return self._session.values()

    def iterkeys(self):
        return self._session.iterkeys()

    def itervalues(self):
        return self._session.itervalues()

    def iteritems(self):
        return self._session.iteritems()

    def clear(self):
        self._session.clear()
        self.modified = True

    def _get_new_session_key(self):
        "Returns session key that isn't being used."
        # The random module is seeded when this Apache child is created.
        # Use settings.SECRET_KEY as added salt.
        try:
            pid = os.getpid()
        except AttributeError:
            # No getpid() in Jython, for example
            pid = 1
        while 1:
            session_key = md5_constructor("%s%s%s%s"
                    % (random.randrange(0, MAX_SESSION_KEY), pid, time.time(),
                       settings.SECRET_KEY)).hexdigest()
            if not self.exists(session_key):
                break
        return session_key

    def _get_session_key(self):
        if self._session_key:
            return self._session_key
        else:
            self._session_key = self._get_new_session_key()
            return self._session_key

    def _set_session_key(self, session_key):
        self._session_key = session_key

    session_key = property(_get_session_key, _set_session_key)

    def _get_session(self):
        # Lazily loads session from storage.
        self.accessed = True
        try:
            return self._session_cache
        except AttributeError:
            if self._session_key is None:
                self._session_cache = {}
            else:
                self._session_cache = self.load()
        return self._session_cache

    _session = property(_get_session)

    def get_expiry_age(self):
        """Get the number of seconds until the session expires."""
        expiry = self.get('_session_expiry')
        if not expiry:   # Checks both None and 0 cases
            return settings.SESSION_COOKIE_AGE
        if not isinstance(expiry, datetime):
            return expiry
        delta = expiry - datetime.now()
        return delta.days * 86400 + delta.seconds

    def get_expiry_date(self):
        """Get session the expiry date (as a datetime object)."""
        expiry = self.get('_session_expiry')
        if isinstance(expiry, datetime):
            return expiry
        if not expiry:   # Checks both None and 0 cases
            expiry = settings.SESSION_COOKIE_AGE
        return datetime.now() + timedelta(seconds=expiry)

    def set_expiry(self, value):
        """
        Sets a custom expiration for the session. ``value`` can be an integer,
        a Python ``datetime`` or ``timedelta`` object or ``None``.

        If ``value`` is an integer, the session will expire after that many
        seconds of inactivity. If set to ``0`` then the session will expire on
        browser close.

        If ``value`` is a ``datetime`` or ``timedelta`` object, the session
        will expire at that specific future time.

        If ``value`` is ``None``, the session uses the global session expiry
        policy.
        """
        if value is None:
            # Remove any custom expiration for this session.
            try:
                del self['_session_expiry']
            except KeyError:
                pass
            return
        if isinstance(value, timedelta):
            value = datetime.now() + value
        self['_session_expiry'] = value

    def get_expire_at_browser_close(self):
        """
        Returns ``True`` if the session is set to expire when the browser
        closes, and ``False`` if there's an expiry date. Use
        ``get_expiry_date()`` or ``get_expiry_age()`` to find the actual expiry
        date/age, if there is one.
        """
        if self.get('_session_expiry') is None:
            return settings.SESSION_EXPIRE_AT_BROWSER_CLOSE
        return self.get('_session_expiry') == 0

    # Methods that child classes must implement.

    def exists(self, session_key):
        """
        Returns True if the given session_key already exists.
        """
        raise NotImplementedError

    def create(self):
        """
        Creates a new session instance. Guaranteed to create a new object with
        a unique key and will have saved the result once (with empty data)
        before the method returns.
        """
        raise NotImplementedError

    def save(self, must_create=False):
        """
        Saves the session data. If 'must_create' is True, a new session object
        is created (otherwise a CreateError exception is raised). Otherwise,
        save() can update an existing object with the same key.
        """
        raise NotImplementedError

    def delete(self, session_key):
        """
        Clears out the session data under this key.
        """
        raise NotImplementedError

    def load(self):
        """
        Loads the session data and returns a dictionary.
        """
        raise NotImplementedError
