from django.forms import ColorInput

from .base import WidgetTest


class ColorInputTest(WidgetTest):
    widget = ColorInput()

    def test_render(self):
        self.check_html(
            self.widget,
            "color",
            "",
            html="<input type='color' name='color'>",
        )

    def test_render_with_value(self):
        self.check_html(
            self.widget,
            "color",
            "#ff0000",
            html='<input type="color" name="color" value="#ff0000">',
        )

    def test_render_with_attrs(self):
        self.check_html(
            self.widget,
            "color",
            "#00ff00",
            attrs={"id": "my-color", "class": "form-control"},
            html=(
                '<input type="color" name="color" value="#00ff00" '
                'class="form-control" id="my-color">'
            ),
        )

    def test_value_from_datadict(self):
        data = {"color": "#0000ff"}
        result = self.widget.value_from_datadict(data, {}, "color")
        self.assertEqual(result, "#0000ff")
