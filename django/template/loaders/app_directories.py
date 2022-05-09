"""
Wrapper for loading templates from "templates" directories in INSTALLED_APPS
packages.
"""

from django.template.utils import get_app_template_dirs

from .filesystem import Loader as FilesystemLoader


class Loader(FilesystemLoader):
    """ Load templates from folders in the installed apps """

    def __init__(self, engine, dir_name=None):
        """
        Loader for Django Templates defined in installed_apps
        :param engine: The template engine
        :param dir_name: The directory name in which the templates are located.
        Default: templates
        """
        super().__init__(engine)
        self.dir_name = dir_name or "templates"

    def get_dirs(self):
        return get_app_template_dirs(self.dir_name)
