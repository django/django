from django.forms import TelInput

from .base import WidgetTest


class TelInputTest(WidgetTest):
    widget = TelInput()

    def test_render(self):
        self.check_html(
            self.widget, "telephone", "", html='<input type="tel" name="telephone">'
        )
