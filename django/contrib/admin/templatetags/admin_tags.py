from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def csp_nonce_attr(context):
    """
    Renders a nonce attribute for script tags.
    Works with Django's ContentSecurityPolicyMiddleware.

    Returns 'nonce="..."' if CSP middleware is active, empty string otherwise.
    """
    request = context.get("request")
    if not request:
        return ""

    # Get the LazyNonce from request (set by ContentSecurityPolicyMiddleware)
    nonce = getattr(request, "_csp_nonce", None)

    if nonce is None:
        return ""

    # Force evaluation of LazyNonce by converting to string
    # This is the intended usage - the nonce is designed to be evaluated here
    nonce_value = str(nonce)

    if nonce_value:
        return mark_safe(f'nonce="{nonce_value}"')

    return ""
