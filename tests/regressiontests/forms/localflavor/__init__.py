from django.forms import EmailField
from utils import LocalFlavorTestCase

class AssertFieldOutputTests(LocalFlavorTestCase):

    def test_assert_field_output(self):
        error_invalid = [u'Enter a valid e-mail address.']
        self.assertFieldOutput(EmailField, {'a@a.com': 'a@a.com'}, {'aaa': error_invalid})
        self.assertRaises(AssertionError, self.assertFieldOutput, EmailField, {'a@a.com': 'a@a.com'}, {'aaa': error_invalid + [u'Another error']})
        self.assertRaises(AssertionError, self.assertFieldOutput, EmailField, {'a@a.com': 'Wrong output'}, {'aaa': error_invalid})
        self.assertRaises(AssertionError, self.assertFieldOutput, EmailField, {'a@a.com': 'a@a.com'}, {'aaa': [u'Come on, gimme some well formatted data, dude.']})
