from django import template

register = template.Library()

class AdminApplistNode(template.Node):
    def __init__(self, varname):
        self.varname = varname

    def render(self, context):
        from django.db import models
        from django.utils.text import capfirst
        app_list = []
        user = context['user']

        for app in models.get_installed_model_modules():
            app_label = app.__name__.split('.')[:-1][-1]
            has_module_perms = user.has_module_perms(app_label)
            if has_module_perms:
                model_list = []
                #HACK
                app_url = "/".join( [comp for comp in app.__name__.split('.') if comp != 'models' ])
                for m in app._MODELS:
                    if m._meta.admin:
                        module_name = m._meta.module_name
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
                                'admin_url':  '%s/%s/' % (app_url, m.__name__.lower()),
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
