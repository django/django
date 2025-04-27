"File-based cache backend"

import glob
import os
import pathlib
import pickle
import random
import tempfile
import time
import zlib
from hashlib import md5

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.core.checks import Warning
from django.core.files import locks
from django.core.files.move import file_move_safe


class FileBasedCache(BaseCache):
    cache_suffix = ".djcache"
    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, dir, params):
        super().__init__(params)
        self._dir = os.path.abspath(dir)
        self._createdir()

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        if self.has_key(key, version):
            return False
        self.set(key, value, timeout, version)
        return True

    def get(self, key, default=None, version=None):
        fname = self._key_to_file(key, version)
        try:
            with open(fname, "rb") as f:
                if not self._is_expired(f):
                    return pickle.loads(zlib.decompress(f.read()))
        except FileNotFoundError:
            pass
        return default

    def check(self, alias, config, **kwargs):
        return [
            *self._check_cache_location_is_not_exposed(alias, config),
            *self._check_location_is_not_relative(alias, config),
        ]

    def _check_cache_location_is_not_exposed(self, alias, config):
        errors = []
        for name in ("MEDIA_ROOT", "STATIC_ROOT", "STATICFILES_DIRS"):
            setting = getattr(settings, name, None)
            if not setting:
                continue
            if name == "STATICFILES_DIRS":
                paths = set()
                for staticfiles_dir in setting:
                    if isinstance(staticfiles_dir, (list, tuple)):
                        _, staticfiles_dir = staticfiles_dir
                    paths.add(pathlib.Path(staticfiles_dir).resolve())
            else:
                paths = {pathlib.Path(setting).resolve()}
            cache_path = pathlib.Path(self._dir).resolve()
            if any(path == cache_path for path in paths):
                relation = "matches"
            elif any(path in cache_path.parents for path in paths):
                relation = "is inside"
            elif any(cache_path in path.parents for path in paths):
                relation = "contains"
            else:
                continue
            errors.append(
                Warning(
                    f"Your '{alias}' cache configuration might expose your cache "
                    f"or lead to corruption of your data because its LOCATION "
                    f"{relation} {name}.",
                    id="caches.W002",
                )
            )
        return errors

    def _check_location_is_not_relative(self, alias, config):
        location = config["LOCATION"]
        if not os.path.isabs(location):
            return [
                Warning(
                    f"Your '{alias}' cache LOCATION path is relative. Use an "
                    f"absolute path instead.",
                    id="caches.W003",
                )
            ]
        return []

    def _write_content(self, file, timeout, value):
        expiry = self.get_backend_timeout(timeout)
        file.write(pickle.dumps(expiry, self.pickle_protocol))
        file.write(zlib.compress(pickle.dumps(value, self.pickle_protocol)))

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        self._createdir()  # Cache dir can be deleted at any time.
        fname = self._key_to_file(key, version)
        self._cull()  # make some room if necessary
        fd, tmp_path = tempfile.mkstemp(dir=self._dir)
        renamed = False
        try:
            with open(fd, "wb") as f:
                self._write_content(f, timeout, value)
            file_move_safe(tmp_path, fname, allow_overwrite=True)
            renamed = True
        finally:
            if not renamed:
                os.remove(tmp_path)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        try:
            with open(self._key_to_file(key, version), "r+b") as f:
                try:
                    locks.lock(f, locks.LOCK_EX)
                    if self._is_expired(f):
                        return False
                    else:
                        previous_value = pickle.loads(zlib.decompress(f.read()))
                        f.seek(0)
                        self._write_content(f, timeout, previous_value)
                        return True
                finally:
                    locks.unlock(f)
        except FileNotFoundError:
            return False

    def delete(self, key, version=None):
        return self._delete(self._key_to_file(key, version))

    def _delete(self, fname):
        if not fname.startswith(self._dir) or not os.path.exists(fname):
            return False
        try:
            os.remove(fname)
        except FileNotFoundError:
            # The file may have been removed by another process.
            return False
        return True

    def has_key(self, key, version=None):
        fname = self._key_to_file(key, version)
        try:
            with open(fname, "rb") as f:
                return not self._is_expired(f)
        except FileNotFoundError:
            return False

    def _cull(self):
        """
        Remove random cache entries if max_entries is reached at a ratio
        of num_entries / cull_frequency. A value of 0 for CULL_FREQUENCY means
        that the entire cache will be purged.
        """
        filelist = self._list_cache_files()
        num_entries = len(filelist)
        if num_entries < self._max_entries:
            return  # return early if no culling is required
        if self._cull_frequency == 0:
            return self.clear()  # Clear the cache when CULL_FREQUENCY = 0
        # Delete a random selection of entries
        filelist = random.sample(filelist, int(num_entries / self._cull_frequency))
        for fname in filelist:
            self._delete(fname)

    def _createdir(self):
        # Set the umask because os.makedirs() doesn't apply the "mode" argument
        # to intermediate-level directories.
        old_umask = os.umask(0o077)
        try:
            os.makedirs(self._dir, 0o700, exist_ok=True)
        finally:
            os.umask(old_umask)

    def _key_to_file(self, key, version=None):
        """
        Convert a key into a cache file path. Basically this is the
        root cache path joined with the md5sum of the key and a suffix.
        """
        key = self.make_and_validate_key(key, version=version)
        return os.path.join(
            self._dir,
            "".join(
                [
                    md5(key.encode(), usedforsecurity=False).hexdigest(),
                    self.cache_suffix,
                ]
            ),
        )

    def clear(self):
        """
        Remove all the cache files.
        """
        for fname in self._list_cache_files():
            self._delete(fname)

    def _is_expired(self, f):
        """
        Take an open cache file `f` and delete it if it's expired.
        """
        try:
            exp = pickle.load(f)
        except EOFError:
            exp = 0  # An empty file is considered expired.
        if exp is not None and exp < time.time():
            f.close()  # On Windows a file has to be closed before deleting
            self._delete(f.name)
            return True
        return False

    def _list_cache_files(self):
        """
        Get a list of paths to all the cache files. These are all the files
        in the root cache dir that end on the cache_suffix.
        """
        return [
            os.path.join(self._dir, fname)
            for fname in glob.glob(f"*{self.cache_suffix}", root_dir=self._dir)
        ]
