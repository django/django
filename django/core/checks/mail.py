from django.conf import settings
from django.core.checks import Error, Tags, Warning, register
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


NON_PRODUCTION_EMAIL_BACKENDS = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
    "django.core.mail.backends.locmem.EmailBackend",
}


@register(Tags.mail, deploy=True)
def check_mailers_production_backend(app_configs, **kwargs):
    try:
        backend = settings.MAILERS[DEFAULT_MAILER_ALIAS]["BACKEND"]
    except (AttributeError, KeyError):
        # There is no "default" backend to inspect: either MAILERS is not
        # defined, or there is no "default" entry, or no "BACKEND" key in it.
        # An omitted BACKEND defaults to SMTP, which is fine.
        return []

    if backend not in NON_PRODUCTION_EMAIL_BACKENDS:
        return []

    return [
        Error(
            f"Your MAILERS setting uses a development-only email backend in the "
            f"'{DEFAULT_MAILER_ALIAS}' entry ({backend}).",
            hint=(
                "Use a production-ready email backend, such as the SMTP backend, "
                "otherwise email will not be sent."
            ),
            id="mail.E001",
        )
    ]
