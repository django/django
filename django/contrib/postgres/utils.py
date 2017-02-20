from django.core.exceptions import ValidationError
from django.utils.functional import SimpleLazyObject
from django.utils.text import format_lazy


def prefix_validation_error(error, prefix, code, params):
    """
    Prefix a validation error message while maintaining the existing
    validation data structure.
    """
    if error.error_list == [error]:
        error_params = error.params or {}
        return ValidationError(
            # We can't simply concatenate messages since they might require
            # their associated parameters to be expressed correctly which
            # is not something `format_lazy` does. For example, proxied
            # ngettext calls require a count parameter and are converted
            # to an empty string if they are missing it.
            message=format_lazy(
                '{}{}',
                SimpleLazyObject(lambda: prefix % params),
                SimpleLazyObject(lambda: error.message % error_params),
            ),
            code=code,
            params=dict(error_params, **params),
        )
    return ValidationError([
        prefix_validation_error(e, prefix, code, params) for e in error.error_list
    ])
