from django.contrib.flatpages.admin import FlatpageForm
from django.test import TestCase

class FlatpageAdminFormTests(TestCase):
    def setUp(self):
        self.form_data = {
            'title': "A test page",
            'content': "This is a test",
            'sites': [1],
        }

    def test_flatpage_admin_form_url_validation(self):
        "The flatpage admin form validates correctly validates urls"
        self.assertTrue(FlatpageForm(data=dict(url='/new_flatpage/', **self.form_data)).is_valid())
        self.assertTrue(FlatpageForm(data=dict(url='/some.special~chars/', **self.form_data)).is_valid())
        self.assertTrue(FlatpageForm(data=dict(url='/some.very_special~chars-here/', **self.form_data)).is_valid())

        self.assertFalse(FlatpageForm(data=dict(url='/a space/', **self.form_data)).is_valid())
        self.assertFalse(FlatpageForm(data=dict(url='/a % char/', **self.form_data)).is_valid())
        self.assertFalse(FlatpageForm(data=dict(url='/a ! char/', **self.form_data)).is_valid())
        self.assertFalse(FlatpageForm(data=dict(url='/a & char/', **self.form_data)).is_valid())
        self.assertFalse(FlatpageForm(data=dict(url='/a ? char/', **self.form_data)).is_valid())
