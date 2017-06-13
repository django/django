from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_site_model():
    """
    Return the Site model that is active in this project.
    """
    try:
        return django_apps.get_model(settings.SITES_SITE_MODEL, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured("SITES_SITE_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "SITES_SITE_MODEL refers to model '%s' that has not been installed" % settings.SITES_SITE_MODEL
        )


default_app_config = 'django.contrib.sites.apps.SitesConfig'
