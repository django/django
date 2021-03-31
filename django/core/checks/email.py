import re

from django.conf import settings

from . import Error, Tags, register


@register(Tags.email)
def check_messageid_fqdn(app_configs, **kwargs):
    errors = []
    pattern = r'^(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])$'  # NOQA
    if (settings.EMAIL_FQDN and
            not re.match(pattern, settings.EMAIL_FQDN)):
        errors.append(Error('EMAIL_FQDN must contain a valid domain name'))
    return errors
