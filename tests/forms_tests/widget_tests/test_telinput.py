from django.forms import TelInput

from .base import WidgetTest


class TelInputTest(WidgetTest):
    widget = TelInput()

    def test_render(self):
        self.check_html(
            self.widget, "telephone", "", html='<input type="tel" name="telephone">'
        )

    def test_render_with_value(self):
        self.check_html(
            self.widget,
            "telephone",
            "+1234567890",
            html='<input type="tel" name="telephone" value="+1234567890">',
        )

    def test_render_with_attrs(self):
        self.check_html(
            self.widget,
            "telephone",
            "",
            attrs={"pattern": r"[0-9]+", "id": "phone"},
            html=('<input type="tel" name="telephone" ' 'id="phone" pattern="[0-9]+">'),
        )

    def test_value_from_datadict(self):
        data = {"telephone": "+1-555-0123"}
        result = self.widget.value_from_datadict(data, {}, "telephone")
        self.assertEqual(result, "+1-555-0123")
