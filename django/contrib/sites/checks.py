from django.conf import settings
from django.core.checks import Error
from django.core.exceptions import ValidationError


def check_site_id(app_configs, **kwargs):
    # Inner import avoids AppRegistryNotReady
    from django.contrib.sites.models import Site

    if hasattr(settings, "SITE_ID"):
        try:
            site_id = Site._meta.pk.to_python(settings.SITE_ID)
        except ValidationError as exc:
            return [
                Error(
                    f"The SITE_ID setting failed to validate: {exc}.", id="sites.E101"
                ),
            ]
        else:
            # to_python() might coerce a SITE_ID of the wrong type to the valid
            # type, e.g. "1" to 1 for AutoField.
            if site_id != settings.SITE_ID:
                expected_type = type(site_id).__name__
                return [
                    Error(
                        f"The SITE_ID setting must be of type {expected_type}.",
                        id="sites.E101",
                    ),
                ]
    return []
