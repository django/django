import json
import os
import posixpath
import re
import textwrap
from graphlib import CycleError, TopologicalSorter
from hashlib import md5
from urllib.parse import unquote, urldefrag, urlsplit, urlunsplit

from django.conf import STATICFILES_STORAGE_ALIAS, settings
from django.contrib.staticfiles.utils import check_settings, matches_patterns
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, storages
from django.utils.functional import LazyObject
from django.utils.jslex import extract_css_urls, find_import_export_strings


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


class ProcessingException(Exception):
    def __init__(self, e, file_name):
        self.file_name = file_name
        self.original_exception = e
        super().__init__(e.args[0] if len(e.args) else "")


class HashedFilesMixin:
    max_post_process_passes = 5
    support_js_module_import_aggregation = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hashed_files = {}

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

    def post_process(self, paths, dry_run=False, **options):
        """
        Post process the given dictionary of files (called from collectstatic).

        Uses a dependency graph to minimize the number of passes required.
        """
        # don't even dare to process the files if we're in dry run mode
        if dry_run:
            return
        try:
            # Process files using the dependency graph
            yield from self._post_process(paths)
        except ProcessingException as exc:
            # django's collectstatic management command is written to expect
            # the exception to be returned in this format
            yield exc.file_name, None, exc.original_exception

    def _post_process(self, paths):
        """
        Process static files using a unified dependency graph approach.
        """
        hashed_files = {}

        substitutions_dict = self._find_substitutions(paths)
        linear_deps, circular_deps = self._topological_sort(paths, substitutions_dict)
        # First process the linear dependencies
        for name in linear_deps:
            name, hashed_name, processed = self._process_file(
                name, paths[name], hashed_files, substitutions_dict.get(name, [])
            )
            hashed_files[self.hash_key(self.clean_name(name))] = hashed_name
            yield name, hashed_name, processed

        # Handle circular dependencies
        if circular_deps:
            circular_hashes = self._process_circular_dependencies(
                circular_deps, paths, substitutions_dict, hashed_files
            )
            for name, hashed_name in circular_hashes:
                hashed_files[self.hash_key(self.clean_name(name))] = hashed_name
                yield name, hashed_name, True

        # Store the processed paths
        self.hashed_files.update(hashed_files)

    @property
    def url_finders(self):
        """
        Mapping of glob patterns to URL extraction functions.

        Each function receives (name, content) and returns a list of
        (url, position) tuples.
        """
        return {
            "*.css": [self._process_css_urls, self._process_sourcemap],
            "*.js": [self._process_js_modules, self._process_sourcemap],
        }

    def _get_url_finders(self, name):
        """Return list of URL finder functions for the given file name."""
        finders = []
        for pattern, pattern_finders in self.url_finders.items():
            if matches_patterns(name, [pattern]):
                finders.extend(pattern_finders)
        return finders

    def _find_substitutions(self, paths):
        """
        Return a dictionary mapping file names that need substitutions to a
        list of file names that need substituting along with the position in
        the file.
        """
        substitutions_dict = {}
        for name in paths:
            finders = self._get_url_finders(name)
            if not finders:
                continue
            storage, path = paths[name]
            with storage.open(path) as original_file:
                try:
                    content = original_file.read().decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ProcessingException(exc, path)

                url_positions = []
                for finder in finders:
                    url_positions.extend(finder(name, content))
                substitutions_dict[name] = url_positions
        return substitutions_dict

    def _topological_sort(self, paths, substitutions_dict):
        """
        Examines all the files that need substitutions and returns the list of
        files sorted in an order that is safe to process linearly, e.g
        image.png is hashed before styles.css needs to replace it with
        image.hash.png in a url().
        Any circular dependencies found will be returned as a separate list.
        """

        graph_sorter = TopologicalSorter()
        adjustable_paths = substitutions_dict.keys()
        non_adjustable = set(paths.keys()) - set(adjustable_paths)

        # build the graph based on the substitutions_dict
        for name, url_positions in substitutions_dict.items():
            if url_positions:
                for url_name, _ in url_positions:
                    # normalise base.css, /static/base.css, ../base.css, etc
                    target = self._get_target_name(url_name, name)
                    graph_sorter.add(name, target)
            else:
                non_adjustable.add(name)

        try:
            graph_sorter.prepare()
        except CycleError:
            # Even if there is a CycleError we can still access the linear
            # nodes using get_ready
            pass
        linear_deps = []
        while graph_sorter.is_active():
            node_group = graph_sorter.get_ready()
            linear_deps += [node for node in node_group if node in adjustable_paths]
            graph_sorter.done(*node_group)

        def path_level(name):
            return len(name.split(os.sep))

        non_adjustable = sorted(list(non_adjustable), key=path_level, reverse=True)
        linear_deps = list(non_adjustable) + linear_deps
        circular_deps = set(adjustable_paths) - set(linear_deps)

        return linear_deps, circular_deps

    def _process_js_modules(self, name, content):
        """Process JavaScript import/export statements."""
        url_positions = []

        if not self.support_js_module_import_aggregation or not matches_patterns(
            name, ("*.js",)
        ):
            return url_positions

        # simple search rules out most js files quickly
        complex_adjustments = "import" in content or (
            "export" in content and "from" in content
        )

        if not complex_adjustments:
            return url_positions

        # The simple search still leaves lots of false positives,
        # like the words important or exports
        # Match for import export syntax to futher reduce the need
        # to run the lexer, should cut out 90% of false positives
        if not self.import_export_pattern.search(content):
            return url_positions

        try:
            urls = find_import_export_strings(content)
        except ValueError as e:
            message = e.args[0] if len(e.args) else ""
            message = f"The js file '{name}' could not be processed.\n{message}"
            raise ProcessingException(ValueError(message), name)
        for url_name, position in urls:
            if self._should_adjust_url(url_name):
                url_positions.append((url_name, position))

        return url_positions

    import_export_pattern = re.compile(
        # check for import statements
        r"((^|[;}]|\*/)\s*import\b|"
        # check for dynamic imports
        r"import\s\(|"
        # check for comment in between import and opening bracket
        r"import\s*/\*.*?\*/\s*\(|"
        # check for the word export must be followed
        r"\bexport[\s{/*])",
        re.MULTILINE,
    )

    def _process_css_urls(self, name, content):
        """Process CSS url & import statements."""
        url_positions = []
        if not matches_patterns(name, ("*.css",)):
            return url_positions
        search_content = content.lower()
        complex_adjustments = "url(" in search_content or "@import" in search_content

        if not complex_adjustments:
            return url_positions

        for url_name, position in extract_css_urls(content):
            if self._should_adjust_url(url_name):
                url_positions.append((url_name, position))
        return url_positions

    def _process_sourcemap(self, name, content):
        url_positions = []
        if "sourceMappingURL" not in content:
            return url_positions

        for extension, pattern in self.source_map_patterns.items():
            if matches_patterns(name, (extension,)):
                for match in pattern.finditer(content):
                    url = match.group("url")
                    if self._should_adjust_url(url):
                        url_positions.append((url, match.start("url")))
        return url_positions

    source_map_patterns = {
        "*.css": re.compile(
            r"(?m)^/\*#[ \t](?-i:sourceMappingURL)=(?P<url>.*?)[ \t]*\*/$",
            re.IGNORECASE,
        ),
        "*.js": re.compile(
            r"(?m)^//# (?-i:sourceMappingURL)=(?P<url>.*?)[ \t]*$", re.IGNORECASE
        ),
    }

    _data_uri_re = re.compile(r"^[a-z]+:")

    def _should_adjust_url(self, url):
        """
        Return whether this is a url that should be adjusted
        """
        # Ignore absolute/protocol-relative and data-uri URLs.
        if self._data_uri_re.match(url) or url.startswith("//"):
            return False

        # Ignore absolute URLs that don't point to a static file (dynamic
        # CSS / JS?). Note that STATIC_URL cannot be empty.
        if url.startswith("/") and not url.startswith(settings.STATIC_URL):
            return False

        # Strip off the fragment so a path-like fragment won't interfere.
        url_path, _ = urldefrag(url)

        # Ignore URLs without a path
        if not url_path:
            return False
        return True

    def _adjust_url(self, url, name, hashed_files):
        """
        Return the hashed url without affecting fragments
        """
        # Strip off the fragment so a path-like fragment won't interfere.
        url_path, fragment = urldefrag(url)

        # determine the target file name (remove /static if needed)
        target_name = self._get_base_target_name(url_path, name)

        # Determine the hashed name of the target file.
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

        # Ensure we return a string (handle mock objects in tests)
        return str(transformed_url)

    def _get_target_name(self, url, source_name):
        """
        Get the target file name from a URL and source file name
        """
        url_path, _ = urldefrag(url)
        path = posixpath.normpath(self._get_base_target_name(url_path, source_name))
        if os.sep != "/":
            path = path.replace("/", os.sep)
        return path

    def _get_base_target_name(self, url_path, source_name):
        """
        Get the target file name from a URL (no fragment) and source file name
        """
        # Used by _get_target_name and _adjust_url
        if url_path.startswith("/"):
            # Otherwise the condition above would have returned prematurely.
            assert url_path.startswith(settings.STATIC_URL)
            target_name = url_path.removeprefix(settings.STATIC_URL)
        else:
            # We're using the posixpath module to mix paths and URLs.
            source_name = (
                source_name if os.sep == "/" else source_name.replace(os.sep, "/")
            )
            target_name = posixpath.join(posixpath.dirname(source_name), url_path)
        return target_name

    def _process_file(self, name, storage_and_path, hashed_files, url_positions):
        """
        Process a single file using the unified graph structure.
        """
        storage, path = storage_and_path

        with storage.open(path) as original_file:
            # Calculate hash of original file
            if hasattr(original_file, "seek"):
                original_file.seek(0)

            hashed_name = self.hashed_name(name, original_file)
            hashed_file_exists = self.exists(hashed_name)
            processed = False

            # If this is an adjustable file with URL positions,
            # apply transformations
            if url_positions:
                if hasattr(original_file, "seek"):
                    original_file.seek(0)
                content = original_file.read().decode("utf-8")

                # Apply URL substitutions using stored positions
                content = self._process_file_content(
                    name, content, url_positions, hashed_files
                )

                # Create a content file and calculate its hash
                content_file = ContentFile(content.encode())
                new_hashed_name = self.hashed_name(name, content_file)

                if not self.exists(new_hashed_name):
                    saved_name = self._save(new_hashed_name, content_file)
                    hashed_name = self.clean_name(saved_name)
                else:
                    hashed_name = new_hashed_name

                processed = True

            elif not hashed_file_exists:
                # For non-adjustable files just copy the file
                if hasattr(original_file, "seek"):
                    original_file.seek(0)
                processed = True
                saved_name = self._save(hashed_name, original_file)
                hashed_name = self.clean_name(saved_name)

            return name, hashed_name, processed

    def _process_file_content(self, name, content, url_positions, hashed_files):
        """
        Process file content by substituting URLs.
        url_positions is a list of (url, position) tuples.
        """
        if not url_positions:
            return content

        result_parts = []
        last_position = 0

        # Sort by position to ensure correct order
        sorted_positions = sorted(
            url_positions,
            key=lambda x: x[1],
        )

        for url, pos in sorted_positions:
            position = pos
            # Add content before this URL
            result_parts.append(content[last_position:position])

            try:
                transformed_url = self._adjust_url(url, name, hashed_files)
            except ValueError as exc:
                message = exc.args[0] if len(exc.args) else ""
                message = f"Error processing the url {url}\n{message}"
                exc = self._make_helpful_exception(ValueError(message), name)
                raise ProcessingException(exc, name)

            result_parts.append(transformed_url)
            last_position = position + len(url)

        # Add remaining content
        result_parts.append(content[last_position:])
        return "".join(result_parts)

    def _process_circular_dependencies(
        self, circular_deps, paths, substitutions_dict, hashed_files
    ):
        """
        Process files with circular dependencies.

        This method breaks the dependency cycle by:
        1. First replacing all non-circular URLs in each file
        and generating a hash based on their combined content
        2. Apply this stable combined hash to each of the files
        3. Safely updating all the references within the files

        Args:
            circular_deps: List of files that have circular dependencies
            paths: Dict mapping file paths to (storage, path) tuples
            substitutions_dict: Dictionary of url positions
            hashed_files: Dict of already processed files
        """
        circular_hashes = {}
        processed_files = set()

        # First pass: Replace all non-circular dependency URLs in each file
        # and generate group hash
        group_hash, original_contents = self._calculate_combined_hash(
            circular_deps, paths, substitutions_dict, hashed_files
        )

        # Second pass: Create hashed filenames using the group hash
        for name in circular_deps:
            if name in processed_files:
                continue

            # Generate a hashed filename based on the group hash
            filename, ext = os.path.splitext(name)
            hashed_name = f"{filename}.{group_hash}{ext}"

            # Store the hash for this file
            hash_key = self.hash_key(self.clean_name(name))
            circular_hashes[hash_key] = hashed_name
            processed_files.add(name)

        # Third pass: Process all URLs (including circular ones) and save files
        for name in circular_deps:
            content = original_contents[name]

            combined_hashes = {**hashed_files, **circular_hashes}
            content = self._process_file_content(
                name, content, substitutions_dict.get(name, []), combined_hashes
            )

            # Get the hashed name for this file
            hash_key = self.hash_key(self.clean_name(name))
            hashed_name = circular_hashes[hash_key]

            # Save the processed content to the hashed filename
            content_file = ContentFile(content.encode())
            if self.exists(hashed_name):
                self.delete(hashed_name)
            self._save(hashed_name, content_file)
            yield name, hashed_name

    def _calculate_combined_hash(
        self, circular_deps, paths, substitutions_dict, hashed_files
    ):
        """
        Return a hash of the combined content from all circular dependencies
        Replace the non circular URL's before calculating

        Also returns the original content to save opening it twice
        """
        original_contents = {}
        processed_contents = {}
        for name in circular_deps:
            storage, path = paths[name]
            with storage.open(path) as original_file:
                if hasattr(original_file, "seek"):
                    original_file.seek(0)
                content = original_file.read().decode("utf-8")

                original_contents[name] = content

                # Filter URL positions to only non-circular dependencies
                non_circular_positions = []
                for url, pos in substitutions_dict.get(name, []):
                    target = self._get_target_name(url, name)
                    if target not in circular_deps:
                        non_circular_positions.append((url, pos))
                # Replace all non-circular URLs first
                if non_circular_positions:
                    content = self._process_file_content(
                        name, content, non_circular_positions, hashed_files
                    )

                # Store the processed content for the second pass
                # We haven't actually saved these changes to disk
                processed_contents[name] = content

        # Calculate a stable hash for all circular dependencies combined
        combined_content = "".join(
            processed_contents[name] for name in sorted(circular_deps)
        )
        combined_file = ContentFile(combined_content.encode())
        group_hash = self.file_hash("_combined", combined_file)
        return group_hash, original_contents

    def _make_helpful_exception(self, exception, name):
        """
        The ValueError for missing files, such as images/fonts in css,
        sourcemaps, or js files in imports, lack context of the file being
        processed. Reformat them to be more helpful in revealing the source
        of the problem.
        """
        message = exception.args[0] if len(exception.args) else ""
        match = self._error_msg_re.search(message)
        if match:
            extension = os.path.splitext(name)[1].lstrip(".").upper()
            message = self._error_msg.format(
                orig_message=message,
                filename=name,
                missing=match.group(2),
                ext=extension,
                url=match.group(1),
            )
            exception = ValueError(message)
        return exception

    _error_msg_re = re.compile(
        r"^Error processing the url (.+)\nThe file '(.+)' could not be found"
    )

    _error_msg = textwrap.dedent(
        """\
        {orig_message}

        The {ext} file '{filename}' references a file which could not be found:
          {missing}

        Please check the URL references in this {ext} file, particularly any
        relative paths which might be pointing to the wrong location.
        """
    )

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
        # the intermediate files on disk may be corrupt; avoid an infinite
        # loop.
        raise ValueError("The name '%s' could not be hashed with %r." % (name, self))


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
