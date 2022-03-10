# RemovedInDjango50
from django.forms import CharField, EmailField, Form, HiddenInput
from django.forms.utils import ErrorList
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango50Warning

from .test_forms import Person


class DivErrorList(ErrorList):
    def __str__(self):
        return self.as_divs()

    def as_divs(self):
        if not self:
            return ""
        return '<div class="errorlist">%s</div>' % "".join(
            f'<div class="error">{error}</div>' for error in self
        )


class DeprecationTests(SimpleTestCase):
    def test_deprecation_warning_html_output(self):
        msg = (
            "django.forms.BaseForm._html_output() is deprecated. Please use "
            ".render() and .get_context() instead."
        )
        with self.assertRaisesMessage(RemovedInDjango50Warning, msg):
            form = Person()
            form._html_output(
                normal_row='<p id="p_%(field_name)s"></p>',
                error_row="%s",
                row_ender="</p>",
                help_text_html=" %s",
                errors_on_separate_row=True,
            )

    def test_deprecation_warning_error_list(self):
        class EmailForm(Form):
            email = EmailField()
            comment = CharField()

        data = {"email": "invalid"}
        f = EmailForm(data, error_class=DivErrorList)
        msg = (
            "Returning a plain string from DivErrorList is deprecated. Please "
            "customize via the template system instead."
        )
        with self.assertRaisesMessage(RemovedInDjango50Warning, msg):
            f.as_p()


@ignore_warnings(category=RemovedInDjango50Warning)
class DeprecatedTests(SimpleTestCase):
    def test_errorlist_override_str(self):
        class CommentForm(Form):
            name = CharField(max_length=50, required=False)
            email = EmailField()
            comment = CharField()

        data = {"email": "invalid"}
        f = CommentForm(data, auto_id=False, error_class=DivErrorList)
        self.assertHTMLEqual(
            f.as_p(),
            '<p>Name: <input type="text" name="name" maxlength="50"></p>'
            '<div class="errorlist">'
            '<div class="error">Enter a valid email address.</div></div>'
            '<p>Email: <input type="email" name="email" value="invalid" required></p>'
            '<div class="errorlist">'
            '<div class="error">This field is required.</div></div>'
            '<p>Comment: <input type="text" name="comment" required></p>',
        )

    def test_field_name(self):
        """#5749 - `field_name` may be used as a key in _html_output()."""

        class SomeForm(Form):
            some_field = CharField()

            def as_p(self):
                return self._html_output(
                    normal_row='<p id="p_%(field_name)s"></p>',
                    error_row="%s",
                    row_ender="</p>",
                    help_text_html=" %s",
                    errors_on_separate_row=True,
                )

        form = SomeForm()
        self.assertHTMLEqual(form.as_p(), '<p id="p_some_field"></p>')

    def test_field_without_css_classes(self):
        """
        `css_classes` may be used as a key in _html_output() (empty classes).
        """

        class SomeForm(Form):
            some_field = CharField()

            def as_p(self):
                return self._html_output(
                    normal_row='<p class="%(css_classes)s"></p>',
                    error_row="%s",
                    row_ender="</p>",
                    help_text_html=" %s",
                    errors_on_separate_row=True,
                )

        form = SomeForm()
        self.assertHTMLEqual(form.as_p(), '<p class=""></p>')

    def test_field_with_css_class(self):
        """
        `css_classes` may be used as a key in _html_output() (class comes
        from required_css_class in this case).
        """

        class SomeForm(Form):
            some_field = CharField()
            required_css_class = "foo"

            def as_p(self):
                return self._html_output(
                    normal_row='<p class="%(css_classes)s"></p>',
                    error_row="%s",
                    row_ender="</p>",
                    help_text_html=" %s",
                    errors_on_separate_row=True,
                )

        form = SomeForm()
        self.assertHTMLEqual(form.as_p(), '<p class="foo"></p>')

    def test_field_name_with_hidden_input(self):
        """
        BaseForm._html_output() should merge all the hidden input fields and
        put them in the last row.
        """

        class SomeForm(Form):
            hidden1 = CharField(widget=HiddenInput)
            custom = CharField()
            hidden2 = CharField(widget=HiddenInput)

            def as_p(self):
                return self._html_output(
                    normal_row="<p%(html_class_attr)s>%(field)s %(field_name)s</p>",
                    error_row="%s",
                    row_ender="</p>",
                    help_text_html=" %s",
                    errors_on_separate_row=True,
                )

        form = SomeForm()
        self.assertHTMLEqual(
            form.as_p(),
            '<p><input id="id_custom" name="custom" type="text" required> custom'
            '<input id="id_hidden1" name="hidden1" type="hidden">'
            '<input id="id_hidden2" name="hidden2" type="hidden"></p>',
        )

    def test_field_name_with_hidden_input_and_non_matching_row_ender(self):
        """
        BaseForm._html_output() should merge all the hidden input fields and
        put them in the last row ended with the specific row ender.
        """

        class SomeForm(Form):
            hidden1 = CharField(widget=HiddenInput)
            custom = CharField()
            hidden2 = CharField(widget=HiddenInput)

            def as_p(self):
                return self._html_output(
                    normal_row="<p%(html_class_attr)s>%(field)s %(field_name)s</p>",
                    error_row="%s",
                    row_ender="<hr><hr>",
                    help_text_html=" %s",
                    errors_on_separate_row=True,
                )

        form = SomeForm()
        self.assertHTMLEqual(
            form.as_p(),
            '<p><input id="id_custom" name="custom" type="text" required> custom</p>\n'
            '<input id="id_hidden1" name="hidden1" type="hidden">'
            '<input id="id_hidden2" name="hidden2" type="hidden"><hr><hr>',
        )
