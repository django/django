import functools
from pathlib import Path

from thibaud.conf import settings
from thibaud.template.backends.thibaud import ThibaudTemplates
from thibaud.template.loader import get_template
from thibaud.utils.functional import cached_property
from thibaud.utils.module_loading import import_string


@functools.lru_cache
def get_default_renderer():
    renderer_class = import_string(settings.FORM_RENDERER)
    return renderer_class()


class BaseRenderer:
    form_template_name = "thibaud/forms/div.html"
    formset_template_name = "thibaud/forms/formsets/div.html"
    field_template_name = "thibaud/forms/field.html"

    bound_field_class = None

    def get_template(self, template_name):
        raise NotImplementedError("subclasses must implement get_template()")

    def render(self, template_name, context, request=None):
        template = self.get_template(template_name)
        return template.render(context, request=request).strip()


class EngineMixin:
    def get_template(self, template_name):
        return self.engine.get_template(template_name)

    @cached_property
    def engine(self):
        return self.backend(
            {
                "APP_DIRS": True,
                "DIRS": [Path(__file__).parent / self.backend.app_dirname],
                "NAME": "thibaudforms",
                "OPTIONS": {},
            }
        )


class ThibaudTemplates(EngineMixin, BaseRenderer):
    """
    Load Thibaud templates from the built-in widget templates in
    thibaud/forms/templates and from apps' 'templates' directory.
    """

    backend = ThibaudTemplates


class Jinja2(EngineMixin, BaseRenderer):
    """
    Load Jinja2 templates from the built-in widget templates in
    thibaud/forms/jinja2 and from apps' 'jinja2' directory.
    """

    @cached_property
    def backend(self):
        from thibaud.template.backends.jinja2 import Jinja2

        return Jinja2


class TemplatesSetting(BaseRenderer):
    """
    Load templates using template.loader.get_template() which is configured
    based on settings.TEMPLATES.
    """

    def get_template(self, template_name):
        return get_template(template_name)
