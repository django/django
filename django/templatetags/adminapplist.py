from django.core import template

class AdminApplistNode(template.Node):
    def __init__(self, varname):
        self.varname = varname

    def render(self, context):
        from django.core import meta
        from django.utils.text import capfirst
        app_list = []
        for app in meta.get_installed_model_modules():
            app_label = app.__name__[app.__name__.rindex('.')+1:]
            model_list = [{'name': capfirst(m._meta.verbose_name_plural),
                            'admin_url': '%s/%s/' % (app_label, m._meta.module_name)} \
                            for m in app._MODELS if m._meta.admin]
            if model_list:
                app_list.append({
                    'name': app_label.title(),
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

template.register_tag('get_admin_app_list', get_admin_app_list)
