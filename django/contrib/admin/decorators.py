from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import site, AdminSite


def register(*models, **kwargs):
    """
    Registers the given model(s) and wrapped ModelAdmin class with admin site.

    The model(s) should be Model classes, not instances.

    A kwarg of `site` can be passed as the admin site, otherwise the default
    admin site will be used

    Calls the `register` method of the admin site to perform the actual
    registration.
    """
    def _model_admin_wrapper(admin_class):
        admin_site = kwargs.pop('site', site)
        # If there are any kwargs left after `site` is popped, they are invalid
        if kwargs:
            raise TypeError('Unsupported arguments: %s' % kwargs.keys())

        if not isinstance(admin_site, AdminSite):
            raise ValueError('Site must derive from AdminSite')

        if not issubclass(admin_class, ModelAdmin):
            raise ValueError('Wrapped class must derive from ModelAdmin.')

        admin_site.register(models, admin_class=admin_class)

        return admin_class
    return _model_admin_wrapper
