import json
import os
import posixpath
import re
from graphlib import CycleError, TopologicalSorter
from hashlib import md5
from urllib.parse import unquote, urldefrag, urlsplit, urlunsplit

from django.conf import STATICFILES_STORAGE_ALIAS, settings
from django.contrib.staticfiles.utils import check_settings, matches_patterns
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, storages
from django.utils.functional import LazyObject
from django.utils.regex_helper import _lazy_re_compile

comment_re = _lazy_re_compile(r"\/\*[^*]*\*+([^/*][^*]*\*+)*\/", re.DOTALL)
line_comment_re = _lazy_re_compile(
    r"\/\*[^*]*\*+([^/*][^*]*\*+)*\/|\/\/[^\n]*", re.DOTALL
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
    support_js_module_import_aggregation = False
    _js_module_import_aggregation_patterns = (
        "*.js",
        (
            (
                (
                    r"""(?P<matched>import"""
                    r"""(?s:(?P<import>[\s\{].*?|\*\s*as\s*\w+))"""
                    r"""\s*from\s*['"](?P<url>[./].*?)["']\s*;)"""
                ),
                """import%(import)s from "%(url)s";""",
            ),
            (
                (
                    r"""(?P<matched>export(?s:(?P<exports>[\s\{].*?))"""
                    r"""\s*from\s*["'](?P<url>[./].*?)["']\s*;)"""
                ),
                """export%(exports)s from "%(url)s";""",
            ),
            (
                r"""(?P<matched>import\s*['"](?P<url>[./].*?)["']\s*;)""",
                """import"%(url)s";""",
            ),
            (
                r"""(?P<matched>import\(["'](?P<url>.*?)["']\))""",
                """import("%(url)s")""",
            ),
        ),
    )
    patterns = (
        (
            "*.css",
            (
                r"""(?P<matched>url\((?P<quote>['"]{0,1})"""
                r"""\s*(?P<url>.*?)(?P=quote)\))""",
                (
                    r"""(?P<matched>@import\s*["']\s*(?P<url>.*?)["'])""",
                    """@import url("%(url)s")""",
                ),
                (
                    (
                        r"(?m)^(?P<matched>/\*#[ \t]"
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
                    r"(?m)^(?P<matched>//# (?-i:sourceMappingURL)=(?P<url>.*))$",
                    "//# sourceMappingURL=%(url)s",
                ),
            ),
        ),
    )

    def __init__(self, *args, **kwargs):
        if self.support_js_module_import_aggregation:
            self.patterns += (self._js_module_import_aggregation_patterns,)
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

    def get_comment_blocks(self, content, include_line_comments=False):
        """
        Return a list of (start, end) tuples for each comment block.
        """
        pattern = line_comment_re if include_line_comments else comment_re
        return [(match.start(), match.end()) for match in re.finditer(pattern, content)]

    def is_in_comment(self, pos, comments):
        for start, end in comments:
            if start < pos and pos < end:
                return True
            if pos < start:
                return False
        return False

    def _make_url_handler(self, name, hashed_files, template=None, comment_blocks=None):
        """
        Return a (handle_match, substitutions) pair for the given file.

        handle_match is a regex match callback that rewrites each matched URL
        to its hashed version. substitutions is the list that handle_match
        populates with (matched, replacement, hash_key, old_filename) tuples
        as it runs.
        """
        if template is None:
            template = self.default_template

        def _line_at_position(content, position):
            start = content.rfind("\n", 0, position) + 1
            end = content.find("\n", position)
            end = end if end != -1 else len(content)
            line_num = content.count("\n", 0, start) + 1
            msg = f"\n{line_num}: {content[start:end]}"
            if len(msg) > 79:
                return f"\n{line_num}"
            return msg

        substitutions = []

        def handle_match(matchobj):
            matches = matchobj.groupdict()
            matched = matches["matched"]
            url = matches["url"]

            # Ignore URLs in comments.
            if comment_blocks and self.is_in_comment(matchobj.start(), comment_blocks):
                return matched

            # Ignore absolute/protocol-relative and data-uri URLs.
            if re.match(r"^[a-z]+:", url) or url.startswith("//"):
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
                # Otherwise the condition above would have returned
                # prematurely.
                assert url_path.startswith(settings.STATIC_URL)
                target_name = url_path.removeprefix(settings.STATIC_URL)
            else:
                # We're using the posixpath module to mix paths and URLs
                # conveniently.
                source_name = name if os.sep == "/" else name.replace(os.sep, "/")
                target_name = posixpath.join(posixpath.dirname(source_name), url_path)

            # Determine the hashed name of the target file with the storage
            # backend.
            try:
                hashed_url = self._url(
                    self._stored_name,
                    unquote(target_name),
                    force=True,
                    hashed_files=hashed_files,
                )
            except ValueError as exc:
                line = _line_at_position(matchobj.string, matchobj.start())
                note = f"{name!r} contains this reference {matched!r} on line {line}"
                exc.add_note(note)
                raise exc

            transformed_url = "/".join(
                url_path.split("/")[:-1] + hashed_url.split("/")[-1:]
            )

            # Restore the fragment that was stripped off earlier.
            if fragment:
                transformed_url += ("?#" if "?#" in url else "#") + fragment

            matches["url"] = unquote(transformed_url)
            replacement = template % matches

            hash_key = self.hash_key(
                self.clean_name(posixpath.normpath(unquote(target_name).strip()))
            )
            old_filename = hashed_url.split("/")[-1]
            substitutions.append((matched, replacement, hash_key, old_filename))

            return replacement

        return handle_match, substitutions

    def post_process(self, paths, dry_run=False, **options):
        """
        Post process the given dictionary of files (called from collectstatic).

        Processing is actually two separate operations:

        1. renaming files to include a hash of their content for cache-busting,
           and copying those files to the target storage.
        2. adjusting files which contain references to other files so they
           refer to the cache-busting filenames.

        If either of these are performed on a file, then that file is
        considered post-processed.
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

        adjustable_set = set(adjustable_paths)

        # Scan all adjustable files once to collect substitutions and build
        # the dependency graph.
        file_subs = {}
        if adjustable_paths:
            for error in self._scan_substitutions(
                paths, adjustable_paths, hashed_files, file_subs
            ):
                yield error

        # Step 1: Process non-adjustable files
        non_adjustable_paths = {
            name: paths[name] for name in paths if name not in adjustable_set
        }
        for name, hashed_name, processed in self._post_process(
            non_adjustable_paths, hashed_files, file_subs
        ):
            yield name, hashed_name, processed

        # Step 2: Process adjustable files
        if adjustable_paths:
            clean_to_name = {self.clean_name(name): name for name in adjustable_paths}
            clean_adjustable = set(clean_to_name)
            graph = {
                name: {
                    clean_to_name[hk]
                    for _, _, hk, _ in file_subs.get(name, [])
                    if hk in clean_adjustable
                }
                for name in adjustable_paths
            }

            processing_order = self._sort_adjustable_paths(graph)

            ordered_paths = {name: paths[name] for name in processing_order}
            for name, hashed_name, processed in self._post_process(
                ordered_paths, hashed_files, file_subs
            ):
                yield name, hashed_name, processed

            # Process and yield circular dependencies.
            circular_nodes = set(graph) - set(processing_order)
            if circular_nodes:
                circular_nodes = sorted(circular_nodes)
                circular_paths = {name: paths[name] for name in circular_nodes}
                self._calculate_combined_hash(
                    circular_nodes, paths, hashed_files, file_subs
                )
                for name, hashed_name, processed in self._post_process(
                    circular_paths, hashed_files, file_subs
                ):
                    yield name, hashed_name, processed

        # Store the processed paths.
        self.hashed_files.update(hashed_files)

    def _post_process(self, paths, hashed_files, file_subs):
        for name in paths:
            # use the original, local file, not the copied-but-unprocessed
            # file, which might be somewhere far away, like S3
            storage, path = paths[name]
            with storage.open(path) as original_file:
                cleaned_name = self.clean_name(name)
                hash_key = self.hash_key(cleaned_name)
                subs = file_subs.get(name)
                if subs:
                    content = original_file.read().decode("utf-8")
                    content = self._apply_substitutions(content, subs, hashed_files)
                    content_file = ContentFile(content.encode())
                    # Use pre-computed hashed name if available (circular deps)
                    hashed_name = hashed_files.get(hash_key) or self.hashed_name(
                        name, content_file
                    )
                    processed = True
                else:
                    hashed_name = self.hashed_name(name, original_file)
                    if hasattr(original_file, "seek"):
                        original_file.seek(0)
                    content_file = original_file
                    processed = False
                if not self.exists(hashed_name):
                    processed = True
                    saved_name = self._save(hashed_name, content_file)
                    hashed_name = self.clean_name(saved_name)
                hashed_files[hash_key] = hashed_name
                yield name, hashed_name, processed

    def _sort_adjustable_paths(self, graph):
        # Topological sort; process and return linear dependencies.
        sorter = TopologicalSorter(graph)
        try:
            sorter.prepare()
        except CycleError:
            pass

        processing_order = []
        while sorter.is_active():
            node_group = sorter.get_ready()
            processing_order.extend(node_group)
            sorter.done(*node_group)
        return processing_order

    def _scan_substitutions(self, paths, adjustable_paths, hashed_files, file_subs):
        # Read each adjustable file once, running url patterns to collect
        # substitutions and build the dependency graph data.
        for name in adjustable_paths:
            storage, path = paths[name]
            with storage.open(path) as f:
                try:
                    content = f.read().decode("utf-8")
                except UnicodeDecodeError as exc:
                    yield name, None, exc
            subs = []
            try:
                for extension, patterns in self._patterns.items():
                    if matches_patterns(path, (extension,)):
                        comment_blocks = self.get_comment_blocks(
                            content,
                            include_line_comments=path.endswith(".js"),
                        )
                        for pattern, template in patterns:
                            handler, handler_subs = self._make_url_handler(
                                name, hashed_files, template, comment_blocks
                            )
                            for matchobj in pattern.finditer(content):
                                handler(matchobj)
                            subs.extend(handler_subs)
            except ValueError as exc:
                yield name, None, exc
            file_subs[name] = subs

    def _apply_substitutions(self, content, subs, hashed_files):
        # Apply stored substitutions, updating any hashed filenames that have
        # changed since the scan (e.g. adjustable files processed before this
        # one whose final hash differed from the unprocessed hash).
        for matched, replacement_text, hash_key, old_filename in subs:
            new_hashed_name = hashed_files.get(hash_key)
            if new_hashed_name:
                new_filename = new_hashed_name.split("/")[-1]
                if new_filename != old_filename:
                    replacement_text = replacement_text.replace(
                        old_filename, new_filename
                    )
            content = content.replace(matched, replacement_text)
        return content

    def _calculate_combined_hash(self, circular_nodes, paths, hashed_files, file_subs):
        # Resolve linear dependencies in circular file contents so the
        # combined hash changes when any linear dependency changes.
        circular_contents = {}
        for name in circular_nodes:
            storage_inst, path = paths[name]
            with storage_inst.open(path) as original_file:
                content = original_file.read().decode("utf-8")
                subs = file_subs.get(name, [])
                content = self._apply_substitutions(content, subs, hashed_files)
                circular_contents[name] = content

        # Calculate a stable hash for all circular dependencies combined
        combined_content = "".join(circular_contents[name] for name in circular_nodes)
        combined_file = ContentFile(combined_content.encode())
        combined_hash = self.file_hash("_combined", combined_file)

        # Register hashed names for circular files using the combined hash.
        for name in circular_nodes:
            cleaned_name = self.clean_name(name)
            hash_key = self.hash_key(cleaned_name)
            file_path, filename = os.path.split(cleaned_name)
            root, ext = os.path.splitext(filename)
            hashed_name = os.path.join(
                file_path, "%s.%s%s" % (root, combined_hash, ext)
            )
            hashed_files[hash_key] = hashed_name

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


class ManifestFilesMixin(HashedFilesMixin):
    manifest_version = "1.1"  # the manifest format standard
    manifest_name = "staticfiles.json"
    manifest_strict = True

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
        sorted_hashed_files = sorted(self.hashed_files.items())
        self.manifest_hash = self.file_hash(
            None, ContentFile(json.dumps(sorted_hashed_files).encode())
        )
        payload = {
            "paths": dict(sorted_hashed_files),
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
        self._wrapped = storages[STATICFILES_STORAGE_ALIAS]


staticfiles_storage = ConfiguredStorage()
