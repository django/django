from django.conf import settings
from django.core.checks import Tags, Warning, register
from django.core.mail.handler import DEFAULT_MAILER_ALIAS


@register(Tags.mail)
def check_mailers_default_alias(app_configs, **kwargs):
    if not settings.is_overridden("MAILERS"):
        return []

    if DEFAULT_MAILER_ALIAS in settings.MAILERS:
        return []

    if settings.MAILERS:
        hint = "Sending email without specifying 'using' will cause an error."
    else:
        hint = "Sending email will cause an error."

    return [
        Warning(
            "There is no 'default' configuration in your MAILERS setting.",
            hint=hint,
            id="mail.W001",
        )
    ]
