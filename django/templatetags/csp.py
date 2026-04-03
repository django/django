from django import template
from django.utils.csp import CSP
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def csp_nonce(context):
    nonce = context.get(CSP.CONTEXT_KEY)
    if nonce is None:
        return ""
    return format_html('nonce="{}"', nonce)


@register.simple_tag(takes_context=True)
def csp_media(context, media):
    nonce = context.get(CSP.CONTEXT_KEY)
    return media.render(attrs={"nonce": nonce} if nonce is not None else None)
