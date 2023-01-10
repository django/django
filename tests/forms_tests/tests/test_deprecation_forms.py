# RemovedInDjango50
from django.forms import CharField, EmailField, Form
from django.forms.utils import ErrorList
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango50Warning


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
