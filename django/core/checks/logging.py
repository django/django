from itertools import chain

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from . import Error, Tags, register


def is_valid_email(email):
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


@register(Tags.logging)
def check_admins_managers_emails(**kwargs):
    issues = []

    invalid_emails = [
        row[1]
        for row in chain(settings.ADMINS, settings.MANAGERS)
        if not is_valid_email(row[1])
    ]
    if invalid_emails:
        issues.append(
            Error(
                'The following email addresses in the ADMINS/MANAGERS setting are invalid:'
                ' %s' % ', '.join(invalid_emails),
                id='logging.E001',
            )
        )

    return issues
