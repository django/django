import os
import posixpath
import unittest

from django.forms.renderers import (
    BaseRenderer,
    DjangoTemplates,
    Jinja2,
    TemplatesSetting,
)
from django.test import SimpleTestCase
from django.utils.version import get_version_tuple

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
        expected_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                self.expected_widget_dir + "/forms_tests/custom_widget.html",
            )
        )
        self.assertEqual(tpl.origin.name, expected_path)


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

    @property
    def jinja2_version(self):
        return get_version_tuple(jinja2.__version__)

    def test_installed_apps_template_found(self):
        """Can find a custom template in INSTALLED_APPS."""
        renderer = self.renderer()
        # Found because forms_tests is .
        tpl = renderer.get_template("forms_tests/custom_widget.html")
        expected_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", self.expected_widget_dir)
        )
        if self.jinja2_version < (3, 1):
            expected_path = os.path.join(
                expected_path, "forms_tests", "custom_widget.html"
            )
        else:
            expected_path = posixpath.join(
                expected_path, "forms_tests", "custom_widget.html"
            )
        self.assertEqual(tpl.origin.name, expected_path)


class TemplatesSettingTests(SharedTests, SimpleTestCase):
    renderer = TemplatesSetting
