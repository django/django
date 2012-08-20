from __future__ import unicode_literals

from django.conf import settings
from django.contrib.flatpages.forms import FlatpageForm
from django.contrib.flatpages.models import FlatPage
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import translation

@override_settings(SITE_ID=1)
class FlatpageAdminFormTests(TestCase):
    fixtures = ['example_site']

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

    def test_flatpage_requires_leading_slash(self):
        form = FlatpageForm(data=dict(url='no_leading_slash/', **self.form_data))
        with translation.override('en'):
            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors['url'], ["URL is missing a leading slash."])

    @override_settings(APPEND_SLASH=True,
            MIDDLEWARE_CLASSES=('django.middleware.common.CommonMiddleware',))
    def test_flatpage_requires_trailing_slash_with_append_slash(self):
        form = FlatpageForm(data=dict(url='/no_trailing_slash', **self.form_data))
        with translation.override('en'):
            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors['url'], ["URL is missing a trailing slash."])

    @override_settings(APPEND_SLASH=False,
            MIDDLEWARE_CLASSES=('django.middleware.common.CommonMiddleware',))
    def test_flatpage_doesnt_requires_trailing_slash_without_append_slash(self):
        form = FlatpageForm(data=dict(url='/no_trailing_slash', **self.form_data))
        self.assertTrue(form.is_valid())

    def test_flatpage_admin_form_url_uniqueness_validation(self):
        "The flatpage admin form correctly enforces url uniqueness among flatpages of the same site"
        data = dict(url='/myflatpage1/', **self.form_data)

        FlatpageForm(data=data).save()

        f = FlatpageForm(data=data)

        self.assertFalse(f.is_valid())

        self.assertEqual(
            f.errors,
            {'__all__': ['Flatpage with url /myflatpage1/ already exists for site example.com']})

    def test_flatpage_admin_form_edit(self):
        """
        Existing flatpages can be edited in the admin form without triggering
        the url-uniqueness validation.

        """
        existing = FlatPage.objects.create(
            url="/myflatpage1/", title="Some page", content="The content")
        existing.sites.add(settings.SITE_ID)

        data = dict(url='/myflatpage1/', **self.form_data)

        f = FlatpageForm(data=data, instance=existing)

        self.assertTrue(f.is_valid(), f.errors)

        updated = f.save()

        self.assertEqual(updated.title, "A test page")

    def test_flatpage_nosites(self):
        data = dict(url='/myflatpage1/', **self.form_data)
        data.update({'sites': ''})

        f = FlatpageForm(data=data)

        self.assertFalse(f.is_valid())

        self.assertEqual(
            f.errors,
            {'sites': [translation.ugettext('This field is required.')]})

