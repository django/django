from __future__ import unicode_literals

from django.forms import Widget
from django.test import SimpleTestCase


class WidgetTests(SimpleTestCase):

    def test_value_omitted_from_data(self):
        widget = Widget()
        self.assertIs(widget.value_omitted_from_data({}, {}, 'field'), True)
        self.assertIs(widget.value_omitted_from_data({'field': 'value'}, {}, 'field'), False)
