from django.core.exceptions import ValidationError
from django.forms import NullBooleanField


class StrictBooleanField(NullBooleanField):
    """
    forms.BooleanField coerces almost any truthy input to True. Delegate to
    NullBooleanField's stricter parsing while still rejecting None values.
    """

    def to_python(self, value):
        # The admin changelist search allows case-insensitivity.
        try:
            value = value.lower()
        except AttributeError:
            pass
        value = super().to_python(value)
        if value is None:
            # Not translated, as this is currently not user-facing.
            raise ValidationError("Invalid value.")
        return value


class StrictNullBooleanField(NullBooleanField):
    """
    forms.NullBooleanField doesn't distinguish explicit None values, so check
    for that before delegating.
    """

    def to_python(self, value):
        # The admin changelist search allows case-insensitivity.
        try:
            value = value.lower()
        except AttributeError:
            pass
        if value in (None, "none"):
            return None
        value = super().to_python(value)
        if value is None:
            # Not translated, as this is currently not user-facing.
            raise ValidationError("Invalid value.")
        return value
