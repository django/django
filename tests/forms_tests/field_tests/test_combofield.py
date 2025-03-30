from django.core.exceptions import ValidationError
from django.forms import CharField, ComboField, EmailField
from django.test import SimpleTestCase


class ComboFieldTest(SimpleTestCase):
    def test_combofield_1(self):
        f = ComboField(fields=[CharField(max_length=20), EmailField()])
        self.assertEqual("test@example.com", f.clean("test@example.com"))

        msg = "'Ensure this value has at most 20 characters (it has 28).'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("longemailaddress@example.com")

        msg = "'Enter a valid email address.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("not an email")

        msg = "'This field is required.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("")
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean(None)

    def test_combofield_2(self):
        f = ComboField(fields=[CharField(max_length=20), EmailField()], required=False)
        self.assertEqual("test@example.com", f.clean("test@example.com"))

        msg = "'Ensure this value has at most 20 characters (it has 28).'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("longemailaddress@example.com")

        msg = "'Enter a valid email address.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("not an email")
        self.assertEqual("", f.clean(""))
        self.assertEqual("", f.clean(None))
