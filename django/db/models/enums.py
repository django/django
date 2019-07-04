from enum import Enum, EnumMeta

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

__all__ = ['ChoiceEnum', 'ChoiceIntEnum', 'ChoiceStrEnum']


class ChoiceEnumMeta(EnumMeta):
    def __new__(metacls, classname, bases, classdict):
        choices = {}
        for key in classdict._member_names:
            value = classdict[key]
            if isinstance(value, (list, tuple)):
                try:
                    value, display = value
                except ValueError as e:
                    raise ValueError('Invalid ChoiceEnum member %r' % key) from e
            else:
                display = key.replace('_', ' ').title()
            choices[value] = display
            # Use dict.__setitem__() to suppress defenses against double
            # assignment in enum's classdict.
            dict.__setitem__(classdict, key, value)
        cls = super().__new__(metacls, classname, bases, classdict)
        cls._choices = choices
        cls.choices = tuple(choices.items())
        return cls


class ChoiceEnum(Enum, metaclass=ChoiceEnumMeta):
    """
    A class suitable for using as an enum with translatable choices.

    The typical use is similar to the stdlib's enums, with three
    modifications:
    * Instead of values in the enum, we use "(value, display)" tuples.
      The "display" can be a lazy translatable string.
    * We add a class method "choices()" which returns a value suitable
      for use as "choices" in a Django field definition.
    * We add a property "display" on enum values, to return the display
      specified.

    Thus, the definition of the Enum class can look like:

    class YearInSchool(ChoiceStrEnum):
        FRESHMAN = 'FR', _('Freshman')
        SOPHOMORE = 'SO', _('Sophomore')
        JUNIOR = 'JR', _('Junior')
        SENIOR = 'SR', _('Senior')

    or even

    class Suit(ChoiceIntEnum):
        DIAMOND = 1, _('Diamond')
        SPADE   = 2, _('Spade')
        HEART   = 3, _('Heart')
        CLUB    = 4, _('Club')

    A field could be defined as

    class Card(models.Model):
        suit = models.IntegerField(choices=Suit.choices)

    Suit.HEART, Suit['HEART'] and Suit(3) work as expected, while
    Suit.HEART.display is a pretty, translatable string.
    """
    @property
    def display(self):
        return self._choices[self]

    @classmethod
    def validate(cls, value, message=_('Invalid choice')):
        try:
            cls(value)
        except ValueError:
            raise ValidationError(message)


class ChoiceIntEnum(int, ChoiceEnum):
    """Class for creating an enum int choices."""
    pass


class ChoiceStrEnum(str, ChoiceEnum):
    """Class for creating an enum string choices."""
    pass
