import unittest
from pathlib import Path

from django.forms.renderers import (
    BaseRenderer,
    DjangoTemplates,
    Jinja2,
    TemplatesSetting,
)
from django.test import SimpleTestCase

try:
    import jinja2
except ImportError:
    jinja2 = None


class SharedTests:
    expected_widget_dir = "templates"

    def test_installed_apps_template_found(self):
        """Can find a custom template in INSTALLED_APPS."""
        renderer = self.renderer()
        # Found because forms_tests is .
        tpl = renderer.get_template("forms_tests/custom_widget.html")
        expected_path = Path(__file__).parent.parent.joinpath(
            self.expected_widget_dir, "forms_tests", "custom_widget.html"
        )
        self.assertEqual(tpl.origin.name, str(expected_path))


class BaseTemplateRendererTests(SimpleTestCase):
    def test_get_renderer(self):
        with self.assertRaisesMessage(
            NotImplementedError, "subclasses must implement get_template()"
        ):
            BaseRenderer().get_template("")


class DjangoTemplatesTests(SharedTests, SimpleTestCase):
    renderer = DjangoTemplates


@unittest.skipIf(jinja2 is None, "jinja2 required")
class Jinja2Tests(SharedTests, SimpleTestCase):
    renderer = Jinja2
    expected_widget_dir = "jinja2"


class TemplatesSettingTests(SharedTests, SimpleTestCase):
    renderer = TemplatesSetting
