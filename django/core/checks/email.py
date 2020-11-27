import re

from django.conf import settings

from . import Error, Tags, register


@register(Tags.email)
def check_messageid_fqdn(app_configs, **kwargs):
    errors = []
    pattern = r'^((?!-)[A-Za-z0-9-]{1,63}(?<!-)\\.)+[A-Za-z]{2,6}$'
    if (settings.EMAIL_MESSAGEID_FQDN and
            not re.match(pattern, settings.EMAIL_MESSAGEID_FQDN)):
        errors.append(Error('EMAIL_MESSAGEID_FQDN must contain a valid domain name'))
    return errors
