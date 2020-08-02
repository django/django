import re

from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _, ngettext


@deconstructible
class ASCIIUsernameValidator(validators.RegexValidator):
    regex = r'^[\w.@+-]+\Z'
    message = _(
        'Enter a valid username. This value may contain only English letters, '
        'numbers, and @/./+/-/_ characters.'
    )
    flags = re.ASCII

    def help_text(self):
        return _(
            'Enter a valid username. This value may contain only English letters, '
            'numbers, and @/./+/-/_ characters.'
        )


@deconstructible
class UnicodeUsernameValidator(validators.RegexValidator):
    regex = r'^[\w.@+-]+\Z'
    message = _(
        'Enter a valid username. This value may contain only letters, '
        'numbers, and @/./+/-/_ characters.'
    )
    flags = 0

    def help_text(self):
        return _(
            'Enter a valid username. This value may contain only English letters, '
            'numbers, and @/./+/-/_ characters.'
        )


@deconstructible
class UsernameMinimumLengthValidator:
    """
    Validate whether the username is of a minimum length.
    """
    def __init__(self, min_length=0):
        self.min_length = min_length

    def __call__(self, username):
        if self.min_length:
            if len(username) < self.min_length:
                raise ValidationError(
                    ngettext(
                        "This username is too short. It must contain at least %(min_length)d character.",
                        "This username is too short. It must contain at least %(min_length)d characters.",
                        self.min_length,
                    ),
                    code='invalid',
                    params={'min_length': self.min_length},
                )

    def help_text(self):
        return ngettext(
            "Your username must contain at least %(min_length)d character.",
            "Your username must contain at least %(min_length)d characters.",
            self.min_length
        ) % {'min_length': self.min_length}
