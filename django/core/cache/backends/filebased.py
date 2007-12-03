"File-based cache backend"

import os, time
try:
    import cPickle as pickle
except ImportError:
    import pickle
from django.core.cache.backends.base import BaseCache
from django.utils.http import urlquote_plus

class CacheClass(BaseCache):
    def __init__(self, dir, params):
        BaseCache.__init__(self, params)
        
        max_entries = params.get('max_entries', 300)
        try:
            self._max_entries = int(max_entries)
        except (ValueError, TypeError):
            self._max_entries = 300
            
        cull_frequency = params.get('cull_frequency', 3)
        try:
            self._cull_frequency = int(cull_frequency)
        except (ValueError, TypeError):
            self._cull_frequency = 3
            
        self._dir = dir
        if not os.path.exists(self._dir):
            self._createdir()

    def add(self, key, value, timeout=None):
        fname = self._key_to_file(key)
        if timeout is None:
            timeout = self.default_timeout
        try:
            filelist = os.listdir(self._dir)
        except (IOError, OSError):
            self._createdir()
            filelist = []
        if len(filelist) > self._max_entries:
            self._cull(filelist)
        if os.path.basename(fname) not in filelist:
            try:
                f = open(fname, 'wb')
                now = time.time()
                pickle.dump(now + timeout, f, 2)
                pickle.dump(value, f, 2)
            except (IOError, OSError):
                pass

    def get(self, key, default=None):
        fname = self._key_to_file(key)
        try:
            f = open(fname, 'rb')
            exp = pickle.load(f)
            now = time.time()
            if exp < now:
                f.close()
                os.remove(fname)
            else:
                return pickle.load(f)
        except (IOError, OSError, EOFError, pickle.PickleError):
            pass
        return default

    def set(self, key, value, timeout=None):
        fname = self._key_to_file(key)
        if timeout is None:
            timeout = self.default_timeout
        try:
            filelist = os.listdir(self._dir)
        except (IOError, OSError):
            self._createdir()
            filelist = []
        if len(filelist) > self._max_entries:
            self._cull(filelist)
        try:
            f = open(fname, 'wb')
            now = time.time()
            pickle.dump(now + timeout, f, 2)
            pickle.dump(value, f, 2)
        except (IOError, OSError):
            pass

    def delete(self, key):
        try:
            os.remove(self._key_to_file(key))
        except (IOError, OSError):
            pass

    def has_key(self, key):
        return os.path.exists(self._key_to_file(key))

    def _cull(self, filelist):
        if self._cull_frequency == 0:
            doomed = filelist
        else:
            doomed = [k for (i, k) in enumerate(filelist) if i % self._cull_frequency == 0]
        for fname in doomed:
            try:
                os.remove(os.path.join(self._dir, fname))
            except (IOError, OSError):
                pass

    def _createdir(self):
        try:
            os.makedirs(self._dir)
        except OSError:
            raise EnvironmentError, "Cache directory '%s' does not exist and could not be created'" % self._dir

    def _key_to_file(self, key):
        return os.path.join(self._dir, urlquote_plus(key))
