import base64
import md5
import os
import random
import sys
import time
from django.conf import settings
from django.core.exceptions import SuspiciousOperation

try:
    import cPickle as pickle
except ImportError:
    import pickle

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
        pickled_md5 = md5.new(pickled + settings.SECRET_KEY).hexdigest()
        return base64.encodestring(pickled + pickled_md5)

    def decode(self, session_data):
        encoded_data = base64.decodestring(session_data)
        pickled, tamper_check = encoded_data[:-32], encoded_data[-32:]
        if md5.new(pickled + settings.SECRET_KEY).hexdigest() != tamper_check:
            raise SuspiciousOperation("User tampered with session cookie.")
        try:
            return pickle.loads(pickled)
        # Unpickling can cause a variety of exceptions. If something happens,
        # just return an empty dictionary (an empty session).
        except:
            return {}

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
            session_key = md5.new("%s%s%s%s" % (random.randint(0, sys.maxint - 1),
                                  pid, time.time(), settings.SECRET_KEY)).hexdigest()
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

    # Methods that child classes must implement.

    def exists(self, session_key):
        """
        Returns True if the given session_key already exists.
        """
        raise NotImplementedError

    def save(self):
        """
        Saves the session data.
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
