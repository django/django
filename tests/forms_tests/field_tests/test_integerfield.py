from django.core.exceptions import ValidationError
from django.forms import IntegerField, Textarea
from django.test import SimpleTestCase

from . import FormFieldAssertionsMixin


class IntegerFieldTest(FormFieldAssertionsMixin, SimpleTestCase):
    def test_integerfield_1(self):
        f = IntegerField()
        self.assertWidgetRendersTo(
            f, '<input type="number" name="f" id="id_f" required>'
        )
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean("")
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        self.assertEqual(1, f.clean("1"))
        self.assertIsInstance(f.clean("1"), int)
        self.assertEqual(23, f.clean("23"))
        with self.assertRaisesMessage(ValidationError, "'Enter a whole number.'"):
            f.clean("a")
        self.assertEqual(42, f.clean(42))
        with self.assertRaisesMessage(ValidationError, "'Enter a whole number.'"):
            f.clean(3.14)
        self.assertEqual(1, f.clean("1 "))
        self.assertEqual(1, f.clean(" 1"))
        self.assertEqual(1, f.clean(" 1 "))
        with self.assertRaisesMessage(ValidationError, "'Enter a whole number.'"):
            f.clean("1a")
        self.assertIsNone(f.max_value)
        self.assertIsNone(f.min_value)

    def test_integerfield_2(self):
        f = IntegerField(required=False)
        self.assertIsNone(f.clean(""))
        self.assertEqual("None", repr(f.clean("")))
        self.assertIsNone(f.clean(None))
        self.assertEqual("None", repr(f.clean(None)))
        self.assertEqual(1, f.clean("1"))
        self.assertIsInstance(f.clean("1"), int)
        self.assertEqual(23, f.clean("23"))
        with self.assertRaisesMessage(ValidationError, "'Enter a whole number.'"):
            f.clean("a")
        self.assertEqual(1, f.clean("1 "))
        self.assertEqual(1, f.clean(" 1"))
        self.assertEqual(1, f.clean(" 1 "))
        with self.assertRaisesMessage(ValidationError, "'Enter a whole number.'"):
            f.clean("1a")
        self.assertIsNone(f.max_value)
        self.assertIsNone(f.min_value)

    def test_integerfield_3(self):
        f = IntegerField(max_value=10)
        self.assertWidgetRendersTo(
            f, '<input max="10" type="number" name="f" id="id_f" required>'
        )
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        self.assertEqual(1, f.clean(1))
        self.assertEqual(10, f.clean(10))
        with self.assertRaisesMessage(
            ValidationError, "'Ensure this value is less than or equal to 10.'"
        ):
            f.clean(11)
        self.assertEqual(10, f.clean("10"))
        with self.assertRaisesMessage(
            ValidationError, "'Ensure this value is less than or equal to 10.'"
        ):
            f.clean("11")
        self.assertEqual(f.max_value, 10)
        self.assertIsNone(f.min_value)

    def test_integerfield_4(self):
        f = IntegerField(min_value=10)
        self.assertWidgetRendersTo(
            f, '<input id="id_f" type="number" name="f" min="10" required>'
        )
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        with self.assertRaisesMessage(
            ValidationError, "'Ensure this value is greater than or equal to 10.'"
        ):
            f.clean(1)
        self.assertEqual(10, f.clean(10))
        self.assertEqual(11, f.clean(11))
        self.assertEqual(10, f.clean("10"))
        self.assertEqual(11, f.clean("11"))
        self.assertIsNone(f.max_value)
        self.assertEqual(f.min_value, 10)

    def test_integerfield_5(self):
        f = IntegerField(min_value=10, max_value=20)
        self.assertWidgetRendersTo(
            f, '<input id="id_f" max="20" type="number" name="f" min="10" required>'
        )
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        with self.assertRaisesMessage(
            ValidationError, "'Ensure this value is greater than or equal to 10.'"
        ):
            f.clean(1)
        self.assertEqual(10, f.clean(10))
        self.assertEqual(11, f.clean(11))
        self.assertEqual(10, f.clean("10"))
        self.assertEqual(11, f.clean("11"))
        self.assertEqual(20, f.clean(20))
        with self.assertRaisesMessage(
            ValidationError, "'Ensure this value is less than or equal to 20.'"
        ):
            f.clean(21)
        self.assertEqual(f.max_value, 20)
        self.assertEqual(f.min_value, 10)

    def test_integerfield_6(self):
        f = IntegerField(step_size=3)
        self.assertWidgetRendersTo(
            f,
            '<input name="f" step="3" type="number" id="id_f" required>',
        )
        with self.assertRaisesMessage(
            ValidationError, "'Ensure this value is a multiple of step size 3.'"
        ):
            f.clean("10")
        self.assertEqual(12, f.clean(12))
        self.assertEqual(12, f.clean("12"))
        self.assertEqual(f.step_size, 3)

    def test_integerfield_step_size_min_value(self):
        f = IntegerField(step_size=3, min_value=-1)
        self.assertWidgetRendersTo(
            f,
            '<input name="f" min="-1" step="3" type="number" id="id_f" required>',
        )
        msg = (
            "Ensure this value is a multiple of step size 3, starting from -1, e.g. "
            "-1, 2, 5, and so on."
        )
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean("9")
        self.assertEqual(f.clean("2"), 2)
        self.assertEqual(f.clean("-1"), -1)
        self.assertEqual(f.step_size, 3)

    def test_integerfield_localized(self):
        """
        A localized IntegerField's widget renders to a text input without any
        number input specific attributes.
        """
        f1 = IntegerField(localize=True)
        self.assertWidgetRendersTo(
            f1, '<input id="id_f" name="f" type="text" required>'
        )

    def test_integerfield_float(self):
        f = IntegerField()
        self.assertEqual(1, f.clean(1.0))
        self.assertEqual(1, f.clean("1.0"))
        self.assertEqual(1, f.clean(" 1.0 "))
        self.assertEqual(1, f.clean("1."))
        self.assertEqual(1, f.clean(" 1. "))
        with self.assertRaisesMessage(ValidationError, "'Enter a whole number.'"):
            f.clean("1.5")
        with self.assertRaisesMessage(ValidationError, "'Enter a whole number.'"):
            f.clean("…")

    def test_integerfield_big_num(self):
        f = IntegerField()
        self.assertEqual(9223372036854775808, f.clean(9223372036854775808))
        self.assertEqual(9223372036854775808, f.clean("9223372036854775808"))
        self.assertEqual(9223372036854775808, f.clean("9223372036854775808.0"))

    def test_integerfield_unicode_number(self):
        f = IntegerField()
        self.assertEqual(50, f.clean("５０"))

    def test_integerfield_subclass(self):
        """
        Class-defined widget is not overwritten by __init__() (#22245).
        """

        class MyIntegerField(IntegerField):
            widget = Textarea

        f = MyIntegerField()
        self.assertEqual(f.widget.__class__, Textarea)
        f = MyIntegerField(localize=True)
        self.assertEqual(f.widget.__class__, Textarea)
