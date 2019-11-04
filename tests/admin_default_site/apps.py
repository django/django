from django.contrib.admin.apps import SimpleAdminConfig


class MyCustomAdminConfig(SimpleAdminConfig):
    verbose_name = 'My custom default admin site.'
    default_site = 'admin_default_site.sites.CustomAdminSite'
