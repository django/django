"""
Wrapper for loading templates from the filesystem.
"""

import errno
import io
import warnings

from django.core.exceptions import SuspiciousFileOperation
from django.template import Origin, TemplateDoesNotExist
from django.utils._os import safe_join
from django.utils.deprecation import RemovedInDjango20Warning

from .base import Loader as BaseLoader


class Loader(BaseLoader):

    def __init__(self, engine, dirs=None):
        super(Loader, self).__init__(engine)
        self.dirs = dirs

    def get_dirs(self):
        return self.dirs if self.dirs is not None else self.engine.dirs

    def get_contents(self, origin):
        try:
            with io.open(origin.name, encoding=self.engine.file_charset) as fp:
                return fp.read()
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise TemplateDoesNotExist(origin)
            raise

    def get_template_sources(self, template_name, template_dirs=None):
        """
        Return an Origin object pointing to an absolute path in each directory
        in template_dirs. For security reasons, if a path doesn't lie inside
        one of the template_dirs it is excluded from the result set.
        """
        if not template_dirs:
            template_dirs = self.get_dirs()
        for template_dir in template_dirs:
            try:
                name = safe_join(template_dir, template_name)
            except SuspiciousFileOperation:
                # The joined path was located outside of this template_dir
                # (it might be inside another one, so this isn't fatal).
                continue

            yield Origin(
                name=name,
                template_name=template_name,
                loader=self,
            )

    def load_template_source(self, template_name, template_dirs=None):
        warnings.warn(
            'The load_template_sources() method is deprecated. Use '
            'get_template() or get_contents() instead.',
            RemovedInDjango20Warning,
        )
        for origin in self.get_template_sources(template_name, template_dirs):
            try:
                return self.get_contents(origin), origin.name
            except TemplateDoesNotExist:
                pass
        raise TemplateDoesNotExist(template_name)
