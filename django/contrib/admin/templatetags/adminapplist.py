from django import template
from django.db.models import get_models

register = template.Library()

class AdminApplistNode(template.Node):
    def __init__(self, varname):
        self.varname = varname

    def render(self, context):
        from django.db import models
        from django.utils.text import capfirst
        app_list = []
        user = context['user']

        for app in models.get_apps():
            # Determine the app_label.
            app_models = get_models(app)
            if not app_models:
                continue
            app_label = app_models[0]._meta.app_label

            has_module_perms = user.has_module_perms(app_label)

            if has_module_perms:
                model_list = []
                for m in app_models:
                    if m._meta.admin:
                        perms = {
                            'add': user.has_perm("%s.%s" % (app_label, m._meta.get_add_permission())),
                            'change': user.has_perm("%s.%s" % (app_label, m._meta.get_change_permission())),
                            'delete': user.has_perm("%s.%s" % (app_label, m._meta.get_delete_permission())),
                        }

                        # Check whether user has any perm for this module.
                        # If so, add the module to the model_list.
                        if True in perms.values():
                            model_list.append({
                                'name': capfirst(m._meta.verbose_name_plural),
                                'admin_url': '%s/%s/' % (app_label, m.__name__.lower()),
                                'perms': perms,
                            })

                if model_list:
                    app_list.append({
                        'name': app_label.title(),
                        'has_module_perms': has_module_perms,
                        'models': model_list,
                    })
        context[self.varname] = app_list
        return ''

def get_admin_app_list(parser, token):
    """
    {% get_admin_app_list as app_list %}
    """
    tokens = token.contents.split()
    if len(tokens) < 3:
        raise template.TemplateSyntaxError, "'%s' tag requires two arguments" % tokens[0]
    if tokens[1] != 'as':
        raise template.TemplateSyntaxError, "First argument to '%s' tag must be 'as'" % tokens[0]
    return AdminApplistNode(tokens[2])

register.tag('get_admin_app_list', get_admin_app_list)
