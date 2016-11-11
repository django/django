from django.forms import Field, Form
from django.test import SimpleTestCase


class TestForm(Form):
    disabled_empty_initial = Field(disabled=True, required=False)
    disabled_initial = Field(disabled=True, initial='Test')


class DisabledFieldTest(SimpleTestCase):
    def test_disabled_field(self):
        disabled_field = Field(disabled=True)
        initial = disabled_field.initial
        self.assertFalse(disabled_field.has_changed(initial, ''))

        disabled_field = Field(disabled=True, initial='Test')
        initial = disabled_field.initial
        self.assertFalse(disabled_field.has_changed(initial, ''))

    def test_disabled_field_in_unbound_form(self):
        f = TestForm()
        self.assertFalse(f.is_bound)
        self.assertEqual(f.errors, {})
        self.assertFalse(f.is_valid())

    def test_disabled_field_in_bound_form(self):
        f = TestForm({'disabled_empty_initial': 'Test'})
        self.assertTrue(f.is_bound)
        self.assertEqual(f.errors, {})
        self.assertTrue(f.is_valid())

        self.assertEqual(f.cleaned_data['disabled_empty_initial'], None)
        self.assertEqual(f.cleaned_data['disabled_initial'], 'Test')
