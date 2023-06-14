from django.core.exceptions import ValidationError
from django.forms import EmailField
from django.test import SimpleTestCase

from . import FormFieldAssertionsMixin


class EmailFieldTest(FormFieldAssertionsMixin, SimpleTestCase):
    def test_emailfield_1(self):
        f = EmailField()
        self.assertEqual(f.max_length, 320)
        self.assertWidgetRendersTo(
            f, '<input type="email" name="f" id="id_f" maxlength="320" required>'
        )
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean("")
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        self.assertEqual("person@example.com", f.clean("person@example.com"))
        with self.assertRaisesMessage(
            ValidationError, "'Enter a valid email address.'"
        ):
            f.clean("foo")
        self.assertEqual(
            "local@domain.with.idn.xyz\xe4\xf6\xfc\xdfabc.part.com",
            f.clean("local@domain.with.idn.xyzäöüßabc.part.com"),
        )

    def test_email_regexp_for_performance(self):
        f = EmailField()
        # Check for runaway regex security problem. This will take a long time
        # if the security fix isn't in place.
        addr = "viewx3dtextx26qx3d@yahoo.comx26latlngx3d15854521645943074058"
        self.assertEqual(addr, f.clean(addr))

    def test_emailfield_not_required(self):
        f = EmailField(required=False)
        self.assertEqual("", f.clean(""))
        self.assertEqual("", f.clean(None))
        self.assertEqual("person@example.com", f.clean("person@example.com"))
        self.assertEqual(
            "example@example.com", f.clean("      example@example.com  \t   \t ")
        )
        with self.assertRaisesMessage(
            ValidationError, "'Enter a valid email address.'"
        ):
            f.clean("foo")

    def test_emailfield_min_max_length(self):
        f = EmailField(min_length=10, max_length=15)
        self.assertWidgetRendersTo(
            f,
            '<input id="id_f" type="email" name="f" maxlength="15" minlength="10" '
            "required>",
        )
        with self.assertRaisesMessage(
            ValidationError,
            "'Ensure this value has at least 10 characters (it has 9).'",
        ):
            f.clean("a@foo.com")
        self.assertEqual("alf@foo.com", f.clean("alf@foo.com"))
        with self.assertRaisesMessage(
            ValidationError,
            "'Ensure this value has at most 15 characters (it has 20).'",
        ):
            f.clean("alf123456788@foo.com")

    def test_emailfield_strip_on_none_value(self):
        f = EmailField(required=False, empty_value=None)
        self.assertIsNone(f.clean(""))
        self.assertIsNone(f.clean(None))

    def test_emailfield_unable_to_set_strip_kwarg(self):
        msg = "__init__() got multiple values for keyword argument 'strip'"
        with self.assertRaisesMessage(TypeError, msg):
            EmailField(strip=False)
