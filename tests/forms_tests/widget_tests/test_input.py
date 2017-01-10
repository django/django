from django.forms.widgets import Input

from .base import WidgetTest


class InputWidgetTests(WidgetTest):

    def test_no_trailing_newline_in_attrs(self):
        self.check_html(Input(), 'name', 'value', strict=True, html='<input type="None" name="name" value="value" />')

    def test_attrs_with_type_passed(self):
        attrs = {'type': 'date'}
        widget = Input(attrs)
        self.check_html(widget, 'name', 'value', html=(
            '<input type="date" name="name" value="value" />'
        ))
        # reuse the same attrs for another widget
        self.check_html(Input(attrs), 'name', 'value', html=(
            '<input type="date" name="name" value="value" />'
        ))
        # shouldn't cause type of widget to become 'number'
        attrs['type'] = 'number'
        self.check_html(widget, 'name', 'value', html=(
            '<input type="date" name="name" value="value" />'
        ))
