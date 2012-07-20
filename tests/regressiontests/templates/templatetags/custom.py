import operator

from django import template
from django.template.defaultfilters import stringfilter
from django.template.loader import get_template
from django.utils import six

register = template.Library()

@register.filter
@stringfilter
def trim(value, num):
    return value[:num]

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

@register.simple_tag
def simple_two_params(one, two):
    """Expected simple_two_params __doc__"""
    return "simple_two_params - Expected result: %s, %s" % (one, two)
simple_two_params.anything = "Expected simple_two_params __dict__"

@register.simple_tag
def simple_one_default(one, two='hi'):
    """Expected simple_one_default __doc__"""
    return "simple_one_default - Expected result: %s, %s" % (one, two)
simple_one_default.anything = "Expected simple_one_default __dict__"

@register.simple_tag
def simple_unlimited_args(one, two='hi', *args):
    """Expected simple_unlimited_args __doc__"""
    return "simple_unlimited_args - Expected result: %s" % (', '.join([six.text_type(arg) for arg in [one, two] + list(args)]))
simple_unlimited_args.anything = "Expected simple_unlimited_args __dict__"

@register.simple_tag
def simple_only_unlimited_args(*args):
    """Expected simple_only_unlimited_args __doc__"""
    return "simple_only_unlimited_args - Expected result: %s" % ', '.join([six.text_type(arg) for arg in args])
simple_only_unlimited_args.anything = "Expected simple_only_unlimited_args __dict__"

@register.simple_tag
def simple_unlimited_args_kwargs(one, two='hi', *args, **kwargs):
    """Expected simple_unlimited_args_kwargs __doc__"""
    # Sort the dictionary by key to guarantee the order for testing.
    sorted_kwarg = sorted(six.iteritems(kwargs), key=operator.itemgetter(0))
    return "simple_unlimited_args_kwargs - Expected result: %s / %s" % (
        ', '.join([six.text_type(arg) for arg in [one, two] + list(args)]),
        ', '.join(['%s=%s' % (k, v) for (k, v) in sorted_kwarg])
        )
simple_unlimited_args_kwargs.anything = "Expected simple_unlimited_args_kwargs __dict__"

@register.simple_tag(takes_context=True)
def simple_tag_without_context_parameter(arg):
    """Expected simple_tag_without_context_parameter __doc__"""
    return "Expected result"
simple_tag_without_context_parameter.anything = "Expected simple_tag_without_context_parameter __dict__"

@register.simple_tag(takes_context=True)
def current_app(context):
    return "%s" % context.current_app

@register.simple_tag(takes_context=True)
def use_l10n(context):
    return "%s" % context.use_l10n

@register.simple_tag(name='minustwo')
def minustwo_overridden_name(value):
    return value - 2

register.simple_tag(lambda x: x - 1, name='minusone')

@register.inclusion_tag('inclusion.html')
def inclusion_no_params():
    """Expected inclusion_no_params __doc__"""
    return {"result" : "inclusion_no_params - Expected result"}
inclusion_no_params.anything = "Expected inclusion_no_params __dict__"

@register.inclusion_tag(get_template('inclusion.html'))
def inclusion_no_params_from_template():
    """Expected inclusion_no_params_from_template __doc__"""
    return {"result" : "inclusion_no_params_from_template - Expected result"}
inclusion_no_params_from_template.anything = "Expected inclusion_no_params_from_template __dict__"

@register.inclusion_tag('inclusion.html')
def inclusion_one_param(arg):
    """Expected inclusion_one_param __doc__"""
    return {"result" : "inclusion_one_param - Expected result: %s" % arg}
inclusion_one_param.anything = "Expected inclusion_one_param __dict__"

@register.inclusion_tag(get_template('inclusion.html'))
def inclusion_one_param_from_template(arg):
    """Expected inclusion_one_param_from_template __doc__"""
    return {"result" : "inclusion_one_param_from_template - Expected result: %s" % arg}
inclusion_one_param_from_template.anything = "Expected inclusion_one_param_from_template __dict__"

@register.inclusion_tag('inclusion.html', takes_context=False)
def inclusion_explicit_no_context(arg):
    """Expected inclusion_explicit_no_context __doc__"""
    return {"result" : "inclusion_explicit_no_context - Expected result: %s" % arg}
inclusion_explicit_no_context.anything = "Expected inclusion_explicit_no_context __dict__"

@register.inclusion_tag(get_template('inclusion.html'), takes_context=False)
def inclusion_explicit_no_context_from_template(arg):
    """Expected inclusion_explicit_no_context_from_template __doc__"""
    return {"result" : "inclusion_explicit_no_context_from_template - Expected result: %s" % arg}
inclusion_explicit_no_context_from_template.anything = "Expected inclusion_explicit_no_context_from_template __dict__"

@register.inclusion_tag('inclusion.html', takes_context=True)
def inclusion_no_params_with_context(context):
    """Expected inclusion_no_params_with_context __doc__"""
    return {"result" : "inclusion_no_params_with_context - Expected result (context value: %s)" % context['value']}
inclusion_no_params_with_context.anything = "Expected inclusion_no_params_with_context __dict__"

@register.inclusion_tag(get_template('inclusion.html'), takes_context=True)
def inclusion_no_params_with_context_from_template(context):
    """Expected inclusion_no_params_with_context_from_template __doc__"""
    return {"result" : "inclusion_no_params_with_context_from_template - Expected result (context value: %s)" % context['value']}
inclusion_no_params_with_context_from_template.anything = "Expected inclusion_no_params_with_context_from_template __dict__"

@register.inclusion_tag('inclusion.html', takes_context=True)
def inclusion_params_and_context(context, arg):
    """Expected inclusion_params_and_context __doc__"""
    return {"result" : "inclusion_params_and_context - Expected result (context value: %s): %s" % (context['value'], arg)}
inclusion_params_and_context.anything = "Expected inclusion_params_and_context __dict__"

@register.inclusion_tag(get_template('inclusion.html'), takes_context=True)
def inclusion_params_and_context_from_template(context, arg):
    """Expected inclusion_params_and_context_from_template __doc__"""
    return {"result" : "inclusion_params_and_context_from_template - Expected result (context value: %s): %s" % (context['value'], arg)}
inclusion_params_and_context_from_template.anything = "Expected inclusion_params_and_context_from_template __dict__"

@register.inclusion_tag('inclusion.html')
def inclusion_two_params(one, two):
    """Expected inclusion_two_params __doc__"""
    return {"result": "inclusion_two_params - Expected result: %s, %s" % (one, two)}
inclusion_two_params.anything = "Expected inclusion_two_params __dict__"

@register.inclusion_tag(get_template('inclusion.html'))
def inclusion_two_params_from_template(one, two):
    """Expected inclusion_two_params_from_template __doc__"""
    return {"result": "inclusion_two_params_from_template - Expected result: %s, %s" % (one, two)}
inclusion_two_params_from_template.anything = "Expected inclusion_two_params_from_template __dict__"

@register.inclusion_tag('inclusion.html')
def inclusion_one_default(one, two='hi'):
    """Expected inclusion_one_default __doc__"""
    return {"result": "inclusion_one_default - Expected result: %s, %s" % (one, two)}
inclusion_one_default.anything = "Expected inclusion_one_default __dict__"

@register.inclusion_tag(get_template('inclusion.html'))
def inclusion_one_default_from_template(one, two='hi'):
    """Expected inclusion_one_default_from_template __doc__"""
    return {"result": "inclusion_one_default_from_template - Expected result: %s, %s" % (one, two)}
inclusion_one_default_from_template.anything = "Expected inclusion_one_default_from_template __dict__"

@register.inclusion_tag('inclusion.html')
def inclusion_unlimited_args(one, two='hi', *args):
    """Expected inclusion_unlimited_args __doc__"""
    return {"result": "inclusion_unlimited_args - Expected result: %s" % (', '.join([six.text_type(arg) for arg in [one, two] + list(args)]))}
inclusion_unlimited_args.anything = "Expected inclusion_unlimited_args __dict__"

@register.inclusion_tag(get_template('inclusion.html'))
def inclusion_unlimited_args_from_template(one, two='hi', *args):
    """Expected inclusion_unlimited_args_from_template __doc__"""
    return {"result": "inclusion_unlimited_args_from_template - Expected result: %s" % (', '.join([six.text_type(arg) for arg in [one, two] + list(args)]))}
inclusion_unlimited_args_from_template.anything = "Expected inclusion_unlimited_args_from_template __dict__"

@register.inclusion_tag('inclusion.html')
def inclusion_only_unlimited_args(*args):
    """Expected inclusion_only_unlimited_args __doc__"""
    return {"result": "inclusion_only_unlimited_args - Expected result: %s" % (', '.join([six.text_type(arg) for arg in args]))}
inclusion_only_unlimited_args.anything = "Expected inclusion_only_unlimited_args __dict__"

@register.inclusion_tag(get_template('inclusion.html'))
def inclusion_only_unlimited_args_from_template(*args):
    """Expected inclusion_only_unlimited_args_from_template __doc__"""
    return {"result": "inclusion_only_unlimited_args_from_template - Expected result: %s" % (', '.join([six.text_type(arg) for arg in args]))}
inclusion_only_unlimited_args_from_template.anything = "Expected inclusion_only_unlimited_args_from_template __dict__"

@register.inclusion_tag('test_incl_tag_current_app.html', takes_context=True)
def inclusion_tag_current_app(context):
    """Expected inclusion_tag_current_app __doc__"""
    return {}
inclusion_tag_current_app.anything = "Expected inclusion_tag_current_app __dict__"

@register.inclusion_tag('test_incl_tag_use_l10n.html', takes_context=True)
def inclusion_tag_use_l10n(context):
    """Expected inclusion_tag_use_l10n __doc__"""
    return {}
inclusion_tag_use_l10n.anything = "Expected inclusion_tag_use_l10n __dict__"

@register.inclusion_tag('inclusion.html')
def inclusion_unlimited_args_kwargs(one, two='hi', *args, **kwargs):
    """Expected inclusion_unlimited_args_kwargs __doc__"""
    # Sort the dictionary by key to guarantee the order for testing.
    sorted_kwarg = sorted(six.iteritems(kwargs), key=operator.itemgetter(0))
    return {"result": "inclusion_unlimited_args_kwargs - Expected result: %s / %s" % (
        ', '.join([six.text_type(arg) for arg in [one, two] + list(args)]),
        ', '.join(['%s=%s' % (k, v) for (k, v) in sorted_kwarg])
        )}
inclusion_unlimited_args_kwargs.anything = "Expected inclusion_unlimited_args_kwargs __dict__"

@register.inclusion_tag('inclusion.html', takes_context=True)
def inclusion_tag_without_context_parameter(arg):
    """Expected inclusion_tag_without_context_parameter __doc__"""
    return {}
inclusion_tag_without_context_parameter.anything = "Expected inclusion_tag_without_context_parameter __dict__"

@register.assignment_tag
def assignment_no_params():
    """Expected assignment_no_params __doc__"""
    return "assignment_no_params - Expected result"
assignment_no_params.anything = "Expected assignment_no_params __dict__"

@register.assignment_tag
def assignment_one_param(arg):
    """Expected assignment_one_param __doc__"""
    return "assignment_one_param - Expected result: %s" % arg
assignment_one_param.anything = "Expected assignment_one_param __dict__"

@register.assignment_tag(takes_context=False)
def assignment_explicit_no_context(arg):
    """Expected assignment_explicit_no_context __doc__"""
    return "assignment_explicit_no_context - Expected result: %s" % arg
assignment_explicit_no_context.anything = "Expected assignment_explicit_no_context __dict__"

@register.assignment_tag(takes_context=True)
def assignment_no_params_with_context(context):
    """Expected assignment_no_params_with_context __doc__"""
    return "assignment_no_params_with_context - Expected result (context value: %s)" % context['value']
assignment_no_params_with_context.anything = "Expected assignment_no_params_with_context __dict__"

@register.assignment_tag(takes_context=True)
def assignment_params_and_context(context, arg):
    """Expected assignment_params_and_context __doc__"""
    return "assignment_params_and_context - Expected result (context value: %s): %s" % (context['value'], arg)
assignment_params_and_context.anything = "Expected assignment_params_and_context __dict__"

@register.assignment_tag
def assignment_two_params(one, two):
    """Expected assignment_two_params __doc__"""
    return "assignment_two_params - Expected result: %s, %s" % (one, two)
assignment_two_params.anything = "Expected assignment_two_params __dict__"

@register.assignment_tag
def assignment_one_default(one, two='hi'):
    """Expected assignment_one_default __doc__"""
    return "assignment_one_default - Expected result: %s, %s" % (one, two)
assignment_one_default.anything = "Expected assignment_one_default __dict__"

@register.assignment_tag
def assignment_unlimited_args(one, two='hi', *args):
    """Expected assignment_unlimited_args __doc__"""
    return "assignment_unlimited_args - Expected result: %s" % (', '.join([six.text_type(arg) for arg in [one, two] + list(args)]))
assignment_unlimited_args.anything = "Expected assignment_unlimited_args __dict__"

@register.assignment_tag
def assignment_only_unlimited_args(*args):
    """Expected assignment_only_unlimited_args __doc__"""
    return "assignment_only_unlimited_args - Expected result: %s" % ', '.join([six.text_type(arg) for arg in args])
assignment_only_unlimited_args.anything = "Expected assignment_only_unlimited_args __dict__"

@register.assignment_tag
def assignment_unlimited_args_kwargs(one, two='hi', *args, **kwargs):
    """Expected assignment_unlimited_args_kwargs __doc__"""
    # Sort the dictionary by key to guarantee the order for testing.
    sorted_kwarg = sorted(six.iteritems(kwargs), key=operator.itemgetter(0))
    return "assignment_unlimited_args_kwargs - Expected result: %s / %s" % (
        ', '.join([six.text_type(arg) for arg in [one, two] + list(args)]),
        ', '.join(['%s=%s' % (k, v) for (k, v) in sorted_kwarg])
        )
assignment_unlimited_args_kwargs.anything = "Expected assignment_unlimited_args_kwargs __dict__"

@register.assignment_tag(takes_context=True)
def assignment_tag_without_context_parameter(arg):
    """Expected assignment_tag_without_context_parameter __doc__"""
    return "Expected result"
assignment_tag_without_context_parameter.anything = "Expected assignment_tag_without_context_parameter __dict__"
