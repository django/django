from django.core.exceptions import ImproperlyConfigured
from django.template.utils import get_app_template_dirs
from django.utils.functional import cached_property


class BaseEngine:

    # Core methods: engines have to provide their own implementation
    #               (except for from_string which is optional).

    def __init__(self, params):
        """
        Initialize the template engine.

        `params` is a dict of configuration settings.
        """
        params = params.copy()
        self.name = params.pop('NAME')
        self.dirs = list(params.pop('DIRS'))
        self.app_dirs = params.pop('APP_DIRS')
        if params:
            raise ImproperlyConfigured(
                "Unknown parameters: {}".format(", ".join(params)))

    @property
    def app_dirname(self):
        raise ImproperlyConfigured(
            "{} doesn't support loading templates from installed "
            "applications.".format(self.__class__.__name__))

    def from_string(self, template_code):
        """
        Create and return a template for the given source code.

        This method is optional.
        """
        raise NotImplementedError(
            "subclasses of BaseEngine should provide "
            "a from_string() method")

    def get_template(self, template_name):
        """
        Load and return a template for the given name.

        Raise TemplateDoesNotExist if no such template exists.
        """
        raise NotImplementedError(
            "subclasses of BaseEngine must provide "
            "a get_template() method")

    # Utility methods: they are provided to minimize code duplication and
    #                  security issues in third-party backends.

    @cached_property
    def template_dirs(self):
        """
        Return a list of directories to search for templates.
        """
        # Immutable return value because it's cached and shared by callers.
        template_dirs = tuple(self.dirs)
        if self.app_dirs:
            template_dirs += get_app_template_dirs(self.app_dirname)
        return template_dirs
