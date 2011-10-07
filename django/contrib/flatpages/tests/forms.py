from django.conf import settings
from django.contrib.flatpages.forms import FlatpageForm
from django.test import TestCase

class FlatpageAdminFormTests(TestCase):
    def setUp(self):
        self.form_data = {
            'title': "A test page",
            'content': "This is a test",
            'sites': [settings.SITE_ID],
        }

    def test_flatpage_admin_form_url_validation(self):
        "The flatpage admin form correctly validates urls"
        self.assertTrue(FlatpageForm(data=dict(url='/new_flatpage/', **self.form_data)).is_valid())
        self.assertTrue(FlatpageForm(data=dict(url='/some.special~chars/', **self.form_data)).is_valid())
        self.assertTrue(FlatpageForm(data=dict(url='/some.very_special~chars-here/', **self.form_data)).is_valid())

        self.assertFalse(FlatpageForm(data=dict(url='/a space/', **self.form_data)).is_valid())
        self.assertFalse(FlatpageForm(data=dict(url='/a % char/', **self.form_data)).is_valid())
        self.assertFalse(FlatpageForm(data=dict(url='/a ! char/', **self.form_data)).is_valid())
        self.assertFalse(FlatpageForm(data=dict(url='/a & char/', **self.form_data)).is_valid())
        self.assertFalse(FlatpageForm(data=dict(url='/a ? char/', **self.form_data)).is_valid())

    def test_flatpage_admin_form_url_uniqueness_validation(self):
        "The flatpage admin form correctly enforces url uniqueness among flatpages of the same site"
        data = dict(url='/myflatpage1', **self.form_data)

        FlatpageForm(data=data).save()

        f = FlatpageForm(data=data)

        self.assertFalse(f.is_valid())

        self.assertEqual(
            f.errors,
            {'__all__': [u'Flatpage with url /myflatpage1 already exists for site example.com']})
