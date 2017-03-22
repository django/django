from __future__ import absolute_import

import os
import re
import textwrap

from django.conf import settings
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage

from .compress import Compressor


class CompressedStaticFilesMixin(object):
    """
    Wraps a StaticFilesStorage instance to create compressed versions of its
    output files
    """

    def post_process(self, *args, **kwargs):
        files = super(CompressedStaticFilesMixin, self).post_process(*args, **kwargs)
        if not kwargs.get('dry_run'):
            files = self.post_process_with_compression(files)
        return files

    def post_process_with_compression(self, files):
        extensions = getattr(settings,
                             'WHITENOISE_SKIP_COMPRESS_EXTENSIONS', None)
        compressor = Compressor(extensions=extensions, quiet=True)
        for name, hashed_name, processed in files:
            if self.should_compress(compressor, name, processed):
                compressor.compress(self.path(name))
                if hashed_name is not None:
                    compressor.compress(self.path(hashed_name))
            yield name, hashed_name, processed

    def should_compress(self, compressor, name, processed):
        if isinstance(processed, Exception):
            return False
        else:
            return compressor.should_compress(name)


class HelpfulExceptionMixin(object):
    """
    If a CSS file contains references to images, fonts etc that can't be found
    then Django's `post_process` blows up with a not particularly helpful
    ValueError that leads people to think WhiteNoise is broken.

    Here we attempt to intercept such errors and reformat them to be more
    helpful in revealing the source of the problem.
    """

    ERROR_MSG_RE = re.compile("^The file '(.+)' could not be found")

    ERROR_MSG = textwrap.dedent(u"""\
        {orig_message}

        The {ext} file '{filename}' references a file which could not be found:
          {missing}

        Please check the URL references in this {ext} file, particularly any
        relative paths which might be pointing to the wrong location.
        """)

    def post_process(self, *args, **kwargs):
        files = super(HelpfulExceptionMixin, self).post_process(*args, **kwargs)
        for name, hashed_name, processed in files:
            if isinstance(processed, Exception):
                processed = self.make_helpful_exception(processed, name)
            yield name, hashed_name, processed

    def make_helpful_exception(self, exception, name):
        if isinstance(exception, ValueError):
            message = exception.args[0] if len(exception.args) else ''
            # Stringly typed exceptions. Yay!
            match = self.ERROR_MSG_RE.search(message)
            if match:
                extension = os.path.splitext(name)[1].lstrip('.').upper()
                message = self.ERROR_MSG.format(
                        orig_message=message,
                        filename=name,
                        missing=match.group(1),
                        ext=extension)
                exception = MissingFileError(message)
        return exception


class MissingFileError(ValueError):
    pass


class CompressedManifestStaticFilesStorage(
        HelpfulExceptionMixin, CompressedStaticFilesMixin,
        ManifestStaticFilesStorage):
    pass
