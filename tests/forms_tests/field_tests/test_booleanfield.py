import pickle

from django.forms import BooleanField, ValidationError
from django.test import SimpleTestCase


class BooleanFieldTest(SimpleTestCase):

    def test_booleanfield_clean_false_required(self):
        f = BooleanField(required=True)
        test_values = ['', None, False, 0, 'False']
        for value in test_values:
            with self.assertRaisesMessage(
                ValidationError,
                'This field is required.',
            ):
                f.clean(value)

    def test_booleanfield_clean_null(self):
        f = BooleanField(required=False, null=True)
        self.assertIs(f.clean(None), None)
        self.assertIs(f.clean(''), None)

    def test_booleanfield_clean_ints(self):
        f = BooleanField(required=False)
        self.assertIs(f.clean(True), True)
        self.assertIs(f.clean(False), False)
        self.assertIs(f.clean(1), True)
        self.assertIs(f.clean(0), False)

    def test_booleanfield_clean_truthy(self):
        f = BooleanField()
        self.assertTrue(f.clean(True))
        self.assertTrue(f.clean(1))
        self.assertTrue(f.clean('Django rocks'))
        self.assertTrue(f.clean('True'))

    def test_booleanfield_clean_strings(self):
        f = BooleanField(required=False)
        self.assertIs(f.clean('1'), True)
        self.assertIs(f.clean('0'), False)
        self.assertIs(f.clean('Django rocks'), True)
        self.assertIs(f.clean('False'), False)
        self.assertIs(f.clean('false'), False)
        self.assertIs(f.clean('FaLsE'), False)

    def test_boolean_picklable(self):
        self.assertIsInstance(pickle.loads(pickle.dumps(BooleanField())), BooleanField)

    def test_booleanfield_has_changed_empty_value(self):
        f = BooleanField()
        self.assertFalse(f.has_changed(None, None))
        self.assertFalse(f.has_changed(None, ''))
        self.assertFalse(f.has_changed('', None))
        self.assertFalse(f.has_changed('', ''))
        self.assertTrue(f.has_changed(True, ''))

    def test_booleanfield_has_changed_advanced_truthy_strings(self):
        # Initial value may have mutated to a string due to show_hidden_initial (#19537)
        f = BooleanField()
        self.assertTrue(f.has_changed('False', 'on'))
        self.assertTrue(f.has_changed(False, 'on'))
        self.assertFalse(f.has_changed(True, 'on'))

    def test_booleanfield_has_changed_basic_truthy_strings(self):
        f = BooleanField()
        self.assertTrue(f.has_changed(False, 'True'))
        self.assertTrue(f.has_changed(True, 'False'))

    def test_booleanfield_has_not_changed_basic_truthy_strings(self):
        f = BooleanField()
        self.assertFalse(f.has_changed(False, 'False'))
        self.assertFalse(f.has_changed(True, 'True'))

    def test_disabled_has_changed(self):
        f = BooleanField(disabled=True)
        self.assertIs(f.has_changed('True', 'False'), False)
