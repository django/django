from __future__ import with_statement
import hashlib
import os
import posixpath
import re

from django.conf import settings
from django.core.cache import (get_cache, InvalidCacheBackendError,
                               cache as default_cache)
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.utils.encoding import force_unicode
from django.utils.functional import LazyObject
from django.utils.importlib import import_module
from django.utils.datastructures import SortedDict

from django.contrib.staticfiles.utils import check_settings, matches_patterns


class StaticFilesStorage(FileSystemStorage):
    """
    Standard file system storage for static files.

    The defaults for ``location`` and ``base_url`` are
    ``STATIC_ROOT`` and ``STATIC_URL``.
    """
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.STATIC_ROOT
        if base_url is None:
            base_url = settings.STATIC_URL
        if not location:
            raise ImproperlyConfigured("You're using the staticfiles app "
                "without having set the STATIC_ROOT setting.")
        # check for None since we might use a root URL (``/``)
        if base_url is None:
            raise ImproperlyConfigured("You're using the staticfiles app "
                "without having set the STATIC_URL setting.")
        check_settings()
        super(StaticFilesStorage, self).__init__(location, base_url,
                                                 *args, **kwargs)


class CachedFilesMixin(object):
    patterns = (
        ("*.css", (
            r"""(url\(['"]{0,1}\s*(.*?)["']{0,1}\))""",
            r"""(@import\s*["']\s*(.*?)["'])""",
        )),
    )

    def __init__(self, *args, **kwargs):
        super(CachedFilesMixin, self).__init__(*args, **kwargs)
        try:
            self.cache = get_cache('staticfiles')
        except InvalidCacheBackendError:
            # Use the default backend
            self.cache = default_cache
        self._patterns = SortedDict()
        for extension, patterns in self.patterns:
            for pattern in patterns:
                compiled = re.compile(pattern)
                self._patterns.setdefault(extension, []).append(compiled)

    def hashed_name(self, name, content=None):
        if content is None:
            if not self.exists(name):
                raise ValueError("The file '%s' could not be found with %r." %
                                 (name, self))
            try:
                content = self.open(name)
            except IOError:
                # Handle directory paths
                return name
        path, filename = os.path.split(name)
        root, ext = os.path.splitext(filename)
        # Get the MD5 hash of the file
        md5 = hashlib.md5()
        for chunk in content.chunks():
            md5.update(chunk)
        md5sum = md5.hexdigest()[:12]
        return os.path.join(path, u"%s.%s%s" % (root, md5sum, ext))

    def cache_key(self, name):
        return u'staticfiles:cache:%s' % name

    def url(self, name, force=False):
        """
        Returns the real URL in DEBUG mode.
        """
        if settings.DEBUG and not force:
            return super(CachedFilesMixin, self).url(name)
        cache_key = self.cache_key(name)
        hashed_name = self.cache.get(cache_key)
        if hashed_name is None:
            hashed_name = self.hashed_name(name)
        return super(CachedFilesMixin, self).url(hashed_name)

    def url_converter(self, name):
        """
        Returns the custom URL converter for the given file name.
        """
        def converter(matchobj):
            """
            Converts the matched URL depending on the parent level (`..`)
            and returns the normalized and hashed URL using the url method
            of the storage.
            """
            matched, url = matchobj.groups()
            # Completely ignore http(s) prefixed URLs
            if url.startswith(('http', 'https')):
                return matched
            name_parts = name.split('/')
            # Using posix normpath here to remove duplicates
            result = url_parts = posixpath.normpath(url).split('/')
            level = url.count('..')
            if level:
                result = name_parts[:-level - 1] + url_parts[level:]
            elif name_parts[:-1]:
                result = name_parts[:-1] + url_parts[-1:]
            joined_result = '/'.join(result)
            hashed_url = self.url(joined_result, force=True)
            # Return the hashed and normalized version to the file
            return 'url("%s")' % hashed_url
        return converter

    def post_process(self, paths, dry_run=False, **options):
        """
        Post process the given list of files (called from collectstatic).
        """
        processed_files = []
        # don't even dare to process the files if we're in dry run mode
        if dry_run:
            return processed_files

        # delete cache of all handled paths
        self.cache.delete_many([self.cache_key(path) for path in paths])

        # only try processing the files we have patterns for
        matches = lambda path: matches_patterns(path, self._patterns.keys())
        processing_paths = [path for path in paths if matches(path)]

        # then sort the files by the directory level
        path_level = lambda name: len(name.split(os.sep))
        for name in sorted(paths, key=path_level, reverse=True):

            # first get a hashed name for the given file
            hashed_name = self.hashed_name(name)

            with self.open(name) as original_file:
                # then get the original's file content
                content = original_file.read()

                # to apply each replacement pattern on the content
                if name in processing_paths:
                    converter = self.url_converter(name)
                    for patterns in self._patterns.values():
                        for pattern in patterns:
                            content = pattern.sub(converter, content)

                # then save the processed result
                if self.exists(hashed_name):
                    self.delete(hashed_name)

                saved_name = self._save(hashed_name, ContentFile(content))
                hashed_name = force_unicode(saved_name.replace('\\', '/'))
                processed_files.append(hashed_name)

                # and then set the cache accordingly
                self.cache.set(self.cache_key(name), hashed_name)

        return processed_files


class CachedStaticFilesStorage(CachedFilesMixin, StaticFilesStorage):
    """
    A static file system storage backend which also saves
    hashed copies of the files it saves.
    """
    pass


class AppStaticStorage(FileSystemStorage):
    """
    A file system storage backend that takes an app module and works
    for the ``static`` directory of it.
    """
    prefix = None
    source_dir = 'static'

    def __init__(self, app, *args, **kwargs):
        """
        Returns a static file storage if available in the given app.
        """
        # app is the actual app module
        mod = import_module(app)
        mod_path = os.path.dirname(mod.__file__)
        location = os.path.join(mod_path, self.source_dir)
        super(AppStaticStorage, self).__init__(location, *args, **kwargs)


class ConfiguredStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class(settings.STATICFILES_STORAGE)()

staticfiles_storage = ConfiguredStorage()
