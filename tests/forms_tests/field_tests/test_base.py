import copy

from django.forms import ChoiceField, Field, Form, Select
from django.test import SimpleTestCase


class BasicFieldsTests(SimpleTestCase):

    def test_field_sets_widget_is_required(self):
        self.assertTrue(Field(required=True).widget.is_required)
        self.assertFalse(Field(required=False).widget.is_required)

    def test_cooperative_multiple_inheritance(self):
        class A:
            def __init__(self):
                self.class_a_var = True
                super().__init__()

        class ComplexField(Field, A):
            def __init__(self):
                super().__init__()

        f = ComplexField()
        self.assertTrue(f.class_a_var)

    def test_field_deepcopies_widget_instance(self):
        class CustomChoiceField(ChoiceField):
            widget = Select(attrs={'class': 'my-custom-class'})

        class TestForm(Form):
            field1 = CustomChoiceField(choices=[])
            field2 = CustomChoiceField(choices=[])

        f = TestForm()
        f.fields['field1'].choices = [('1', '1')]
        f.fields['field2'].choices = [('2', '2')]
        self.assertEqual(f.fields['field1'].widget.choices, [('1', '1')])
        self.assertEqual(f.fields['field2'].widget.choices, [('2', '2')])

    def test_field_deepcopies_error_messages(self):
        """
        Test that __deepcopy__ creates a deep copy of the error_messages dict.
        Modifying error_messages on one field instance should not affect other
        instances.
        """
        class MyForm(Form):
            field1 = Field()
            field2 = Field()

        form1 = MyForm()
        form2 = MyForm()

        # Store original error message
        original_error = str(form2.fields['field1'].error_messages['required'])

        # Modify error_messages on form1's field1
        form1.fields['field1'].error_messages['required'] = 'Custom error for form1'

        # form2's field1 should not be affected
        self.assertEqual(
            form2.fields['field1'].error_messages['required'],
            original_error
        )

        # form1's field2 should not be affected either
        self.assertEqual(
            form1.fields['field2'].error_messages['required'],
            original_error
        )

        # Adding a new error message to form1's field1 should not affect form2
        form1.fields['field1'].error_messages['custom'] = 'New custom error'
        self.assertNotIn('custom', form2.fields['field1'].error_messages)

    def test_field_direct_deepcopy_error_messages(self):
        """
        Test that directly deepcopying a field creates independent error_messages.
        """
        field1 = Field(error_messages={'required': 'Original required error'})
        field2 = copy.deepcopy(field1)

        # Modify field1's error_messages
        field1.error_messages['required'] = 'Modified required error'
        field1.error_messages['new_error'] = 'A new error'

        # field2 should not be affected
        self.assertEqual(field2.error_messages['required'], 'Original required error')
        self.assertNotIn('new_error', field2.error_messages)


class DisabledFieldTests(SimpleTestCase):
    def test_disabled_field_has_changed_always_false(self):
        disabled_field = Field(disabled=True)
        self.assertFalse(disabled_field.has_changed('x', 'y'))
