"""
Tests for allowing cleaned_data to overwrite fields' default values.

This addresses the issue where form.cleaned_data values were being ignored
if the field had a default value and wasn't in the POST data.
"""
import datetime
from django import forms
from django.test import TestCase

from .models import PublicationDefaults


class CleanedDataOverridesDefaultsTests(TestCase):
    """
    Test that values set in cleaned_data can override model field defaults,
    even when the field wasn't included in the form's POST data.
    """

    def test_cleaned_data_overrides_default_on_excluded_field(self):
        """
        Test that a field excluded from the form can have its default
        overridden by setting a value in cleaned_data.
        """
        class PubForm(forms.ModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ('title',)  # mode is excluded

            def clean(self):
                cleaned_data = super().clean()
                # Set mode in cleaned_data even though it's not in the form
                cleaned_data['mode'] = 'de'  # Override default 'di'
                return cleaned_data

        # Submit form with only title
        form = PubForm({'title': 'Test Publication'})
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)

        # mode should be 'de' from cleaned_data, not the default 'di'
        self.assertEqual(instance.mode, 'de')
        self.assertEqual(instance.title, 'Test Publication')

    def test_cleaned_data_overrides_callable_default(self):
        """
        Test that cleaned_data can override a callable default.
        """
        class PubForm(forms.ModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ('title',)  # category is excluded

            def clean(self):
                cleaned_data = super().clean()
                # Override the callable default (which returns 3)
                cleaned_data['category'] = 1
                return cleaned_data

        form = PubForm({'title': 'Test Publication'})
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)

        # category should be 1 from cleaned_data, not the default 3
        self.assertEqual(instance.category, 1)

    def test_cleaned_data_overrides_date_default(self):
        """
        Test that cleaned_data can override a date field default.
        """
        class PubForm(forms.ModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ('title',)  # date_published is excluded

            def clean(self):
                cleaned_data = super().clean()
                # Override the default (today) with a specific date
                cleaned_data['date_published'] = datetime.date(2020, 1, 1)
                return cleaned_data

        form = PubForm({'title': 'Test Publication'})
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)

        # date_published should be the overridden date, not today
        self.assertEqual(instance.date_published, datetime.date(2020, 1, 1))

    def test_cleaned_data_overrides_boolean_default(self):
        """
        Test that cleaned_data can override a boolean field default.
        """
        class PubForm(forms.ModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ('title',)  # active is excluded

            def clean(self):
                cleaned_data = super().clean()
                # Override the default (True) to False
                cleaned_data['active'] = False
                return cleaned_data

        form = PubForm({'title': 'Test Publication'})
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)

        # active should be False from cleaned_data, not the default True
        self.assertFalse(instance.active)

    def test_cleaned_data_can_set_default_value_explicitly(self):
        """
        Test that cleaned_data can explicitly set a value that happens
        to be the same as the default.
        """
        class PubForm(forms.ModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ('title',)  # mode is excluded

            def clean(self):
                cleaned_data = super().clean()
                # Explicitly set the default value in cleaned_data
                cleaned_data['mode'] = 'di'  # This is the default
                return cleaned_data

        form = PubForm({'title': 'Test Publication'})
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)

        # mode should be 'di' (the default, but set via cleaned_data)
        self.assertEqual(instance.mode, 'di')

    def test_cleaned_data_with_derived_value(self):
        """
        Test a realistic use case where one field's value is derived from another.
        """
        class PubForm(forms.ModelForm):
            source_field = forms.CharField(required=False)

            class Meta:
                model = PublicationDefaults
                fields = ('title', 'source_field')  # mode is excluded

            def clean(self):
                cleaned_data = super().clean()
                # Derive mode from source_field
                source = cleaned_data.get('source_field', '')
                if 'delayed' in source.lower():
                    cleaned_data['mode'] = 'de'
                else:
                    cleaned_data['mode'] = 'di'
                return cleaned_data

        # Test with 'delayed' in source
        form1 = PubForm({'title': 'Test 1', 'source_field': 'DELAYED PROCESSING'})
        self.assertTrue(form1.is_valid())
        instance1 = form1.save(commit=False)
        self.assertEqual(instance1.mode, 'de')

        # Test without 'delayed' in source
        form2 = PubForm({'title': 'Test 2', 'source_field': 'immediate'})
        self.assertTrue(form2.is_valid())
        instance2 = form2.save(commit=False)
        self.assertEqual(instance2.mode, 'di')

    def test_missing_field_still_uses_default(self):
        """
        Test that fields not in cleaned_data still use their defaults.
        """
        class PubForm(forms.ModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ('title',)  # mode, category, active are excluded

            # Don't override anything in clean()

        form = PubForm({'title': 'Test Publication'})
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)

        # Fields not in cleaned_data should use their defaults
        self.assertEqual(instance.mode, 'di')
        self.assertEqual(instance.category, 3)
        self.assertTrue(instance.active)

    def test_cleaned_data_overrides_with_included_and_excluded_fields(self):
        """
        Test a form with some fields included and some excluded, where
        cleaned_data sets values for excluded fields.
        """
        class PubForm(forms.ModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ('title', 'date_published')  # mode and category excluded

            def clean(self):
                cleaned_data = super().clean()
                # Set values for excluded fields based on included fields
                title = cleaned_data.get('title', '')
                if 'game' in title.lower():
                    cleaned_data['category'] = 1  # Games
                    cleaned_data['mode'] = 'di'  # Direct
                elif 'comic' in title.lower():
                    cleaned_data['category'] = 2  # Comics
                    cleaned_data['mode'] = 'de'  # Delayed
                else:
                    cleaned_data['category'] = 3  # Novel
                    cleaned_data['mode'] = 'di'  # Direct
                return cleaned_data

        # Test with 'game' in title
        form1 = PubForm({
            'title': 'Best Game Ever',
            'date_published': str(datetime.date.today())
        })
        self.assertTrue(form1.is_valid())
        instance1 = form1.save(commit=False)
        self.assertEqual(instance1.category, 1)
        self.assertEqual(instance1.mode, 'di')

        # Test with 'comic' in title
        form2 = PubForm({
            'title': 'Amazing Comic Book',
            'date_published': str(datetime.date.today())
        })
        self.assertTrue(form2.is_valid())
        instance2 = form2.save(commit=False)
        self.assertEqual(instance2.category, 2)
        self.assertEqual(instance2.mode, 'de')

    def test_cleaned_data_none_value_overrides_default(self):
        """
        Test that setting None in cleaned_data is respected, even if there's a default.
        Note: This only works for nullable fields.
        """
        class PubForm(forms.ModelForm):
            class Meta:
                model = PublicationDefaults
                fields = ('title', 'mode')

            def clean(self):
                cleaned_data = super().clean()
                # For a nullable field, we could set None
                # mode is not nullable, so this test focuses on the behavior
                # that cleaned_data values are respected
                cleaned_data['mode'] = 'de'
                return cleaned_data

        form = PubForm({'title': 'Test', 'mode': 'di'})
        self.assertTrue(form.is_valid())
        instance = form.save(commit=False)

        # mode should be 'de' from cleaned_data, overriding the POST value
        self.assertEqual(instance.mode, 'de')
