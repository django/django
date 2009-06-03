from django.core.exceptions import ValidationError

def validate_integer(value, all_values={}, model_instance=None):
    try:
        int(value)
    except (ValueError, TypeError), e:
        raise ValidationError('')
