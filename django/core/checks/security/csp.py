from django.conf import settings

from .. import Tags, Warning, register

W026 = Warning(
    "Each enabled CSP setting (SECURE_CSP, SECURE_CSP_REPORT_ONLY) must be a "
    "dictionary.",
    id="security.W026",
)


@register(Tags.security)
def check_csp_directives(app_configs, **kwargs):
    """
    Validate that CSP settings are properly configured when enabled.

    Ensures both SECURE_CSP and SECURE_CSP_REPORT_ONLY are dictionaries.
    """
    errors = []

    # Check both CSP settings
    for setting_name in ("SECURE_CSP", "SECURE_CSP_REPORT_ONLY"):
        setting_value = getattr(settings, setting_name, None)

        # Only validate if the setting is explicitly set (not None or empty dict)
        if setting_value:
            if not isinstance(setting_value, dict):
                errors.append(W026)

    return errors
