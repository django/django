from django.forms import CharField, Form, URLInput

from .base import WidgetTest


class URLInputTest(WidgetTest):
    widget = URLInput()

    def test_render(self):
        self.check_html(
            self.widget,
            "url",
            "",
            html='<input type="url" name="url" dir="ltr">',
        )

    def test_render_value(self):
        self.check_html(
            self.widget,
            "url",
            "https://example.com",
            html='<input type="url" name="url" value="https://example.com" dir="ltr">',
        )

    def test_render_custom_attrs(self):
        self.check_html(
            self.widget,
            "url",
            "https://example.com",
            attrs={"class": "fun"},
            html=(
                '<input type="url" name="url" value="https://example.com" '
                'class="fun" dir="ltr">'
            ),
        )

    def test_constructor_attrs(self):
        widget = URLInput(attrs={"class": "fun"})
        self.check_html(
            widget,
            "url",
            "",
            html='<input type="url" class="fun" name="url" dir="ltr">',
        )

    def test_dir_override(self):
        """Allow developers to override dir attribute if desired."""
        widget = URLInput(attrs={"dir": "rtl"})
        self.check_html(
            widget,
            "url",
            "",
            html='<input type="url" name="url" dir="rtl">',
        )

    def test_fieldset(self):
        class TestForm(Form):
            template_name = "forms_tests/use_fieldset.html"
            field = CharField(widget=self.widget)

        form = TestForm()
        self.assertIs(self.widget.use_fieldset, False)
        self.assertHTMLEqual(
            '<div><label for="id_field">Field:</label>'
            '<input type="url" name="field" required id="id_field" dir="ltr"></div>',
            form.render(),
        )
