from thibaud.apps import apps as thibaud_apps
from thibaud.contrib.sitemaps import Sitemap
from thibaud.core.exceptions import ImproperlyConfigured


class FlatPageSitemap(Sitemap):
    def items(self):
        if not thibaud_apps.is_installed("thibaud.contrib.sites"):
            raise ImproperlyConfigured(
                "FlatPageSitemap requires thibaud.contrib.sites, which isn't installed."
            )
        Site = thibaud_apps.get_model("sites.Site")
        current_site = Site.objects.get_current()
        return current_site.flatpage_set.filter(registration_required=False)
