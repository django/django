from django.forms import FileField, FileInput, Form

from .base import WidgetTest


class FileInputTest(WidgetTest):
    widget = FileInput()

    def test_render(self):
        """
        FileInput widgets never render the value attribute. The old value
        isn't useful if a form is updated or an error occurred.
        """
        self.check_html(
            self.widget,
            "email",
            "test@example.com",
            html='<input type="file" name="email">',
        )
        self.check_html(
            self.widget, "email", "", html='<input type="file" name="email">'
        )
        self.check_html(
            self.widget, "email", None, html='<input type="file" name="email">'
        )

    def test_value_omitted_from_data(self):
        self.assertIs(self.widget.value_omitted_from_data({}, {}, "field"), True)
        self.assertIs(
            self.widget.value_omitted_from_data({}, {"field": "value"}, "field"), False
        )

    def test_use_required_attribute(self):
        # False when initial data exists. The file input is left blank by the
        # user to keep the existing, initial value.
        self.assertIs(self.widget.use_required_attribute(None), True)
        self.assertIs(self.widget.use_required_attribute("resume.txt"), False)

    def test_fieldset(self):
        class TestForm(Form):
            template_name = "forms_tests/use_fieldset.html"
            field = FileField(widget=self.widget)

        form = TestForm()
        self.assertIs(self.widget.use_fieldset, False)
        self.assertHTMLEqual(
            '<div><label for="id_field">Field:</label><input id="id_field" '
            'name="field" required type="file"></div>',
            form.render(),
        )
