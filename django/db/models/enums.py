import enum
import warnings

from django.utils.deprecation import RemovedInDjango60Warning
from django.utils.functional import Promise
from django.utils.version import PY311, PY312

if PY311:
    from enum import EnumType, IntEnum, StrEnum
    from enum import property as enum_property
else:
    from enum import EnumMeta as EnumType
    from types import DynamicClassAttribute as enum_property

    class ReprEnum(enum.Enum):
        def __str__(self):
            return str(self.value)

    class IntEnum(int, ReprEnum):
        pass

    class StrEnum(str, ReprEnum):
        pass


__all__ = ["Choices", "IntegerChoices", "TextChoices"]


class ChoicesType(EnumType):
    """A metaclass for creating a enum choices."""

    def __new__(metacls, classname, bases, classdict, **kwds):
        labels = []
        for key in classdict._member_names:
            value = classdict[key]
            if (
                isinstance(value, (list, tuple))
                and len(value) > 1
                and isinstance(value[-1], (Promise, str))
            ):
                *value, label = value
                value = tuple(value)
            else:
                label = key.replace("_", " ").title()
            labels.append(label)
            # Use dict.__setitem__() to suppress defenses against double
            # assignment in enum's classdict.
            dict.__setitem__(classdict, key, value)
        cls = super().__new__(metacls, classname, bases, classdict, **kwds)
        for member, label in zip(cls.__members__.values(), labels):
            member._label_ = label
        return enum.unique(cls)

    if not PY312:

        def __contains__(cls, member):
            if not isinstance(member, enum.Enum):
                # Allow non-enums to match against member values.
                return any(x.value == member for x in cls)
            return super().__contains__(member)

    @property
    def names(cls):
        empty = ["__empty__"] if hasattr(cls, "__empty__") else []
        return empty + [member.name for member in cls]

    @property
    def choices(cls):
        empty = [(None, cls.__empty__)] if hasattr(cls, "__empty__") else []
        return empty + [(member.value, member.label) for member in cls]

    @property
    def labels(cls):
        return [label for _, label in cls.choices]

    @property
    def values(cls):
        return [value for value, _ in cls.choices]


class Choices(enum.Enum, metaclass=ChoicesType):
    """Class for creating enumerated choices."""

    if PY311:
        do_not_call_in_templates = enum.nonmember(True)
    else:

        @property
        def do_not_call_in_templates(self):
            return True

    @enum_property
    def label(self):
        return self._label_

    # A similar format was proposed for Python 3.10.
    def __repr__(self):
        return f"{self.__class__.__qualname__}.{self._name_}"


class IntegerChoices(Choices, IntEnum):
    """Class for creating enumerated integer choices."""

    pass


class TextChoices(Choices, StrEnum):
    """Class for creating enumerated string choices."""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name


def __getattr__(name):
    if name == "ChoicesMeta":
        warnings.warn(
            "ChoicesMeta is deprecated in favor of ChoicesType.",
            RemovedInDjango60Warning,
            stacklevel=2,
        )
        return ChoicesType
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
