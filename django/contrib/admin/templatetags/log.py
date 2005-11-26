from django.models.admin import log
from django.core import template

register = template.Library()

class AdminLogNode(template.Node):
    def __init__(self, limit, varname, user):
        self.limit, self.varname, self.user = limit, varname, user

    def __repr__(self):
        return "<GetAdminLog Node>"

    def render(self, context):
        if self.user is not None and not self.user.isdigit():
            self.user = context[self.user].id
        context[self.varname] = log.get_list(user__id__exact=self.user, limit=self.limit, select_related=True)
        return ''

class DoGetAdminLog:
    """
    Populates a template variable with the admin log for the given criteria.

    Usage::

        {% get_admin_log [limit] as [varname] for_user [context_var_containing_user_obj] %}

    Examples::

        {% get_admin_log 10 as admin_log for_user 23 %}
        {% get_admin_log 10 as admin_log for_user user %}
        {% get_admin_log 10 as admin_log %}

    Note that ``context_var_containing_user_obj`` can be a hard-coded integer
    (user ID) or the name of a template context variable containing the user
    object whose ID you want.
    """
    def __init__(self, tag_name):
        self.tag_name = tag_name

    def __call__(self, parser, token):
        tokens = token.contents.split()
        if len(tokens) < 4:
            raise template.TemplateSyntaxError, "'%s' statements require two arguments" % self.tag_name
        if not tokens[1].isdigit():
            raise template.TemplateSyntaxError, "First argument in '%s' must be an integer" % self.tag_name
        if tokens[2] != 'as':
            raise template.TemplateSyntaxError, "Second argument in '%s' must be 'as'" % self.tag_name
        if len(tokens) > 4:
            if tokens[4] != 'for_user':
                raise template.TemplateSyntaxError, "Fourth argument in '%s' must be 'for_user'" % self.tag_name
        return AdminLogNode(limit=tokens[1], varname=tokens[3], user=(len(tokens) > 5 and tokens[5] or None))

register.tag('get_admin_log', DoGetAdminLog('get_admin_log'))
