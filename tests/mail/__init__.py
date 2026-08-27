import re
from contextlib import nullcontext

from django.conf import DEPRECATED_EMAIL_SETTINGS, EMAIL_SETTING_DEPRECATED_MSG
from django.core.mail.deprecation import NO_DEFAULT_MAILER_WARNING
from django.test import ignore_warnings, override_settings
from django.utils.deprecation import RemovedInDjango70Warning


# RemovedInDjango70Warning.
class override_deprecated_email_settings(override_settings):
    """Override settings, ignoring warnings for deprecated email settings.

    Like override_settings(), but suppresses deprecation warnings related to
    defining the overridden settings. Other settings can be included.

    Warnings are ignored only while installing and restoring the settings
    overrides, not for code within the context.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        deprecated_names = [
            name for name in kwargs if name in DEPRECATED_EMAIL_SETTINGS
        ]
        if deprecated_names:
            assert "{name}" in EMAIL_SETTING_DEPRECATED_MSG
            deprecated_names_re = r"|".join(
                re.escape(name) for name in deprecated_names
            )
            message_re = re.escape(EMAIL_SETTING_DEPRECATED_MSG).replace(
                re.escape("{name}"), rf"(?:{deprecated_names_re})"
            )
            self.ignore_warnings = ignore_warnings(
                category=RemovedInDjango70Warning, message=message_re
            )
        else:
            self.ignore_warnings = nullcontext()

    def enable(self):
        with self.ignore_warnings:
            super().enable()

    def disable(self):
        with self.ignore_warnings:
            super().disable()


# RemovedInDjango70Warning: Remove this helper and all uses of it.
def ignore_no_default_mailer_warning():
    return ignore_warnings(
        category=RemovedInDjango70Warning,
        message=re.escape(NO_DEFAULT_MAILER_WARNING),
    )
