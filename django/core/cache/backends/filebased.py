"File-based cache backend"

import os
import time
try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.core.cache.backends.base import BaseCache
from django.utils.hashcompat import md5_constructor

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
        if self.has_key(key):
            return False

        self.set(key, value, timeout)
        return True

    def get(self, key, default=None):
        fname = self._key_to_file(key)
        try:
            f = open(fname, 'rb')
            exp = pickle.load(f)
            now = time.time()
            if exp < now:
                f.close()
                self._delete(fname)
            else:
                return pickle.load(f)
        except (IOError, OSError, EOFError, pickle.PickleError):
            pass
        return default

    def set(self, key, value, timeout=None):
        fname = self._key_to_file(key)
        dirname = os.path.dirname(fname)

        if timeout is None:
            timeout = self.default_timeout

        self._cull()

        try:
            if not os.path.exists(dirname):
                os.makedirs(dirname)

            f = open(fname, 'wb')
            now = time.time()
            pickle.dump(now + timeout, f, pickle.HIGHEST_PROTOCOL)
            pickle.dump(value, f, pickle.HIGHEST_PROTOCOL)
        except (IOError, OSError):
            pass

    def delete(self, key):
        try:
            self._delete(self._key_to_file(key))
        except (IOError, OSError):
            pass

    def _delete(self, fname):
        os.remove(fname)
        try:
            # Remove the 2 subdirs if they're empty
            dirname = os.path.dirname(fname)
            os.rmdir(dirname)
            os.rmdir(os.path.dirname(dirname))
        except (IOError, OSError):
            pass

    def has_key(self, key):
        fname = self._key_to_file(key)
        try:
            f = open(fname, 'rb')
            exp = pickle.load(f)
            now = time.time()
            if exp < now:
                f.close()
                self._delete(fname)
                return False
            else:
                return True
        except (IOError, OSError, EOFError, pickle.PickleError):
            return False

    def _cull(self):
        if int(self._num_entries) < self._max_entries:
            return

        try:
            filelist = os.listdir(self._dir)
        except (IOError, OSError):
            return

        if self._cull_frequency == 0:
            doomed = filelist
        else:
            doomed = [os.path.join(self._dir, k) for (i, k) in enumerate(filelist) if i % self._cull_frequency == 0]

        for topdir in doomed:
            try:
                for root, _, files in os.walk(topdir):
                    for f in files:
                        self._delete(os.path.join(root, f))
            except (IOError, OSError):
                pass

    def _createdir(self):
        try:
            os.makedirs(self._dir)
        except OSError:
            raise EnvironmentError("Cache directory '%s' does not exist and could not be created'" % self._dir)

    def _key_to_file(self, key):
        """
        Convert the filename into an md5 string. We'll turn the first couple
        bits of the path into directory prefixes to be nice to filesystems
        that have problems with large numbers of files in a directory.

        Thus, a cache key of "foo" gets turnned into a file named
        ``{cache-dir}ac/bd/18db4cc2f85cedef654fccc4a4d8``.
        """
        path = md5_constructor(key.encode('utf-8')).hexdigest()
        path = os.path.join(path[:2], path[2:4], path[4:])
        return os.path.join(self._dir, path)

    def _get_num_entries(self):
        count = 0
        for _,_,files in os.walk(self._dir):
            count += len(files)
        return count
    _num_entries = property(_get_num_entries)
