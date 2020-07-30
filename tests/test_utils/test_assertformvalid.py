from django.core.validators import validate_email
from django.test import SimpleTestCase
from django.forms import Form, CharField, IntegerField


class AssertFormValidTests(SimpleTestCase):
    class TestForm(Form):
        name = CharField(label='Name', max_length=4)
        age = IntegerField(label='Age')

    def test_with_valid_form(self):
        form = self.TestForm(data={
            'name': 'John',
            'age': 7,
        })
        self.assertFormValid(form)

    def test_error_message_with_invalid_form(self):
        form = self.TestForm(data={
            'name': 'John',
            'age': None,
        })
        expected_message = (
            'Form validation failed. Error(s):\n'
            '- age:\n'
            '    - This field is required.'
        )
        with self.assertRaisesMessage(AssertionError, expected_message):
            self.assertFormValid(form)


class AssertFormNotValidTests(SimpleTestCase):
    class TestForm(Form):
        name = CharField(label='Name', max_length=4)
        age = IntegerField(label='Age')

    class TestFormEmail(Form):
        email = CharField(label='email', max_length=4, validators=[validate_email])

    def test_valid_form(self):
        form = self.TestForm(data={
            'name': 'John',
            'age': 7,
        })
        msg = (
            'Error: Form is valid'
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormNotValid(form)

    def test_invalid_form_with_redundant_expected_errors(self):
        form = self.TestForm(data={
            'name': 'John',
            'age': None,
        })
        msg = (
            'Error(s):\n'
            '- (\'name\', \'max_length\') expected error not found.'
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormNotValid(
                form,
                expected_errors={
                    'age': 'required',
                    'name': 'max_length',
                }
            )

    def test_invalid_form_with_expected_errors_allow_other_errors(self):
        form = self.TestForm(data={
            'name': 'John',
            'age': None,
        })
        self.assertFormNotValid(
            form,
            expected_errors={'age': 'required'},
        )

    def test_invalid_form_with_expected_errors_disallow_other_errors(self):
        form = self.TestForm(data={
            'name': 'John',
            'age': None,
        })
        self.assertFormNotValid(
            form,
            expected_errors={'age': 'required'},
        )

    def test_with_invalid_form_with_unexpected_errors_disallow_other_errors(self):
        form = self.TestForm(data={
            'name': 'Johnny',
            'age': None,
        })
        msg = (
            "Error(s):\n"
            "- ('name', '['Ensure this value has at most 4 characters (it has 6).']') unexpected error found."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormNotValid(
                form,
                expected_errors={'age': 'required'},
            )

    def test_multiple_expected_errors_for_single_field(self):
        form = self.TestFormEmail(data={
            'email': 'not_an_email_address'
        })
        self.assertFormNotValid(
            form,
            expected_errors={'email': ('invalid', 'max_length')},
        )

    def test_partial_errors_raised_for_single_field(self):
        form = self.TestFormEmail(data={
            'email': 'not_an_email_address'
        })
        msg = (
            "Error(s):\n"
            "- ('email', '['Enter a valid email address.']') unexpected error found."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormNotValid(
                form,
                expected_errors={
                    'email': 'max_length'
                },
            )
