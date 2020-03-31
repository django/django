import pickle

from django.forms import (
    BooleanField, Form, HiddenInput, RadioSelect, ValidationError,
)
from django.test import SimpleTestCase


class BooleanFieldTest(SimpleTestCase):

    def test_booleanfield_clean_1(self):
        f = BooleanField()
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean('')
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        self.assertTrue(f.clean(True))
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(False)
        self.assertTrue(f.clean(1))
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(0)
        self.assertTrue(f.clean('Django rocks'))
        self.assertTrue(f.clean('True'))
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean('False')

    def test_booleanfield_clean_2(self):
        f = BooleanField(required=False)
        self.assertIs(f.clean(''), False)
        self.assertIs(f.clean(None), False)
        self.assertIs(f.clean(True), True)
        self.assertIs(f.clean(False), False)
        self.assertIs(f.clean(1), True)
        self.assertIs(f.clean(0), False)
        self.assertIs(f.clean('1'), True)
        self.assertIs(f.clean('0'), False)
        self.assertIs(f.clean('Django rocks'), True)
        self.assertIs(f.clean('False'), False)
        self.assertIs(f.clean('false'), False)
        self.assertIs(f.clean('FaLsE'), False)

    def test_booleanfield_clean_null(self):
        f = BooleanField(null=True)
        self.assertIsNone(f.clean(''))
        self.assertTrue(f.clean(True))
        self.assertFalse(f.clean(False))
        self.assertIsNone(f.clean(None))
        self.assertFalse(f.clean('0'))
        self.assertTrue(f.clean('1'))
        self.assertIsNone(f.clean('2'))
        self.assertIsNone(f.clean('3'))
        self.assertIsNone(f.clean('hello'))
        self.assertTrue(f.clean('true'))
        self.assertFalse(f.clean('false'))

    def test_boolean_picklable(self):
        self.assertIsInstance(pickle.loads(pickle.dumps(BooleanField())), BooleanField)

    def test_booleanfield_changed(self):
        f = BooleanField()
        self.assertFalse(f.has_changed(None, None))
        self.assertFalse(f.has_changed(None, ''))
        self.assertFalse(f.has_changed('', None))
        self.assertFalse(f.has_changed('', ''))
        self.assertTrue(f.has_changed(False, 'on'))
        self.assertFalse(f.has_changed(True, 'on'))
        self.assertTrue(f.has_changed(True, ''))
        # Initial value may have mutated to a string due to show_hidden_initial (#19537)
        self.assertTrue(f.has_changed('False', 'on'))
        # HiddenInput widget sends string values for boolean but doesn't clean them in value_from_datadict
        self.assertFalse(f.has_changed(False, 'False'))
        self.assertFalse(f.has_changed(True, 'True'))
        self.assertTrue(f.has_changed(False, 'True'))
        self.assertTrue(f.has_changed(True, 'False'))

    def test_nullbooleanfield_changed_null(self):
        f = BooleanField(null=True)
        self.assertTrue(f.has_changed(False, None))
        self.assertTrue(f.has_changed(None, False))
        self.assertFalse(f.has_changed(None, None))
        self.assertFalse(f.has_changed(False, False))
        self.assertTrue(f.has_changed(True, False))
        self.assertTrue(f.has_changed(True, None))
        self.assertTrue(f.has_changed(True, False))
        # Initial value may have mutated to a string due to show_hidden_initial (#19537)
        self.assertTrue(f.has_changed('False', 'on'))
        # HiddenInput widget sends string values for boolean but doesn't clean them in value_from_datadict
        self.assertFalse(f.has_changed(False, 'False'))
        self.assertFalse(f.has_changed(True, 'True'))
        self.assertFalse(f.has_changed(None, ''))
        self.assertTrue(f.has_changed(False, 'True'))
        self.assertTrue(f.has_changed(True, 'False'))
        self.assertTrue(f.has_changed(None, 'False'))

    def test_disabled_has_changed(self):
        f = BooleanField(disabled=True)
        self.assertIs(f.has_changed('True', 'False'), False)

    def test_booleanfield_null1(self):
        # The internal value is preserved if using HiddenInput (#7753).
        class HiddenBooleanForm(Form):
            hidden_bool1 = BooleanField(null=True, widget=HiddenInput, initial=True)
            hidden_bool2 = BooleanField(null=True, widget=HiddenInput, initial=False)

        f = HiddenBooleanForm()
        self.assertHTMLEqual(
            '<input type="hidden" name="hidden_bool1" value="True" id="id_hidden_bool1">'
            '<input type="hidden" name="hidden_bool2" value="False" id="id_hidden_bool2">',
            str(f)
        )

    def test_booleanfield_null2(self):
        class HiddenBooleanForm(Form):
            hidden_bool1 = BooleanField(null=True, widget=HiddenInput, initial=True)
            hidden_bool2 = BooleanField(null=True, widget=HiddenInput, initial=False)

        f = HiddenBooleanForm({'hidden_bool1': 'True', 'hidden_bool2': 'False'})
        self.assertIsNone(f.full_clean())
        self.assertTrue(f.cleaned_data['hidden_bool1'])
        self.assertFalse(f.cleaned_data['hidden_bool2'])

    def test_booleanfield_null3(self):
        # Make sure we're compatible with MySQL, which uses 0 and 1 for its
        # boolean values (#9609).
        NULLBOOL_CHOICES = (('1', 'Yes'), ('0', 'No'), ('', 'Unknown'))

        class MySQLBooleanForm(Form):
            bool0 = BooleanField(null=True, widget=RadioSelect(choices=NULLBOOL_CHOICES))
            bool1 = BooleanField(null=True, widget=RadioSelect(choices=NULLBOOL_CHOICES))
            bool2 = BooleanField(null=True, widget=RadioSelect(choices=NULLBOOL_CHOICES))

        f = MySQLBooleanForm({'bool0': '1', 'bool1': '0', 'bool2': ''})
        self.assertIsNone(f.full_clean())
        self.assertTrue(f.cleaned_data['bool0'])
        self.assertFalse(f.cleaned_data['bool1'])
        self.assertIsNone(f.cleaned_data['bool2'])
