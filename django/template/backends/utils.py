from django.middleware.csrf import get_token
from django.utils.functional import lazy
from django.utils.safestring import SafeString


def csrf_input(request):
    token = get_token(request)
    return SafeString(f'<input type="hidden" name="csrfmiddlewaretoken" value="{token}">')


csrf_input_lazy = lazy(csrf_input, SafeString, str)
csrf_token_lazy = lazy(get_token, str)
