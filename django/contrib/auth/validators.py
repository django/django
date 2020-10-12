import re

from django.core import validators
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _, ngettext


@deconstructible
class ASCIIUsernameValidator(validators.RegexValidator):
    regex = r'^[\w.@+-]+\Z'
    message = _(
        'Enter a valid username. This value may contain only letters from the Latin alphabet,'
        ' numbers, and @/./+/-/_ characters.'
    )
    flags = re.ASCII

    def help_text(self):
        return _(
            'Enter a valid username. This value may contain only letters from the Latin alphabet,'
            ' numbers, and @/./+/-/_ characters.'
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
            'Enter a valid username. This value may contain only letters, '
            'numbers, and @/./+/-/_ characters.'
        )


@deconstructible
class UsernameMinimumLengthValidator(validators.MinLengthValidator):
    """
    Validate whether the username is of a minimum length.
    """
    def help_text(self):
        return ngettext(
            'Your username must contain at least %(limit_value)d character.',
            'Your username must contain at least %(limit_value)d characters.',
            self.limit_value
        ) % {'limit_value': self.limit_value}
