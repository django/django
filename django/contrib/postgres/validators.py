from django.core.validators import MaxLengthValidator
from django.utils.translation import ungettext_lazy


class ArrayMaxLengthValidator(MaxLengthValidator):
    message = ungettext_lazy(
        'Array contains %(show_value)d item, it should contain no more than %(limit_value)d.',
        'Array contains %(show_value)d items, it should contain no more than %(limit_value)d.',
        'limit_value')
