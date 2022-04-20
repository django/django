from django.forms import CharField, Form, HiddenInput

from .base import WidgetTest


class HiddenInputTest(WidgetTest):
    widget = HiddenInput()

    def test_render(self):
        self.check_html(
            self.widget, "email", "", html='<input type="hidden" name="email">'
        )

    def test_use_required_attribute(self):
        # Always False to avoid browser validation on inputs hidden from the
        # user.
        self.assertIs(self.widget.use_required_attribute(None), False)
        self.assertIs(self.widget.use_required_attribute(""), False)
        self.assertIs(self.widget.use_required_attribute("foo"), False)

    def test_fieldset(self):
        class TestForm(Form):
            template_name = "forms_tests/use_fieldset.html"
            field = CharField(widget=self.widget)

        form = TestForm()
        self.assertIs(self.widget.use_fieldset, False)
        self.assertHTMLEqual(
            '<input type="hidden" name="field" id="id_field">',
            form.render(),
        )
