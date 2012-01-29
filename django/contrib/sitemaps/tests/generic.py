from django.contrib.auth.models import User

from .base import SitemapTestsBase

class GenericViewsSitemapTests(SitemapTestsBase):

    def test_generic_sitemap(self):
        "A minimal generic sitemap can be rendered"
        response = self.client.get('/generic/sitemap.xml')
        expected = ''
        for username in User.objects.values_list("username", flat=True):
            expected += "<url><loc>%s/users/%s/</loc></url>" % (self.base_url, username)
        self.assertEqual(response.content, """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
%s
</urlset>
""" % expected)
