from django.core.exceptions import ValidationError
from django.forms import NullBooleanField


class StrictBooleanField(NullBooleanField):
    """
    forms.BooleanField coerces almost any truthy input to True. Delegate to
    NullBooleanField's stricter parsing while still rejecting None values.
    """

    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            # Not translated, as this is currently not user-facing.
            raise ValidationError("None is not a valid value.")
        return value
