from django.middleware.csrf import get_token
from django.utils.functional import lazy
from django.utils.html import format_html
from django.utils.safestring import SafeText


def csrf_input(request):
    return format_html(
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />',
        get_token(request))


csrf_input_lazy = lazy(csrf_input, SafeText, str)
csrf_token_lazy = lazy(get_token, str)
