"""
Wrapper for loading templates from "templates" directories in INSTALLED_APPS
packages.
"""

import io

from django.core.exceptions import SuspiciousFileOperation
from django.template.base import TemplateDoesNotExist
from django.template.utils import get_app_template_dirs
from django.utils._os import safe_join

from .base import Loader as BaseLoader


class Loader(BaseLoader):
    is_usable = True

    def get_template_sources(self, template_name, template_dirs=None):
        """
        Returns the absolute paths to "template_name", when appended to each
        directory in "template_dirs". Any paths that don't lie inside one of the
        template dirs are excluded from the result set, for security reasons.
        """
        if not template_dirs:
            template_dirs = get_app_template_dirs('templates')
        for template_dir in template_dirs:
            try:
                yield safe_join(template_dir, template_name)
            except SuspiciousFileOperation:
                # The joined path was located outside of this template_dir
                # (it might be inside another one, so this isn't fatal).
                pass

    def load_template_source(self, template_name, template_dirs=None):
        for filepath in self.get_template_sources(template_name, template_dirs):
            try:
                with io.open(filepath, encoding=self.engine.file_charset) as fp:
                    return fp.read(), filepath
            except IOError:
                pass
        raise TemplateDoesNotExist(template_name)
