from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit

from django import template
from django.contrib.admin.utils import quote
from django.urls import Resolver404, get_script_prefix, resolve
from django.utils.http import urlencode

from .base import InclusionAdminNode

register = template.Library()


@register.filter
def admin_urlname(value, arg):
    return "admin:%s_%s_%s" % (value.app_label, value.model_name, arg)


@register.filter
def admin_urlquote(value):
    return quote(value)


@register.simple_tag(takes_context=True)
def add_preserved_filters(context, url, popup=False, to_field=None):
    opts = context.get("opts")
    preserved_filters = context.get("preserved_filters")
    preserved_qsl = context.get("preserved_qsl")

    parsed_url = list(urlsplit(url))
    parsed_qs = dict(parse_qsl(parsed_url[3]))
    merged_qs = {}

    if preserved_qsl:
        merged_qs.update(preserved_qsl)

    if opts and preserved_filters:
        preserved_filters = dict(parse_qsl(preserved_filters))

        match_url = "/%s" % unquote(url).partition(get_script_prefix())[2]
        try:
            match = resolve(match_url)
        except Resolver404:
            pass
        else:
            current_url = "%s:%s" % (match.app_name, match.url_name)
            changelist_url = "admin:%s_%s_changelist" % (
                opts.app_label,
                opts.model_name,
            )
            if (
                changelist_url == current_url
                and "_changelist_filters" in preserved_filters
            ):
                preserved_filters = dict(
                    parse_qsl(preserved_filters["_changelist_filters"])
                )

        merged_qs.update(preserved_filters)

    if popup:
        from django.contrib.admin.options import IS_POPUP_VAR

        merged_qs[IS_POPUP_VAR] = 1
    if to_field:
        from django.contrib.admin.options import TO_FIELD_VAR

        merged_qs[TO_FIELD_VAR] = to_field

    merged_qs.update(parsed_qs)

    parsed_url[3] = urlencode(merged_qs)
    return urlunsplit(parsed_url)


def admin_actions(context):
    """
    Track the number of times the action field has been rendered on the page,
    so we know which value to use.
    """
    context["action_index"] = context.get("action_index", -1) + 1
    return context


@register.tag(name="admin_actions")
def admin_actions_tag(parser, token):
    return InclusionAdminNode(
        parser, token, func=admin_actions, template_name="actions.html"
    )
