

import os
import posixpath
import re

from urllib.parse import unquote, urldefrag

from django.conf import settings
from django.contrib.staticfiles.storage import ManifestFilesMixin, StaticFilesStorage
from django.contrib.staticfiles.utils import matches_patterns
from django.core.files.base import ContentFile

from pipeline.storage import PipelineMixin
from storages.backends.s3boto3 import S3Boto3Storage

from django.core.files.base import File

__all__ = ['File']

class MediaStorage(S3Boto3Storage):
    location = settings.MEDIAFILES_LOCATION


class PipelineManifestStorage(PipelineMixin, ManifestFilesMixin, StaticFilesStorage):
    """
    Applys patches from https://github.com/django/django/pull/11241 to ignore
    imports in comments. Ref: https://code.djangoproject.com/ticket/21080
    """

    def get_comment_blocks(self, content):
        """
        Return a list of (start, end) tuples for each comment block.
        """
        return [
            (match.start(), match.end())
            for match in re.finditer(r"\/\*.*?\*\/", content, flags=re.DOTALL)
        ]

    def url_converter(self, name, hashed_files, template=None, comment_blocks=[]):
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

            # Ignore URLs in comments.
            if self.is_in_comment(matchobj.start(), comment_blocks):
                return matched

            # Ignore absolute/protocol-relative and data-uri URLs.
            if re.match(r'^[a-z]+:', url):
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
            hashed_url = self._url(
                self._stored_name, unquote(target_name),
                force=True, hashed_files=hashed_files,
            )

            transformed_url = '/'.join(url_path.split('/')[:-1] + hashed_url.split('/')[-1:])

            # Restore the fragment that was stripped off earlier.
            if fragment:
                transformed_url += ('?#' if '?#' in url else '#') + fragment

            # Return the hashed version to the file
            return template % unquote(transformed_url)

        return converter

    def is_in_comment(self, pos, comments):
        for start, end in comments:
            if start < pos and pos < end:
                return True
            if pos < start:
                return False
        return False

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
                if hasattr(original_file, 'seek'):
                    original_file.seek(0)

                hashed_file_exists = self.exists(hashed_name)
                processed = False

                # ..to apply each replacement pattern to the content
                if name in adjustable_paths:
                    old_hashed_name = hashed_name
                    content = original_file.read().decode(settings.FILE_CHARSET)
                    for extension, patterns in self._patterns.items():
                        if matches_patterns(path, (extension,)):
                            comment_blocks = self.get_comment_blocks(content)
                            for pattern, template in patterns:
                                converter = self.url_converter(name, hashed_files, template, comment_blocks)
                                try:
                                    content = pattern.sub(converter, content)
                                except ValueError as exc:
                                    yield name, None, exc, False
                    if hashed_file_exists:
                        self.delete(hashed_name)
                    # then save the processed result
                    content_file = ContentFile(content.encode())
                    # Save intermediate file for reference
                    saved_name = self._save(hashed_name, content_file)
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
