"File-based cache backend"

import os
import time
import shutil
try:
    import cPickle as pickle
except ImportError:
    import pickle

from django.core.cache.backends.base import BaseCache
from django.utils.hashcompat import md5_constructor

class CacheClass(BaseCache):
    def __init__(self, dir, params):
        BaseCache.__init__(self, params)
        self._dir = dir
        if not os.path.exists(self._dir):
            self._createdir()

    def add(self, key, value, timeout=None):
        self.validate_key(key)
        if self.has_key(key):
            return False

        self.set(key, value, timeout)
        return True

    def get(self, key, default=None):
        self.validate_key(key)
        fname = self._key_to_file(key)
        try:
            f = open(fname, 'rb')
            try:
                exp = pickle.load(f)
                now = time.time()
                if exp < now:
                    self._delete(fname)
                else:
                    return pickle.load(f)
            finally:
                f.close()
        except (IOError, OSError, EOFError, pickle.PickleError):
            pass
        return default

    def set(self, key, value, timeout=None):
        self.validate_key(key)
        fname = self._key_to_file(key)
        dirname = os.path.dirname(fname)

        if timeout is None:
            timeout = self.default_timeout

        self._cull()

        try:
            if not os.path.exists(dirname):
                os.makedirs(dirname)

            f = open(fname, 'wb')
            try:
                now = time.time()
                pickle.dump(now + timeout, f, pickle.HIGHEST_PROTOCOL)
                pickle.dump(value, f, pickle.HIGHEST_PROTOCOL)
            finally:
                f.close()
        except (IOError, OSError):
            pass

    def delete(self, key):
        self.validate_key(key)
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
        self.validate_key(key)
        fname = self._key_to_file(key)
        try:
            f = open(fname, 'rb')
            try:
                exp = pickle.load(f)
                now = time.time()
                if exp < now:
                    self._delete(fname)
                    return False
                else:
                    return True
            finally:
                f.close()
        except (IOError, OSError, EOFError, pickle.PickleError):
            return False

    def _cull(self):
        if int(self._num_entries) < self._max_entries:
            return

        try:
            filelist = sorted(os.listdir(self._dir))
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

    def clear(self):
        try:
            shutil.rmtree(self._dir)
        except (IOError, OSError):
            pass
