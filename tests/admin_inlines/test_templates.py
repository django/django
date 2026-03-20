import json

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class TestTemplates(SimpleTestCase):
    def test_javascript_escaping(self):
        context = {
            "inline_admin_formset": {
                "inline_formset_data": json.dumps(
                    {
                        "formset": {"prefix": "my-prefix"},
                        "opts": {"verbose_name": "verbose name\\"},
                    }
                ),
            },
        }
        output = render_to_string("admin/edit_inline/stacked.html", context)
        self.assertIn("&quot;prefix&quot;: &quot;my-prefix&quot;", output)
        self.assertIn("&quot;verbose_name&quot;: &quot;verbose name\\\\&quot;", output)

        output = render_to_string("admin/edit_inline/tabular.html", context)
        self.assertIn("&quot;prefix&quot;: &quot;my-prefix&quot;", output)
        self.assertIn("&quot;verbose_name&quot;: &quot;verbose name\\\\&quot;", output)

    def test_stacked_template_renders(self):
        context = {
            "inline_admin_formset": {
                "inline_formset_data": json.dumps(
                    {
                        "formset": {"prefix": "test-prefix"},
                        "opts": {"verbose_name": "item"},
                    }
                ),
            },
        }
        output = render_to_string("admin/edit_inline/stacked.html", context)
        self.assertIn("test-prefix", output)

    def test_tabular_template_renders(self):
        context = {
            "inline_admin_formset": {
                "inline_formset_data": json.dumps(
                    {
                        "formset": {"prefix": "tab-prefix"},
                        "opts": {"verbose_name": "entry"},
                    }
                ),
            },
        }
        output = render_to_string("admin/edit_inline/tabular.html", context)
        self.assertIn("tab-prefix", output)
