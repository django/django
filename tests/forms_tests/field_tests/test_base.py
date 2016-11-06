from django.forms import ChoiceField, Field, Form, Select
from django.test import SimpleTestCase


class BasicFieldsTests(SimpleTestCase):

    def test_field_sets_widget_is_required(self):
        self.assertTrue(Field(required=True).widget.is_required)
        self.assertFalse(Field(required=False).widget.is_required)

    def test_cooperative_multiple_inheritance(self):
        class A(object):
            def __init__(self):
                self.class_a_var = True
                super(A, self).__init__()

        class ComplexField(Field, A):
            def __init__(self):
                super(ComplexField, self).__init__()

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


class DisabledFieldTests(SimpleTestCase):
    def test_disabled_field_has_changed_always_false(self):
        disabled_field = Field(disabled=True)
        self.assertFalse(disabled_field.has_changed('x', 'y'))
