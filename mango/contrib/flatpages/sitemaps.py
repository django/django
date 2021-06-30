from mango.apps import apps as mango_apps
from mango.contrib.sitemaps import Sitemap
from mango.core.exceptions import ImproperlyConfigured


class FlatPageSitemap(Sitemap):
    def items(self):
        if not mango_apps.is_installed('mango.contrib.sites'):
            raise ImproperlyConfigured("FlatPageSitemap requires mango.contrib.sites, which isn't installed.")
        Site = mango_apps.get_model('sites.Site')
        current_site = Site.objects.get_current()
        return current_site.flatpage_set.filter(registration_required=False)
