import json
import os
import posixpath
import re
from urllib.parse import unquote, urldefrag, urlsplit, urlunsplit

from django.conf import settings
from django.contrib.staticfiles.utils import check_settings, matches_patterns
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, get_storage_class
from django.utils.crypto import md5
from django.utils.functional import LazyObject


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
        super().__init__(location, base_url, *args, **kwargs)
        # FileSystemStorage fallbacks to MEDIA_ROOT when location
        # is empty, so we restore the empty value.
        if not location:
            self.base_location = None
            self.location = None

    def path(self, name):
        if not self.location:
            raise ImproperlyConfigured(
                "You're using the staticfiles app "
                "without having set the STATIC_ROOT "
                "setting to a filesystem path."
            )
        return super().path(name)


class HashedFilesMixin:
    default_template = """url("%(url)s")"""
    max_post_process_passes = 5
    patterns = (
        (
            "*.css",
            (
                r"""(?P<matched>url\(['"]{0,1}\s*(?P<url>.*?)["']{0,1}\))""",
                (
                    r"""(?P<matched>@import\s*["']\s*(?P<url>.*?)["'])""",
                    """@import url("%(url)s")""",
                ),
                (
                    (
                        r"(?m)(?P<matched>)^(/\*#[ \t]"
                        r"(?-i:sourceMappingURL)=(?P<url>.*)[ \t]*\*/)$"
                    ),
                    "/*# sourceMappingURL=%(url)s */",
                ),
            ),
        ),
        (
            "*.js",
            (
                (
                    r"(?m)(?P<matched>)^(//# (?-i:sourceMappingURL)=(?P<url>.*))$",
                    "//# sourceMappingURL=%(url)s",
                ),
                (
                    (
                        r"""(?P<matched>import(?s:(?P<import>[\s\{].*?))"""
                        r"""\s*from\s*['"](?P<url>[\.\/].*?)["']\s*;)"""
                    ),
                    """import%(import)s from "%(url)s";""",
                ),
                (
                    (
                        r"""(?P<matched>export(?s:(?P<exports>[\s\{].*?))"""
                        r"""\s*from\s*["'](?P<url>[\.\/].*?)["']\s*;)"""
                    ),
                    """export%(exports)s from "%(url)s";""",
                ),
                (
                    r"""(?P<matched>import\s*['"](?P<url>[\.\/].*?)["']\s*;)""",
                    """import"%(url)s";""",
                ),
                (
                    r"""(?P<matched>import\(["'](?P<url>.*?)["']\))""",
                    """import("%(url)s")""",
                ),
            ),
        ),
    )
    keep_intermediate_files = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._patterns = {}
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
        hasher = md5(usedforsecurity=False)
        for chunk in content.chunks():
            hasher.update(chunk)
        return hasher.hexdigest()[:12]

    def hashed_name(self, name, content=None, filename=None):
        # `filename` is the name of file to hash if `content` isn't given.
        # `name` is the base name to construct the new hashed filename from.
        parsed_name = urlsplit(unquote(name))
        clean_name = parsed_name.path.strip()
        filename = (filename and urlsplit(unquote(filename)).path.strip()) or clean_name
        opened = content is None
        if opened:
            if not self.exists(filename):
                raise ValueError(
                    "The file '%s' could not be found with %r." % (filename, self)
                )
            try:
                content = self.open(filename)
            except OSError:
                # Handle directory paths and fragments
                return name
        try:
            file_hash = self.file_hash(clean_name, content)
        finally:
            if opened:
                content.close()
        path, filename = os.path.split(clean_name)
        root, ext = os.path.splitext(filename)
        file_hash = (".%s" % file_hash) if file_hash else ""
        hashed_name = os.path.join(path, "%s%s%s" % (root, file_hash, ext))
        unparsed_name = list(parsed_name)
        unparsed_name[2] = hashed_name
        # Special casing for a @font-face hack, like url(myfont.eot?#iefix")
        # http://www.fontspring.com/blog/the-new-bulletproof-font-face-syntax
        if "?#" in name and not unparsed_name[3]:
            unparsed_name[2] += "?"
        return urlunsplit(unparsed_name)

    def _url(self, hashed_name_func, name, force=False, hashed_files=None):
        """
        Return the non-hashed URL in DEBUG mode.
        """
        if settings.DEBUG and not force:
            hashed_name, fragment = name, ""
        else:
            clean_name, fragment = urldefrag(name)
            if urlsplit(clean_name).path.endswith("/"):  # don't hash paths
                hashed_name = name
            else:
                args = (clean_name,)
                if hashed_files is not None:
                    args += (hashed_files,)
                hashed_name = hashed_name_func(*args)

        final_url = super().url(hashed_name)

        # Special casing for a @font-face hack, like url(myfont.eot?#iefix")
        # http://www.fontspring.com/blog/the-new-bulletproof-font-face-syntax
        query_fragment = "?#" in name  # [sic!]
        if fragment or query_fragment:
            urlparts = list(urlsplit(final_url))
            if fragment and not urlparts[4]:
                urlparts[4] = fragment
            if query_fragment and not urlparts[3]:
                urlparts[2] += "?"
            final_url = urlunsplit(urlparts)

        return unquote(final_url)

    def url(self, name, force=False):
        """
        Return the non-hashed URL in DEBUG mode.
        """
        return self._url(self.stored_name, name, force)

    def url_converter(self, name, hashed_files, template=None):
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
            matches = matchobj.groupdict()
            matched = matches["matched"]
            url = matches["url"]

            # Ignore absolute/protocol-relative and data-uri URLs.
            if re.match(r"^[a-z]+:", url):
                return matched

            # Ignore absolute URLs that don't point to a static file (dynamic
            # CSS / JS?). Note that STATIC_URL cannot be empty.
            if url.startswith("/") and not url.startswith(settings.STATIC_URL):
                return matched

            # Strip off the fragment so a path-like fragment won't interfere.
            url_path, fragment = urldefrag(url)

            # Ignore URLs without a path
            if not url_path:
                return matched

            if url_path.startswith("/"):
                # Otherwise the condition above would have returned prematurely.
                assert url_path.startswith(settings.STATIC_URL)
                target_name = url_path[len(settings.STATIC_URL) :]
            else:
                # We're using the posixpath module to mix paths and URLs conveniently.
                source_name = name if os.sep == "/" else name.replace(os.sep, "/")
                target_name = posixpath.join(posixpath.dirname(source_name), url_path)

            # Determine the hashed name of the target file with the storage backend.
            hashed_url = self._url(
                self._stored_name,
                unquote(target_name),
                force=True,
                hashed_files=hashed_files,
            )

            transformed_url = "/".join(
                url_path.split("/")[:-1] + hashed_url.split("/")[-1:]
            )

            # Restore the fragment that was stripped off earlier.
            if fragment:
                transformed_url += ("?#" if "?#" in url else "#") + fragment

            # Return the hashed version to the file
            matches["url"] = unquote(transformed_url)
            return template % matches

        return converter

    def post_process(self, paths, dry_run=False, **options):
        """
        Post process the given dictionary of files (called from collectstatic).

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
        hashed_files = {}

        # build a list of adjustable files
        adjustable_paths = [
            path for path in paths if matches_patterns(path, self._patterns)
        ]

        # Adjustable files to yield at end, keyed by the original path.
        processed_adjustable_paths = {}

        # Do a single pass first. Post-process all files once, yielding not
        # adjustable files and exceptions, and collecting adjustable files.
        for name, hashed_name, processed, _ in self._post_process(
            paths, adjustable_paths, hashed_files
        ):
            if name not in adjustable_paths or isinstance(processed, Exception):
                yield name, hashed_name, processed
            else:
                processed_adjustable_paths[name] = (name, hashed_name, processed)

        paths = {path: paths[path] for path in adjustable_paths}
        substitutions = False

        for i in range(self.max_post_process_passes):
            substitutions = False
            for name, hashed_name, processed, subst in self._post_process(
                paths, adjustable_paths, hashed_files
            ):
                # Overwrite since hashed_name may be newer.
                processed_adjustable_paths[name] = (name, hashed_name, processed)
                substitutions = substitutions or subst

            if not substitutions:
                break

        if substitutions:
            yield "All", None, RuntimeError("Max post-process passes exceeded.")

        # Store the processed paths
        self.hashed_files.update(hashed_files)

        # Yield adjustable files with final, hashed name.
        yield from processed_adjustable_paths.values()

    def _post_process(self, paths, adjustable_paths, hashed_files):
        # Sort the files by directory level
        def path_level(name):
            return len(name.split(os.sep))

        for name in sorted(paths, key=path_level, reverse=True):
            substitutions = True
            # use the original, local file, not the copied-but-unprocessed
            # file, which might be somewhere far away, like S3
            storage, path = paths[name]
            with storage.open(path) as original_file:
                cleaned_name = self.clean_name(name)
                hash_key = self.hash_key(cleaned_name)

                # generate the hash with the original content, even for
                # adjustable files.
                if hash_key not in hashed_files:
                    hashed_name = self.hashed_name(name, original_file)
                else:
                    hashed_name = hashed_files[hash_key]

                # then get the original's file content..
                if hasattr(original_file, "seek"):
                    original_file.seek(0)

                hashed_file_exists = self.exists(hashed_name)
                processed = False

                # ..to apply each replacement pattern to the content
                if name in adjustable_paths:
                    old_hashed_name = hashed_name
                    content = original_file.read().decode("utf-8")
                    for extension, patterns in self._patterns.items():
                        if matches_patterns(path, (extension,)):
                            for pattern, template in patterns:
                                converter = self.url_converter(
                                    name, hashed_files, template
                                )
                                try:
                                    content = pattern.sub(converter, content)
                                except ValueError as exc:
                                    yield name, None, exc, False
                    if hashed_file_exists:
                        self.delete(hashed_name)
                    # then save the processed result
                    content_file = ContentFile(content.encode())
                    if self.keep_intermediate_files:
                        # Save intermediate file for reference
                        self._save(hashed_name, content_file)
                    hashed_name = self.hashed_name(name, content_file)

                    if self.exists(hashed_name):
                        self.delete(hashed_name)

                    saved_name = self._save(hashed_name, content_file)
                    hashed_name = self.clean_name(saved_name)
                    # If the file hash stayed the same, this file didn't change
                    if old_hashed_name == hashed_name:
                        substitutions = False
                    processed = True

                if not processed:
                    # or handle the case in which neither processing nor
                    # a change to the original file happened
                    if not hashed_file_exists:
                        processed = True
                        saved_name = self._save(hashed_name, original_file)
                        hashed_name = self.clean_name(saved_name)

                # and then set the cache accordingly
                hashed_files[hash_key] = hashed_name

                yield name, hashed_name, processed, substitutions

    def clean_name(self, name):
        return name.replace("\\", "/")

    def hash_key(self, name):
        return name

    def _stored_name(self, name, hashed_files):
        # Normalize the path to avoid multiple names for the same file like
        # ../foo/bar.css and ../foo/../foo/bar.css which normalize to the same
        # path.
        name = posixpath.normpath(name)
        cleaned_name = self.clean_name(name)
        hash_key = self.hash_key(cleaned_name)
        cache_name = hashed_files.get(hash_key)
        if cache_name is None:
            cache_name = self.clean_name(self.hashed_name(name))
        return cache_name

    def stored_name(self, name):
        cleaned_name = self.clean_name(name)
        hash_key = self.hash_key(cleaned_name)
        cache_name = self.hashed_files.get(hash_key)
        if cache_name:
            return cache_name
        # No cached name found, recalculate it from the files.
        intermediate_name = name
        for i in range(self.max_post_process_passes + 1):
            cache_name = self.clean_name(
                self.hashed_name(name, content=None, filename=intermediate_name)
            )
            if intermediate_name == cache_name:
                # Store the hashed name if there was a miss.
                self.hashed_files[hash_key] = cache_name
                return cache_name
            else:
                # Move on to the next intermediate file.
                intermediate_name = cache_name
        # If the cache name can't be determined after the max number of passes,
        # the intermediate files on disk may be corrupt; avoid an infinite loop.
        raise ValueError("The name '%s' could not be hashed with %r." % (name, self))


class ManifestFilesMixin(HashedFilesMixin):
    manifest_version = "1.1"  # the manifest format standard
    manifest_name = "staticfiles.json"
    manifest_strict = True
    keep_intermediate_files = False

    def __init__(self, *args, manifest_storage=None, **kwargs):
        super().__init__(*args, **kwargs)
        if manifest_storage is None:
            manifest_storage = self
        self.manifest_storage = manifest_storage
        self.hashed_files, self.manifest_hash = self.load_manifest()

    def read_manifest(self):
        try:
            with self.manifest_storage.open(self.manifest_name) as manifest:
                return manifest.read().decode()
        except FileNotFoundError:
            return None

    def load_manifest(self):
        content = self.read_manifest()
        if content is None:
            return {}, ""
        try:
            stored = json.loads(content)
        except json.JSONDecodeError:
            pass
        else:
            version = stored.get("version")
            if version in ("1.0", "1.1"):
                return stored.get("paths", {}), stored.get("hash", "")
        raise ValueError(
            "Couldn't load manifest '%s' (version %s)"
            % (self.manifest_name, self.manifest_version)
        )

    def post_process(self, *args, **kwargs):
        self.hashed_files = {}
        yield from super().post_process(*args, **kwargs)
        if not kwargs.get("dry_run"):
            self.save_manifest()

    def save_manifest(self):
        self.manifest_hash = self.file_hash(
            None, ContentFile(json.dumps(sorted(self.hashed_files.items())).encode())
        )
        payload = {
            "paths": self.hashed_files,
            "version": self.manifest_version,
            "hash": self.manifest_hash,
        }
        if self.manifest_storage.exists(self.manifest_name):
            self.manifest_storage.delete(self.manifest_name)
        contents = json.dumps(payload).encode()
        self.manifest_storage._save(self.manifest_name, ContentFile(contents))

    def stored_name(self, name):
        parsed_name = urlsplit(unquote(name))
        clean_name = parsed_name.path.strip()
        hash_key = self.hash_key(clean_name)
        cache_name = self.hashed_files.get(hash_key)
        if cache_name is None:
            if self.manifest_strict:
                raise ValueError(
                    "Missing staticfiles manifest entry for '%s'" % clean_name
                )
            cache_name = self.clean_name(self.hashed_name(name))
        unparsed_name = list(parsed_name)
        unparsed_name[2] = cache_name
        # Special casing for a @font-face hack, like url(myfont.eot?#iefix")
        # http://www.fontspring.com/blog/the-new-bulletproof-font-face-syntax
        if "?#" in name and not unparsed_name[3]:
            unparsed_name[2] += "?"
        return urlunsplit(unparsed_name)


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
