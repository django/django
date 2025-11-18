"""
Test Field.__deepcopy__() method.
"""
import copy

from django.forms import CharField, IntegerField, Form
from django.test import SimpleTestCase


class FieldDeepCopyTest(SimpleTestCase):
    """
    Test that Field.__deepcopy__() properly deep copies all attributes,
    including error_messages.
    """

    def test_field_deepcopy_independence(self):
        """
        Test that deepcopy creates an independent field.
        """
        field1 = CharField()
        field2 = copy.deepcopy(field1)
        self.assertIsNot(field1, field2)
        self.assertIsNot(field1.widget, field2.widget)

    def test_field_deepcopy_error_messages(self):
        """
        Test that deepcopy creates independent error_messages dictionaries.
        Regression test for the issue where error_messages were shared
        between field copies.
        """
        # Create a field with custom error messages
        field1 = CharField(error_messages={'required': 'Custom required message'})

        # Deep copy the field
        field2 = copy.deepcopy(field1)

        # Verify that error_messages are copied correctly
        self.assertEqual(field1.error_messages['required'], 'Custom required message')
        self.assertEqual(field2.error_messages['required'], 'Custom required message')

        # Modify error_messages in the copy
        field2.error_messages['required'] = 'Modified message'

        # The original field should not be affected
        self.assertEqual(field1.error_messages['required'], 'Custom required message')
        self.assertEqual(field2.error_messages['required'], 'Modified message')

        # error_messages should be different objects
        self.assertIsNot(field1.error_messages, field2.error_messages)

    def test_field_deepcopy_default_error_messages(self):
        """
        Test that deepcopy works correctly with default error_messages.
        """
        field1 = CharField()
        field2 = copy.deepcopy(field1)

        # Modify error message in copy
        field2.error_messages['required'] = 'Modified in copy'

        # Original should not be affected
        self.assertNotEqual(
            field1.error_messages['required'],
            'Modified in copy'
        )
        self.assertEqual(
            field2.error_messages['required'],
            'Modified in copy'
        )

    def test_form_instances_independent_error_messages(self):
        """
        Test that form instances have independent error_messages.

        This is a regression test for the issue where modifying error_messages
        in one form instance would affect all other instances of the same form.
        """
        class TestForm(Form):
            name = CharField(error_messages={'required': 'Name is required'})
            age = IntegerField(error_messages={'invalid': 'Enter a valid age'})

        # Create two form instances
        form1 = TestForm()
        form2 = TestForm()

        # Verify initial state
        self.assertEqual(
            form1.fields['name'].error_messages['required'],
            'Name is required'
        )
        self.assertEqual(
            form2.fields['name'].error_messages['required'],
            'Name is required'
        )

        # Modify error message in form1
        form1.fields['name'].error_messages['required'] = 'Form1 custom message'

        # form2 should not be affected
        self.assertEqual(
            form1.fields['name'].error_messages['required'],
            'Form1 custom message'
        )
        self.assertEqual(
            form2.fields['name'].error_messages['required'],
            'Name is required'
        )

        # error_messages should be different objects
        self.assertIsNot(
            form1.fields['name'].error_messages,
            form2.fields['name'].error_messages
        )

    def test_form_instances_independent_nested_error_messages(self):
        """
        Test that nested modifications to error messages don't affect other instances.
        """
        class TestForm(Form):
            field1 = CharField()

        form1 = TestForm()
        form2 = TestForm()

        # Add a new error message key to form1
        form1.fields['field1'].error_messages['custom_error'] = 'Custom error'

        # form2 should not have this key
        self.assertIn('custom_error', form1.fields['field1'].error_messages)
        self.assertNotIn('custom_error', form2.fields['field1'].error_messages)
