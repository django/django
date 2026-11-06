from django.forms import CharField, EmailInput, Form

from .base import WidgetTest


class EmailInputTest(WidgetTest):
    widget = EmailInput()

    def test_render(self):
        self.check_html(
            self.widget,
            "email",
            "",
            html='<input type="email" name="email" dir="ltr">',
        )

    def test_render_value(self):
        self.check_html(
            self.widget,
            "email",
            "test@example.com",
            html=(
                '<input type="email" name="email" value="test@example.com" dir="ltr">'
            ),
        )

    def test_render_custom_attrs(self):
        self.check_html(
            self.widget,
            "email",
            "test@example.com",
            attrs={"class": "fun"},
            html=(
                '<input type="email" name="email" value="test@example.com" '
                'class="fun" dir="ltr">'
            ),
        )

    def test_constructor_attrs(self):
        widget = EmailInput(attrs={"class": "fun"})
        self.check_html(
            widget,
            "email",
            "",
            html='<input type="email" class="fun" name="email" dir="ltr">',
        )

    def test_dir_override(self):
        """Allow developers to override dir attribute if desired."""
        widget = EmailInput(attrs={"dir": "rtl"})
        self.check_html(
            widget,
            "email",
            "",
            html='<input type="email" name="email" dir="rtl">',
        )

    def test_fieldset(self):
        class TestForm(Form):
            template_name = "forms_tests/use_fieldset.html"
            field = CharField(widget=self.widget)

        form = TestForm()
        self.assertIs(self.widget.use_fieldset, False)
        self.assertHTMLEqual(
            '<div><label for="id_field">Field:</label>'
            '<input type="email" name="field" required id="id_field" dir="ltr"></div>',
            form.render(),
        )
