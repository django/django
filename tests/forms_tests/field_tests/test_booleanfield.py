import pickle

from django.core.exceptions import ValidationError
from django.forms import BooleanField
from django.test import SimpleTestCase


class BooleanFieldTest(SimpleTestCase):
    def test_booleanfield_clean_1(self):
        f = BooleanField()
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean("")
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(None)
        self.assertTrue(f.clean(True))
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(False)
        self.assertTrue(f.clean(1))
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean(0)
        self.assertTrue(f.clean("Django rocks"))
        self.assertTrue(f.clean("True"))
        with self.assertRaisesMessage(ValidationError, "'This field is required.'"):
            f.clean("False")

    def test_booleanfield_clean_2(self):
        f = BooleanField(required=False)
        self.assertIs(f.clean(""), False)
        self.assertIs(f.clean(None), False)
        self.assertIs(f.clean(True), True)
        self.assertIs(f.clean(False), False)
        self.assertIs(f.clean(1), True)
        self.assertIs(f.clean(0), False)
        self.assertIs(f.clean("1"), True)
        self.assertIs(f.clean("0"), False)
        self.assertIs(f.clean("Django rocks"), True)
        self.assertIs(f.clean("False"), False)
        self.assertIs(f.clean("false"), False)
        self.assertIs(f.clean("FaLsE"), False)

    def test_boolean_picklable(self):
        self.assertIsInstance(pickle.loads(pickle.dumps(BooleanField())), BooleanField)

    def test_booleanfield_changed(self):
        f = BooleanField()
        self.assertFalse(f.has_changed(None, None))
        self.assertFalse(f.has_changed(None, ""))
        self.assertFalse(f.has_changed("", None))
        self.assertFalse(f.has_changed("", ""))
        self.assertTrue(f.has_changed(False, "on"))
        self.assertFalse(f.has_changed(True, "on"))
        self.assertTrue(f.has_changed(True, ""))
        # Initial value may have mutated to a string due to show_hidden_initial (#19537)
        self.assertTrue(f.has_changed("False", "on"))
        # HiddenInput widget sends string values for boolean but doesn't clean
        # them in value_from_datadict.
        self.assertFalse(f.has_changed(False, "False"))
        self.assertFalse(f.has_changed(True, "True"))
        self.assertTrue(f.has_changed(False, "True"))
        self.assertTrue(f.has_changed(True, "False"))

    def test_disabled_has_changed(self):
        f = BooleanField(disabled=True)
        self.assertIs(f.has_changed("True", "False"), False)
