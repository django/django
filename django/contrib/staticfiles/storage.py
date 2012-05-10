from __future__ import with_statement
import hashlib
import os
import posixpath
import re
from urllib import unquote
from urlparse import urlsplit, urlunsplit, urldefrag

from django.conf import settings
from django.core.cache import (get_cache, InvalidCacheBackendError,
                               cache as default_cache)
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_unicode, smart_str
from django.utils.functional import LazyObject
from django.utils.importlib import import_module

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
        check_settings(base_url)
        super(StaticFilesStorage, self).__init__(location, base_url,
                                                 *args, **kwargs)

    def path(self, name):
        if not self.location:
            raise ImproperlyConfigured("You're using the staticfiles app "
                                       "without having set the STATIC_ROOT "
                                       "setting to a filesystem path.")
        return super(StaticFilesStorage, self).path(name)


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
        parsed_name = urlsplit(unquote(name))
        clean_name = parsed_name.path.strip()
        if content is None:
            if not self.exists(clean_name):
                raise ValueError("The file '%s' could not be found with %r." %
                                 (clean_name, self))
            try:
                content = self.open(clean_name)
            except IOError:
                # Handle directory paths and fragments
                return name
        path, filename = os.path.split(clean_name)
        root, ext = os.path.splitext(filename)
        # Get the MD5 hash of the file
        md5 = hashlib.md5()
        for chunk in content.chunks():
            md5.update(chunk)
        md5sum = md5.hexdigest()[:12]
        hashed_name = os.path.join(path, u"%s.%s%s" %
                                   (root, md5sum, ext))
        unparsed_name = list(parsed_name)
        unparsed_name[2] = hashed_name
        # Special casing for a @font-face hack, like url(myfont.eot?#iefix")
        # http://www.fontspring.com/blog/the-new-bulletproof-font-face-syntax
        if '?#' in name and not unparsed_name[3]:
            unparsed_name[2] += '?'
        return urlunsplit(unparsed_name)

    def cache_key(self, name):
        return u'staticfiles:%s' % hashlib.md5(smart_str(name)).hexdigest()

    def url(self, name, force=False):
        """
        Returns the real URL in DEBUG mode.
        """
        if settings.DEBUG and not force:
            hashed_name, fragment = name, ''
        else:
            clean_name, fragment = urldefrag(name)
            if urlsplit(clean_name).path.endswith('/'):  # don't hash paths
                hashed_name = name
            else:
                cache_key = self.cache_key(name)
                hashed_name = self.cache.get(cache_key)
                if hashed_name is None:
                    hashed_name = self.hashed_name(clean_name).replace('\\', '/')
                    # set the cache if there was a miss
                    # (e.g. if cache server goes down)
                    self.cache.set(cache_key, hashed_name)

        final_url = super(CachedFilesMixin, self).url(hashed_name)

        # Special casing for a @font-face hack, like url(myfont.eot?#iefix")
        # http://www.fontspring.com/blog/the-new-bulletproof-font-face-syntax
        query_fragment = '?#' in name  # [sic!]
        if fragment or query_fragment:
            urlparts = list(urlsplit(final_url))
            if fragment and not urlparts[4]:
                urlparts[4] = fragment
            if query_fragment and not urlparts[3]:
                urlparts[2] += '?'
            final_url = urlunsplit(urlparts)

        return unquote(final_url)

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
            # Completely ignore http(s) prefixed URLs,
            # fragments and data-uri URLs
            if url.startswith(('#', 'http:', 'https:', 'data:')):
                return matched
            name_parts = name.split(os.sep)
            # Using posix normpath here to remove duplicates
            url = posixpath.normpath(url)
            url_parts = url.split('/')
            parent_level, sub_level = url.count('..'), url.count('/')
            if url.startswith('/'):
                sub_level -= 1
                url_parts = url_parts[1:]
            if parent_level or not url.startswith('/'):
                start, end = parent_level + 1, parent_level
            else:
                if sub_level:
                    if sub_level == 1:
                        parent_level -= 1
                    start, end = parent_level, 1
                else:
                    start, end = 1, sub_level - 1
            joined_result = '/'.join(name_parts[:-start] + url_parts[end:])
            hashed_url = self.url(unquote(joined_result), force=True)
            file_name = hashed_url.split('/')[-1:]
            relative_url = '/'.join(url.split('/')[:-1] + file_name)

            # Return the hashed version to the file
            return 'url("%s")' % unquote(relative_url)
        return converter

    def post_process(self, paths, dry_run=False, **options):
        """
        Post process the given list of files (called from collectstatic).

        Processing is actually two separate operations:

        1. renaming files to include a hash of their content for cache-busting,
           and copying those files to the target storage.
        2. adjusting files which contain references to other files so they
           refer to the cache-busting filenames.

        If either of these are performed on a file, then that file is considered
        post-processed.
        """
        # don't even dare to process the files if we're in dry run mode
        if dry_run:
            return

        # where to store the new paths
        hashed_paths = {}

        # build a list of adjustable files
        matches = lambda path: matches_patterns(path, self._patterns.keys())
        adjustable_paths = [path for path in paths if matches(path)]

        # then sort the files by the directory level
        path_level = lambda name: len(name.split(os.sep))
        for name in sorted(paths.keys(), key=path_level, reverse=True):

            # use the original, local file, not the copied-but-unprocessed
            # file, which might be somewhere far away, like S3
            storage, path = paths[name]
            with storage.open(path) as original_file:

                # generate the hash with the original content, even for
                # adjustable files.
                hashed_name = self.hashed_name(name, original_file)

                # then get the original's file content..
                if hasattr(original_file, 'seek'):
                    original_file.seek(0)

                hashed_file_exists = self.exists(hashed_name)
                processed = False

                # ..to apply each replacement pattern to the content
                if name in adjustable_paths:
                    content = original_file.read()
                    converter = self.url_converter(name)
                    for patterns in self._patterns.values():
                        for pattern in patterns:
                            content = pattern.sub(converter, content)
                    if hashed_file_exists:
                        self.delete(hashed_name)
                    # then save the processed result
                    content_file = ContentFile(smart_str(content))
                    saved_name = self._save(hashed_name, content_file)
                    hashed_name = force_unicode(saved_name.replace('\\', '/'))
                    processed = True
                else:
                    # or handle the case in which neither processing nor
                    # a change to the original file happened
                    if not hashed_file_exists:
                        processed = True
                        saved_name = self._save(hashed_name, original_file)
                        hashed_name = force_unicode(saved_name.replace('\\', '/'))

                # and then set the cache accordingly
                hashed_paths[self.cache_key(name)] = hashed_name
                yield name, hashed_name, processed

        # Finally set the cache
        self.cache.set_many(hashed_paths)


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
