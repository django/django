from django.forms import (
    CharField, HiddenInput, PasswordInput, Textarea, TextInput,
    ValidationError,
)
from django.test import SimpleTestCase

from . import FormFieldAssertionsMixin


class CharFieldTest(FormFieldAssertionsMixin, SimpleTestCase):

    def test_charfield_1(self):
        f = CharField()
        self.assertEqual('1', f.clean(1))
        self.assertEqual('hello', f.clean('hello'))
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean('')
        self.assertEqual('[1, 2, 3]', f.clean([1, 2, 3]))
        self.assertIsNone(f.max_length)
        self.assertIsNone(f.min_length)

    def test_charfield_2(self):
        f = CharField(required=False)
        self.assertEqual('1', f.clean(1))
        self.assertEqual('hello', f.clean('hello'))
        self.assertEqual('', f.clean(None))
        self.assertEqual('', f.clean(''))
        self.assertEqual('[1, 2, 3]', f.clean([1, 2, 3]))
        self.assertIsNone(f.max_length)
        self.assertIsNone(f.min_length)

    def test_charfield_3(self):
        f = CharField(max_length=10, required=False)
        self.assertEqual('12345', f.clean('12345'))
        self.assertEqual('1234567890', f.clean('1234567890'))
        msg = "'Ensure this value has at most 10 characters (it has 11).'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('1234567890a')
        self.assertEqual(f.max_length, 10)
        self.assertIsNone(f.min_length)

    def test_charfield_4(self):
        f = CharField(min_length=10, required=False)
        self.assertEqual('', f.clean(''))
        msg = "'Ensure this value has at least 10 characters (it has 5).'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('12345')
        self.assertEqual('1234567890', f.clean('1234567890'))
        self.assertEqual('1234567890a', f.clean('1234567890a'))
        self.assertIsNone(f.max_length)
        self.assertEqual(f.min_length, 10)

    def test_charfield_5(self):
        f = CharField(min_length=10, required=True)
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean('')
        msg = "'Ensure this value has at least 10 characters (it has 5).'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('12345')
        self.assertEqual('1234567890', f.clean('1234567890'))
        self.assertEqual('1234567890a', f.clean('1234567890a'))
        self.assertIsNone(f.max_length)
        self.assertEqual(f.min_length, 10)

    def test_charfield_length_not_int(self):
        """
        Setting min_length or max_length to something that is not a number
        raises an exception.
        """
        with self.assertRaises(ValueError):
            CharField(min_length='a')
        with self.assertRaises(ValueError):
            CharField(max_length='a')
        msg = '__init__() takes 1 positional argument but 2 were given'
        with self.assertRaisesMessage(TypeError, msg):
            CharField('a')

    def test_charfield_widget_attrs(self):
        """
        CharField.widget_attrs() always returns a dictionary and includes
        minlength/maxlength if min_length/max_length are defined on the field
        and the widget is not hidden.
        """
        # Return an empty dictionary if max_length and min_length are both None.
        f = CharField()
        self.assertEqual(f.widget_attrs(TextInput()), {})
        self.assertEqual(f.widget_attrs(Textarea()), {})

        # Return a maxlength attribute equal to max_length.
        f = CharField(max_length=10)
        self.assertEqual(f.widget_attrs(TextInput()), {'maxlength': '10'})
        self.assertEqual(f.widget_attrs(PasswordInput()), {'maxlength': '10'})
        self.assertEqual(f.widget_attrs(Textarea()), {'maxlength': '10'})

        # Return a minlength attribute equal to min_length.
        f = CharField(min_length=5)
        self.assertEqual(f.widget_attrs(TextInput()), {'minlength': '5'})
        self.assertEqual(f.widget_attrs(PasswordInput()), {'minlength': '5'})
        self.assertEqual(f.widget_attrs(Textarea()), {'minlength': '5'})

        # Return both maxlength and minlength when both max_length and
        # min_length are set.
        f = CharField(max_length=10, min_length=5)
        self.assertEqual(f.widget_attrs(TextInput()), {'maxlength': '10', 'minlength': '5'})
        self.assertEqual(f.widget_attrs(PasswordInput()), {'maxlength': '10', 'minlength': '5'})
        self.assertEqual(f.widget_attrs(Textarea()), {'maxlength': '10', 'minlength': '5'})
        self.assertEqual(f.widget_attrs(HiddenInput()), {})

    def test_charfield_strip(self):
        """
        Values have whitespace stripped but not if strip=False.
        """
        f = CharField()
        self.assertEqual(f.clean(' 1'), '1')
        self.assertEqual(f.clean('1 '), '1')

        f = CharField(strip=False)
        self.assertEqual(f.clean(' 1'), ' 1')
        self.assertEqual(f.clean('1 '), '1 ')

    def test_strip_before_checking_empty(self):
        """
        A whitespace-only value, ' ', is stripped to an empty string and then
        converted to the empty value, None.
        """
        f = CharField(required=False, empty_value=None)
        self.assertIsNone(f.clean(' '))

    def test_clean_non_string(self):
        """CharField.clean() calls str(value) before stripping it."""
        class StringWrapper:
            def __init__(self, v):
                self.v = v

            def __str__(self):
                return self.v

        value = StringWrapper(' ')
        f1 = CharField(required=False, empty_value=None)
        self.assertIsNone(f1.clean(value))
        f2 = CharField(strip=False)
        self.assertEqual(f2.clean(value), ' ')

    def test_charfield_disabled(self):
        f = CharField(disabled=True)
        self.assertWidgetRendersTo(f, '<input type="text" name="f" id="id_f" disabled required />')

    def test_null_characters_prohibited(self):
        f = CharField()
        msg = 'Null characters are not allowed.'
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('\x00something')
