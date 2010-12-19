from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

def trim(value, num):
    return value[:num]
trim = stringfilter(trim)

register.filter(trim)

@register.simple_tag
def no_params():
    """Expected no_params __doc__"""
    return "no_params - Expected result"
no_params.anything = "Expected no_params __dict__"

@register.simple_tag
def one_param(arg):
    """Expected one_param __doc__"""
    return "one_param - Expected result: %s" % arg
one_param.anything = "Expected one_param __dict__"

@register.simple_tag(takes_context=False)
def explicit_no_context(arg):
    """Expected explicit_no_context __doc__"""
    return "explicit_no_context - Expected result: %s" % arg
explicit_no_context.anything = "Expected explicit_no_context __dict__"

@register.simple_tag(takes_context=True)
def no_params_with_context(context):
    """Expected no_params_with_context __doc__"""
    return "no_params_with_context - Expected result (context value: %s)" % context['value']
no_params_with_context.anything = "Expected no_params_with_context __dict__"

@register.simple_tag(takes_context=True)
def params_and_context(context, arg):
    """Expected params_and_context __doc__"""
    return "params_and_context - Expected result (context value: %s): %s" % (context['value'], arg)
params_and_context.anything = "Expected params_and_context __dict__"

