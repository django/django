from django.conf import settings
from django.core.checks import Tags, Warning, register
from django.core.mail import DEFAULT_MAILER_ALIAS


@register(Tags.mail)
def check_mailers_default_alias(app_configs, **kwargs):
    if not settings.is_overridden("MAILERS"):
        return []

    if DEFAULT_MAILER_ALIAS in settings.MAILERS:
        return []

    if settings.MAILERS:
        hint = (
            f"Add a '{DEFAULT_MAILER_ALIAS}' entry to MAILERS, or pass 'using' when "
            "sending email."
        )
    else:
        hint = f"Add a '{DEFAULT_MAILER_ALIAS}' entry to MAILERS."

    return [
        Warning(
            f"Your MAILERS setting has no '{DEFAULT_MAILER_ALIAS}' entry. Sending "
            "email without a valid mailer will fail.",
            hint=hint,
            id="mail.W001",
        )
    ]
