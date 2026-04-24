from django import template
from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist

register = template.Library()


class AdminLogNode(template.Node):
    def __init__(self, limit, varname, user):
        self.limit = limit
        self.varname = varname
        self.user = user

    def __repr__(self):
        return "<GetAdminLog Node>"

    def render(self, context):
        entries = context["log_entries"]
        if self.user is not None:
            user_id = self.user
            if not user_id.isdigit():
                user_id = context[self.user].pk
            entries = entries.filter(user__pk=user_id)
        context[self.varname] = entries[: int(self.limit)]
        return ""


@register.tag
def get_admin_log(parser, token):
    """
    Populate a template variable with the admin log for the given criteria.

    Usage::

        {% get_admin_log [limit] as [varname] for_user [user_id_or_varname] %}

    Examples::

        {% get_admin_log 10 as admin_log for_user 23 %}
        {% get_admin_log 10 as admin_log for_user user %}
        {% get_admin_log 10 as admin_log %}

    Note that ``user_id_or_varname`` can be a hard-coded integer (user ID)
    or the name of a template context variable containing the user object
    whose ID you want.
    """
    tokens = token.contents.split()
    if len(tokens) < 4:
        raise template.TemplateSyntaxError(
            "'get_admin_log' statements require two arguments"
        )
    if not tokens[1].isdigit():
        raise template.TemplateSyntaxError(
            "First argument to 'get_admin_log' must be an integer"
        )
    if tokens[2] != "as":
        raise template.TemplateSyntaxError(
            "Second argument to 'get_admin_log' must be 'as'"
        )
    if len(tokens) > 4:
        if tokens[4] != "for_user":
            raise template.TemplateSyntaxError(
                "Fourth argument to 'get_admin_log' must be 'for_user'"
            )
    return AdminLogNode(
        limit=tokens[1],
        varname=tokens[3],
        user=(tokens[5] if len(tokens) > 5 else None),
    )


def get_admin_site_from_request(request):
    namespace = request.resolver_match.namespace

    for site in admin.sites.all_sites:
        if site.name == namespace:
            return site

    return admin.site


@register.simple_tag(takes_context=True)
def can_change_log_entry(context, user, entry):
    """
    Determines if user has change permissions to determine
    whether to show <a> link or <span> in recent actions section.
    """

    # Some of the tests in admin_utils require to show link
    # when content type is not available so we have to return
    # True so link shows instead of span

    if entry.content_type is None:
        return True  # can't get object or determine perms - show link

    try:
        obj = entry.get_edited_object()
    except (AttributeError, ObjectDoesNotExist):
        # contenttype deleted or unavailable - show link
        return True

    if obj is None or not hasattr(obj, "_meta"):
        return True

    perm = f"{obj._meta.app_label}.change_{obj._meta.model_name}"

    request = context["request"]
    site = get_admin_site_from_request(request)
    model_admin = site._registry.get(obj.__class__)
    if model_admin:
        return model_admin.has_change_permission(request, obj)
    return user.has_perm(perm)
