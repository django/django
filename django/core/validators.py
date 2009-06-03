from django.core.exceptions import ValidationError

# These values, if given to to_python(), will trigger the self.required check.
EMPTY_VALUES = (None, '')

def validate_integer(value, all_values={}, model_instance=None):
    try:
        int(value)
    except (ValueError, TypeError), e:
        raise ValidationError('')
