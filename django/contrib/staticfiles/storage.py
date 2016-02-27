from __future__ import unicode_literals

import hashlib
import json
import os
import posixpath
import re
from collections import OrderedDict

from django.conf import settings
from django.contrib.staticfiles.utils import check_settings, matches_patterns
from django.core.cache import (
    InvalidCacheBackendError, cache as default_cache, caches,
)
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.utils.encoding import force_bytes, force_text
from django.utils.functional import LazyObject
from django.utils.six import iteritems
from django.utils.six.moves.urllib.parse import (
    unquote, urldefrag, urlsplit, urlunsplit,
)


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
        # FileSystemStorage fallbacks to MEDIA_ROOT when location
        # is empty, so we restore the empty value.
        if not location:
            self.base_location = None
            self.location = None

    def path(self, name):
        if not self.location:
            raise ImproperlyConfigured("You're using the staticfiles app "
                                       "without having set the STATIC_ROOT "
                                       "setting to a filesystem path.")
        return super(StaticFilesStorage, self).path(name)


class HashedFilesMixin(object):
    default_template = """url("%s")"""
    patterns = (
        ("*.css", (
            r"""(url\(['"]{0,1}\s*(.*?)["']{0,1}\))""",
            (r"""(@import\s*["']\s*(.*?)["'])""", """@import url("%s")"""),
        )),
    )

    def __init__(self, *args, **kwargs):
        super(HashedFilesMixin, self).__init__(*args, **kwargs)
        self._patterns = OrderedDict()
        self.hashed_files = {}
        for extension, patterns in self.patterns:
            for pattern in patterns:
                if isinstance(pattern, (tuple, list)):
                    pattern, template = pattern
                else:
                    template = self.default_template
                compiled = re.compile(pattern, re.IGNORECASE)
                self._patterns.setdefault(extension, []).append((compiled, template))

    def file_hash(self, name, content=None):
        """
        Return a hash of the file with the given name and optional content.
        """
        if content is None:
            return None
        md5 = hashlib.md5()
        for chunk in content.chunks():
            md5.update(chunk)
        return md5.hexdigest()[:12]

    def hashed_name(self, name, content=None):
        parsed_name = urlsplit(unquote(name))
        clean_name = parsed_name.path.strip()
        opened = False
        if content is None:
            if not self.exists(clean_name):
                raise ValueError("The file '%s' could not be found with %r." %
                                 (clean_name, self))
            try:
                content = self.open(clean_name)
            except IOError:
                # Handle directory paths and fragments
                return name
            opened = True
        try:
            file_hash = self.file_hash(clean_name, content)
        finally:
            if opened:
                content.close()
        path, filename = os.path.split(clean_name)
        root, ext = os.path.splitext(filename)
        if file_hash is not None:
            file_hash = ".%s" % file_hash
        hashed_name = os.path.join(path, "%s%s%s" %
                                   (root, file_hash, ext))
        unparsed_name = list(parsed_name)
        unparsed_name[2] = hashed_name
        # Special casing for a @font-face hack, like url(myfont.eot?#iefix")
        # http://www.fontspring.com/blog/the-new-bulletproof-font-face-syntax
        if '?#' in name and not unparsed_name[3]:
            unparsed_name[2] += '?'
        return urlunsplit(unparsed_name)

    def url(self, name, force=False):
        """
        Return the real URL in DEBUG mode.
        """
        if settings.DEBUG and not force:
            hashed_name, fragment = name, ''
        else:
            clean_name, fragment = urldefrag(name)
            if urlsplit(clean_name).path.endswith('/'):  # don't hash paths
                hashed_name = name
            else:
                hashed_name = self.stored_name(clean_name)

        final_url = super(HashedFilesMixin, self).url(hashed_name)

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

    def url_converter(self, name, template=None):
        """
        Return the custom URL converter for the given file name.
        """
        if template is None:
            template = self.default_template

        def converter(matchobj):
            """
            Convert the matched URL to a normalized and hashed URL.

            This requires figuring out which files the matched URL resolves
            to and calling the url() method of the storage.
            """
            matched, url = matchobj.groups()

            # Ignore absolute/protocol-relative, fragments and data-uri URLs.
            if url.startswith(('http:', 'https:', '//', '#', 'data:')):
                return matched

            # Ignore absolute URLs that don't point to a static file (dynamic
            # CSS / JS?). Note that STATIC_URL cannot be empty.
            if url.startswith('/') and not url.startswith(settings.STATIC_URL):
                return matched

            # Strip off the fragment so a path-like fragment won't interfere.
            url_path, fragment = urldefrag(url)

            if url_path.startswith('/'):
                # Otherwise the condition above would have returned prematurely.
                assert url_path.startswith(settings.STATIC_URL)
                target_name = url_path[len(settings.STATIC_URL):]
            else:
                # We're using the posixpath module to mix paths and URLs conveniently.
                source_name = name if os.sep == '/' else name.replace(os.sep, '/')
                target_name = posixpath.join(posixpath.dirname(source_name), url_path)

            # Determine the hashed name of the target file with the storage backend.
            hashed_url = self.url(unquote(target_name), force=True)

            transformed_url = '/'.join(url_path.split('/')[:-1] + hashed_url.split('/')[-1:])

            # Restore the fragment that was stripped off earlier.
            if fragment:
                transformed_url += ('?#' if '?#' in url else '#') + fragment

            # Return the hashed version to the file
            return template % unquote(transformed_url)

        return converter

    def post_process(self, paths, dry_run=False, **options):
        """
        Post process the given OrderedDict of files (called from collectstatic).

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
        hashed_files = OrderedDict()

        # build a list of adjustable files
        adjustable_paths = [
            path for path in paths
            if matches_patterns(path, self._patterns.keys())
        ]

        # then sort the files by the directory level
        def path_level(name):
            return len(name.split(os.sep))

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
                    content = original_file.read().decode(settings.FILE_CHARSET)
                    for extension, patterns in iteritems(self._patterns):
                        if matches_patterns(path, (extension,)):
                            for pattern, template in patterns:
                                converter = self.url_converter(name, template)
                                try:
                                    content = pattern.sub(converter, content)
                                except ValueError as exc:
                                    yield name, None, exc
                    if hashed_file_exists:
                        self.delete(hashed_name)
                    # then save the processed result
                    content_file = ContentFile(force_bytes(content))
                    saved_name = self._save(hashed_name, content_file)
                    hashed_name = force_text(self.clean_name(saved_name))
                    processed = True
                else:
                    # or handle the case in which neither processing nor
                    # a change to the original file happened
                    if not hashed_file_exists:
                        processed = True
                        saved_name = self._save(hashed_name, original_file)
                        hashed_name = force_text(self.clean_name(saved_name))

                # and then set the cache accordingly
                hashed_files[self.hash_key(name)] = hashed_name
                yield name, hashed_name, processed

        # Finally store the processed paths
        self.hashed_files.update(hashed_files)

    def clean_name(self, name):
        return name.replace('\\', '/')

    def hash_key(self, name):
        return name

    def stored_name(self, name):
        hash_key = self.hash_key(name)
        cache_name = self.hashed_files.get(hash_key)
        if cache_name is None:
            cache_name = self.clean_name(self.hashed_name(name))
            # store the hashed name if there was a miss, e.g.
            # when the files are still processed
            self.hashed_files[hash_key] = cache_name
        return cache_name


class ManifestFilesMixin(HashedFilesMixin):
    manifest_version = '1.0'  # the manifest format standard
    manifest_name = 'staticfiles.json'

    def __init__(self, *args, **kwargs):
        super(ManifestFilesMixin, self).__init__(*args, **kwargs)
        self.hashed_files = self.load_manifest()

    def read_manifest(self):
        try:
            with self.open(self.manifest_name) as manifest:
                return manifest.read().decode('utf-8')
        except IOError:
            return None

    def load_manifest(self):
        content = self.read_manifest()
        if content is None:
            return OrderedDict()
        try:
            stored = json.loads(content, object_pairs_hook=OrderedDict)
        except ValueError:
            pass
        else:
            version = stored.get('version')
            if version == '1.0':
                return stored.get('paths', OrderedDict())
        raise ValueError("Couldn't load manifest '%s' (version %s)" %
                         (self.manifest_name, self.manifest_version))

    def post_process(self, *args, **kwargs):
        self.hashed_files = OrderedDict()
        all_post_processed = super(ManifestFilesMixin,
                                   self).post_process(*args, **kwargs)
        for post_processed in all_post_processed:
            yield post_processed
        self.save_manifest()

    def save_manifest(self):
        payload = {'paths': self.hashed_files, 'version': self.manifest_version}
        if self.exists(self.manifest_name):
            self.delete(self.manifest_name)
        contents = json.dumps(payload).encode('utf-8')
        self._save(self.manifest_name, ContentFile(contents))


class _MappingCache(object):
    """
    A small dict-like wrapper for a given cache backend instance.
    """
    def __init__(self, cache):
        self.cache = cache

    def __setitem__(self, key, value):
        self.cache.set(key, value)

    def __getitem__(self, key):
        value = self.cache.get(key)
        if value is None:
            raise KeyError("Couldn't find a file name '%s'" % key)
        return value

    def clear(self):
        self.cache.clear()

    def update(self, data):
        self.cache.set_many(data)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


class CachedFilesMixin(HashedFilesMixin):
    def __init__(self, *args, **kwargs):
        super(CachedFilesMixin, self).__init__(*args, **kwargs)
        try:
            self.hashed_files = _MappingCache(caches['staticfiles'])
        except InvalidCacheBackendError:
            # Use the default backend
            self.hashed_files = _MappingCache(default_cache)

    def hash_key(self, name):
        key = hashlib.md5(force_bytes(self.clean_name(name))).hexdigest()
        return 'staticfiles:%s' % key


class CachedStaticFilesStorage(CachedFilesMixin, StaticFilesStorage):
    """
    A static file system storage backend which also saves
    hashed copies of the files it saves.
    """
    pass


class ManifestStaticFilesStorage(ManifestFilesMixin, StaticFilesStorage):
    """
    A static file system storage backend which also saves
    hashed copies of the files it saves.
    """
    pass


class ConfiguredStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class(settings.STATICFILES_STORAGE)()

staticfiles_storage = ConfiguredStorage()
