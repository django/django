from collections.abc import Callable, Iterable, Iterator, Mapping
from itertools import islice, tee, zip_longest

from django.utils.functional import Promise

__all__ = [
    "BaseChoiceIterator",
    "BlankChoiceIterator",
    "CallableChoiceIterator",
    "flatten_choices",
    "normalize_choices",
]


class BaseChoiceIterator:
    """Base class for lazy iterators for choices."""

    def __eq__(self, other):
        if isinstance(other, Iterable):
            return all(a == b for a, b in zip_longest(self, other, fillvalue=object()))
        return super().__eq__(other)

    def __getitem__(self, index):
        if isinstance(index, slice) or index < 0:
            # Suboptimally consume whole iterator to handle slices and negative
            # indexes.
            return list(self)[index]
        try:
            return next(islice(self, index, index + 1))
        except StopIteration:
            raise IndexError("index out of range") from None

    def __iter__(self):
        raise NotImplementedError(
            "BaseChoiceIterator subclasses must implement __iter__()."
        )


class BlankChoiceIterator(BaseChoiceIterator):
    """Iterator to lazily inject a blank choice."""

    def __init__(self, choices, blank_choice):
        self.choices = choices
        self.blank_choice = blank_choice

    def __iter__(self):
        choices, other = tee(self.choices)
        if not any(value in ("", None) for value, _ in flatten_choices(other)):
            yield from self.blank_choice
        yield from choices


class CallableChoiceIterator(BaseChoiceIterator):
    """Iterator to lazily normalize choices generated by a callable."""

    def __init__(self, func):
        self.func = func

    def __iter__(self):
        yield from normalize_choices(self.func())


def flatten_choices(choices):
    """Flatten choices by removing nested values."""
    for value_or_group, label_or_nested in choices or ():
        if isinstance(label_or_nested, (list, tuple)):
            yield from label_or_nested
        else:
            yield value_or_group, label_or_nested


def normalize_choices(value, *, depth=0):
    """Normalize choices values consistently for fields and widgets."""
    # Avoid circular import when importing django.forms.
    from django.db.models.enums import ChoicesType

    match value:
        case BaseChoiceIterator() | Promise() | bytes() | str():
            # Avoid prematurely normalizing iterators that should be lazy.
            # Because string-like types are iterable, return early to avoid
            # iterating over them in the guard for the Iterable case below.
            return value
        case ChoicesType():
            # Choices enumeration helpers already output in canonical form.
            return value.choices
        case Mapping() if depth < 2:
            value = value.items()
        case Iterator() if depth < 2:
            # Although Iterator would be handled by the Iterable case below,
            # the iterator would be consumed prematurely while checking that
            # its elements are not string-like in the guard, so we handle it
            # separately.
            pass
        case Iterable() if depth < 2 and not any(
            isinstance(x, (Promise, bytes, str)) for x in value
        ):
            # String-like types are iterable, so the guard above ensures that
            # they're handled by the default case below.
            pass
        case Callable() if depth == 0:
            # If at the top level, wrap callables to be evaluated lazily.
            return CallableChoiceIterator(value)
        case Callable() if depth < 2:
            value = value()
        case _:
            return value

    try:
        # Recursive call to convert any nested values to a list of 2-tuples.
        return [(k, normalize_choices(v, depth=depth + 1)) for k, v in value]
    except (TypeError, ValueError):
        # Return original value for the system check to raise if it has items
        # that are not iterable or not 2-tuples:
        # - TypeError: cannot unpack non-iterable <type> object
        # - ValueError: <not enough / too many> values to unpack
        return value
