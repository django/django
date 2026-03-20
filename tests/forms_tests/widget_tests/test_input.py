from django.forms.widgets import Input

from .base import WidgetTest


class InputTests(WidgetTest):
    def test_attrs_with_type(self):
        attrs = {"type": "date"}
        widget = Input(attrs)
        self.check_html(
            widget, "name", "value", '<input type="date" name="name" value="value">'
        )
        # reuse the same attrs for another widget
        self.check_html(
            Input(attrs),
            "name",
            "value",
            '<input type="date" name="name" value="value">',
        )
        attrs["type"] = "number"  # shouldn't change the widget type
        self.check_html(
            widget, "name", "value", '<input type="date" name="name" value="value">'
        )

    def test_id_for_label(self):
        widget = Input(attrs={"type": "text"})
        self.assertEqual(widget.id_for_label("id_name"), "id_name")

    def test_render_with_custom_attrs(self):
        widget = Input(attrs={"type": "text"})
        self.check_html(
            widget,
            "field",
            "val",
            attrs={"class": "custom", "data-x": "1"},
            html=(
                '<input type="text" name="field" value="val" '
                'class="custom" data-x="1">'
            ),
        )
