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
