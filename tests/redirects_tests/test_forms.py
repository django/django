from unittest import skipIf

from django.apps import apps
from django.contrib.redirects.models import Redirect
from django.forms import modelform_factory
from django.test import TestCase, modify_settings


class RedirectFormTests(TestCase):
    def setUp(self):
        from django.contrib.redirects.forms import RedirectForm
        self.form_class = modelform_factory(Redirect, form=RedirectForm)

    @skipIf(not apps.is_installed('django.contrib.sites'),
            'django.contrib.sites is not installed')
    def test_site_overrides_empty_domain(self):
        from django.contrib.sites.models import Site
        site = Site.objects.create(domain='site.loc', name='site')
        form = self.form_class(data={
            'old_path': '/old/',
            'site': site.domain
        })

        redirect = form.save()

        self.assertEqual(redirect.domain, site.domain)

    @skipIf(not apps.is_installed('django.contrib.sites'),
            'django.contrib.sites is not installed')
    def test_non_empty_domain_overrides_site(self):
        from django.contrib.sites.models import Site
        site = Site.objects.create(domain='site.loc', name='site')
        form = self.form_class(data={
            'old_path': '/old/',
            'domain': 'test.loc',
            'site': site.domain
        })

        redirect = form.save()

        self.assertEqual(redirect.domain, 'test.loc')

    def test_save_instance_on_commit(self):
        form = self.form_class(data={'old_path': '/'})

        form.save(commit=False)
        self.assertFalse(Redirect.objects.all())

        redirect = form.save()
        self.assertTrue(Redirect.objects.get(old_path=redirect.old_path))

    @modify_settings(INSTALLED_APPS={'remove': 'django.contrib.sites'})
    def test_no_sites_framework(self):
        form = self.form_class(data={
            'old_path': '/old/',
            'site': 'site.loc'
        })

        form.save()

        self.assertTrue(
            Redirect.objects.get(domain='', old_path='/old/')
        )
