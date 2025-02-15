"""
Wrapper for loading templates from "templates" directories in INSTALLED_APPS
packages.
"""

from thibaud.template.utils import get_app_template_dirs

from .filesystem import Loader as FilesystemLoader


class Loader(FilesystemLoader):
    def get_dirs(self):
        return get_app_template_dirs("templates")
