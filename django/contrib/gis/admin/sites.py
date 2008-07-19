from django.contrib.admin import sites
from django.contrib.gis.admin.options import GeoModelAdmin
from django.db.models.loading import get_apps

class GeoAdminSite(sites.AdminSite):
    """
    The GeoAdminSite is overloaded from the AdminSite to provide facilities
    for editing geographic fields (using the GeoModelAdmin for the options
    class instead of ModelAdmin).
    """
    def register(self, model_or_iterable, admin_class=None, **options):
        "Overloaded register method that uses GeoModelAdmin."
        admin_class = admin_class or GeoModelAdmin
        try:
            return super(GeoAdminSite, self).register(model_or_iterable, admin_class, **options)
        except sites.AlreadyRegistered:
            # Unlike the default behavior in newforms-admin we won't 
            # raise this exception.
            pass

# `site` is an instance of GeoAdminSite
site = GeoAdminSite()

# Re-registering models that appear normally in AdminSite with the 
# GeoAdminSite (if the user has these installed).
APPS = get_apps()

# Registering the `auth` Group & User models.
from django.contrib.auth import models, admin
if models in APPS:
    site.register(models.Group, admin.GroupAdmin)
    site.register(models.User, admin.UserAdmin)

# Registering the `sites` Site model.
from django.contrib.sites import models, admin
if models in APPS:
    site.register(models.Site, admin.SiteAdmin)
