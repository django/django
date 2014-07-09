from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.utils.translation import ungettext_lazy


class ArrayMaxLengthValidator(MaxLengthValidator):
    message = ungettext_lazy(
        'List contains %(show_value)d item, it should contain no more than %(limit_value)d.',
        'List contains %(show_value)d items, it should contain no more than %(limit_value)d.',
        'limit_value')


class ArrayMinLengthValidator(MinLengthValidator):
    message = ungettext_lazy(
        'List contains %(show_value)d item, it should contain no fewer than %(limit_value)d.',
        'List contains %(show_value)d items, it should contain no fewer than %(limit_value)d.',
        'limit_value')
