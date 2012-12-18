from django.conf import settings
from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import site, AlreadyRegistered
from django.core.exceptions import ImproperlyConfigured
from django.db.models.base import ModelBase


def register(*models, **kwargs):
    """
    Registers the given model(s) and wrapped ModelAdmin class with admin site.

    The model(s) should be Model classes, not instances.

    A kwarg of `site` can be passed as the admin site, otherwise the default
    admin site will be used

    Raises AlreadyRegistered if a model is already registered

    Raises ImproperlyConfigured if a model is abstract
    """
    def _model_admin_wrapper(admin_class):
        admin_site = kwargs.pop('site', site)
        # If there are any kwargs left after `site` is popped, they are invalid
        if kwargs:
            raise TypeError('Unsupported arguments: %s' % kwargs.keys())

        if not issubclass(admin_class, ModelAdmin):
            raise ValueError('Wrapped class must derive from ModelAdmin.')

        # Don't import the humongous validation code unless required
        if settings.DEBUG:
            from django.contrib.admin.validation import validate
        else:
            validate = lambda model, adminclass: None

        for model in models:
            if not isinstance(model, ModelBase):
                raise ValueError('Only Model classes can be registered.')

            if model._meta.abstract:
                raise ImproperlyConfigured('The model %s is abstract, so it '
                        'cannot be registered with admin.' % model.__name__)

            if model in admin_site._registry:
                raise AlreadyRegistered('The model %s is already registered.'
                                        % model.__name__)

            # Ignore the registration if model has been swapped out
            if not model._meta.swapped:
                # Validate (which might be a no-op)
                validate(admin_class, model)

                # Instantiate the admin class to save in the registry
                admin_site._registry[model] = admin_class(model, admin_site)
        return admin_class
    return _model_admin_wrapper
