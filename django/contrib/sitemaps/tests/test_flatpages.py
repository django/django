from __future__ import unicode_literals

from unittest import skipUnless

from django.apps import apps
from django.conf import settings

from .base import SitemapTestsBase


class FlatpagesSitemapTests(SitemapTestsBase):

    @skipUnless(apps.is_installed('django.contrib.flatpages'),
                "django.contrib.flatpages app not installed.")
    def test_flatpage_sitemap(self):
        "Basic FlatPage sitemap test"

        # Import FlatPage inside the test so that when django.contrib.flatpages
        # is not installed we don't get problems trying to delete Site
        # objects (FlatPage has an M2M to Site, Site.delete() tries to
        # delete related objects, but the M2M table doesn't exist.
        from django.contrib.flatpages.models import FlatPage

        public = FlatPage.objects.create(
            url='/public/',
            title='Public Page',
            enable_comments=True,
            registration_required=False,
        )
        public.sites.add(settings.SITE_ID)
        private = FlatPage.objects.create(
            url='/private/',
            title='Private Page',
            enable_comments=True,
            registration_required=True
        )
        private.sites.add(settings.SITE_ID)
        response = self.client.get('/flatpages/sitemap.xml')
        # Public flatpage should be in the sitemap
        self.assertContains(response, '<loc>%s%s</loc>' % (self.base_url, public.url))
        # Private flatpage should not be in the sitemap
        self.assertNotContains(response, '<loc>%s%s</loc>' % (self.base_url, private.url))
