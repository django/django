from __future__ import unicode_literals

from django.template.loader import render_to_string
from django.test import SimpleTestCase


class TestTemplates(SimpleTestCase):
    def test_javascript_escaping(self):
        context = {
            'inline_admin_formset': {
                'formset': {'prefix': 'my-prefix'},
                'opts': {'verbose_name': 'verbose name\\'},
            },
        }
        output = render_to_string('admin/edit_inline/stacked.html', context)
        self.assertIn('prefix: "my\\u002Dprefix",', output)
        self.assertIn('addText: "Add another Verbose name\\u005C"', output)

        output = render_to_string('admin/edit_inline/tabular.html', context)
        self.assertIn('prefix: "my\\u002Dprefix",', output)
        self.assertIn('addText: "Add another Verbose name\\u005C"', output)
