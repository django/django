"""
Wrapper for loading templates from a plain Python dict.
"""

from django.template.base import TemplateDoesNotExist

from .base import Loader as BaseLoader


class Loader(BaseLoader):
    is_usable = True

    def __init__(self, engine, templates_dict):
        self.templates_dict = templates_dict
        super(Loader, self).__init__(engine)

    def load_template_source(self, template_name, template_dirs=None):
        try:
            return self.templates_dict[template_name], template_name
        except KeyError:
            raise TemplateDoesNotExist(template_name)
