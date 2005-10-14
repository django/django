from inspect import getargspec
from django.core import template
from django.core.template_loader import render_to_string, get_template
from django.utils.functional import curry

def gen_compile_func(params, defaults, name, node_class, parser, token):
    #look in tags for
    bits = token.contents.split()[1:]
    bmax = len(params)
    def_len = defaults and len(defaults) or 0
    bmin = bmax - def_len
    if( len(bits) < bmin or len(bits) > bmax  ):
        if bmin == bmax:
            message = "%s takes %s arguments" % (name, bmin)
        else:
            message = "%s takes between %s and %s arguments" % (name, bmin, bmax)
        raise template.TemplateSyntaxError(message)
    return node_class(bits)


def simple_tag(func):
    (params,_, _, defaults) = getargspec(func)
    class TNode(template.Node):
        def __init__(self, vars_to_resolve):
            #get the vars to resolve
            self.vars_to_resolve = vars_to_resolve    

        def render(self, context):
            resolved_vars = [template.resolve_variable(var, context) 
                              for var in self.vars_to_resolve]
            return func(*resolved_vars)
    compile_func = curry(gen_compile_func, params, defaults, func.__name__, TNode)
    compile_func.__doc__ = func.__doc__
    template.register_tag(func.__name__, compile_func)
    return func


def inclusion_tag(file_name, context_class=template.Context, takes_context=False):
    def dec(func):
        (params,_, _, defaults) = getargspec(func)
        if takes_context:
            if params[0] == 'context':
                params = params[1:]
            else:
                raise template.TemplateSyntaxError("Any tag function decorated with takes_context=True must have a first argument of 'context'" )
        class TNode(template.Node):
            def __init__(self, vars_to_resolve):
                self.vars_to_resolve = vars_to_resolve

            def render(self, context):
                resolved_vars = [template.resolve_variable(var, context)
                                 for var in self.vars_to_resolve]
                if takes_context:
                    args = [context] + resolved_vars
                else:
                    args = resolved_vars

                dict = func(*args)
                
                if not getattr(self, 'nodelist', False):
                    t = get_template(file_name)
                    self.nodelist = t.nodelist
                return self.nodelist.render(context_class(dict))

        compile_func = curry(gen_compile_func, params, defaults, func.__name__, TNode)
        compile_func.__doc__ = func.__doc__
        template.register_tag(func.__name__, compile_func)
        return func
    return dec

