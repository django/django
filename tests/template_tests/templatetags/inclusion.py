import operator

from django.template import Engine, Library
from django.utils import six

engine = Engine(app_dirs=True)
register = Library()


@register.inclusion_tag('inclusion.html')
def inclusion_no_params():
    """Expected inclusion_no_params __doc__"""
    return {"result": "inclusion_no_params - Expected result"}
inclusion_no_params.anything = "Expected inclusion_no_params __dict__"


@register.inclusion_tag(engine.get_template('inclusion.html'))
def inclusion_no_params_from_template():
    """Expected inclusion_no_params_from_template __doc__"""
    return {"result": "inclusion_no_params_from_template - Expected result"}
inclusion_no_params_from_template.anything = "Expected inclusion_no_params_from_template __dict__"


@register.inclusion_tag('inclusion.html')
def inclusion_one_param(arg):
    """Expected inclusion_one_param __doc__"""
    return {"result": "inclusion_one_param - Expected result: %s" % arg}
inclusion_one_param.anything = "Expected inclusion_one_param __dict__"


@register.inclusion_tag(engine.get_template('inclusion.html'))
def inclusion_one_param_from_template(arg):
    """Expected inclusion_one_param_from_template __doc__"""
    return {"result": "inclusion_one_param_from_template - Expected result: %s" % arg}
inclusion_one_param_from_template.anything = "Expected inclusion_one_param_from_template __dict__"


@register.inclusion_tag('inclusion.html', takes_context=False)
def inclusion_explicit_no_context(arg):
    """Expected inclusion_explicit_no_context __doc__"""
    return {"result": "inclusion_explicit_no_context - Expected result: %s" % arg}
inclusion_explicit_no_context.anything = "Expected inclusion_explicit_no_context __dict__"


@register.inclusion_tag(engine.get_template('inclusion.html'), takes_context=False)
def inclusion_explicit_no_context_from_template(arg):
    """Expected inclusion_explicit_no_context_from_template __doc__"""
    return {"result": "inclusion_explicit_no_context_from_template - Expected result: %s" % arg}
inclusion_explicit_no_context_from_template.anything = "Expected inclusion_explicit_no_context_from_template __dict__"


@register.inclusion_tag('inclusion.html', takes_context=True)
def inclusion_no_params_with_context(context):
    """Expected inclusion_no_params_with_context __doc__"""
    return {"result": "inclusion_no_params_with_context - Expected result (context value: %s)" % context['value']}
inclusion_no_params_with_context.anything = "Expected inclusion_no_params_with_context __dict__"


@register.inclusion_tag(engine.get_template('inclusion.html'), takes_context=True)
def inclusion_no_params_with_context_from_template(context):
    """Expected inclusion_no_params_with_context_from_template __doc__"""
    return {
        "result": (
            "inclusion_no_params_with_context_from_template - Expected result (context value: %s)" % context['value']
        )
    }
inclusion_no_params_with_context_from_template.anything = (
    "Expected inclusion_no_params_with_context_from_template __dict__"
)


@register.inclusion_tag('inclusion.html', takes_context=True)
def inclusion_params_and_context(context, arg):
    """Expected inclusion_params_and_context __doc__"""
    return {
        "result": "inclusion_params_and_context - Expected result (context value: %s): %s" % (context['value'], arg)
    }
inclusion_params_and_context.anything = "Expected inclusion_params_and_context __dict__"


@register.inclusion_tag(engine.get_template('inclusion.html'), takes_context=True)
def inclusion_params_and_context_from_template(context, arg):
    """Expected inclusion_params_and_context_from_template __doc__"""
    return {
        "result": (
            "inclusion_params_and_context_from_template - Expected result "
            "(context value: %s): %s" % (context['value'], arg)
        )
    }
inclusion_params_and_context_from_template.anything = "Expected inclusion_params_and_context_from_template __dict__"


@register.inclusion_tag('inclusion.html')
def inclusion_two_params(one, two):
    """Expected inclusion_two_params __doc__"""
    return {"result": "inclusion_two_params - Expected result: %s, %s" % (one, two)}
inclusion_two_params.anything = "Expected inclusion_two_params __dict__"


@register.inclusion_tag(engine.get_template('inclusion.html'))
def inclusion_two_params_from_template(one, two):
    """Expected inclusion_two_params_from_template __doc__"""
    return {"result": "inclusion_two_params_from_template - Expected result: %s, %s" % (one, two)}
inclusion_two_params_from_template.anything = "Expected inclusion_two_params_from_template __dict__"


@register.inclusion_tag('inclusion.html')
def inclusion_one_default(one, two='hi'):
    """Expected inclusion_one_default __doc__"""
    return {"result": "inclusion_one_default - Expected result: %s, %s" % (one, two)}
inclusion_one_default.anything = "Expected inclusion_one_default __dict__"


@register.inclusion_tag(engine.get_template('inclusion.html'))
def inclusion_one_default_from_template(one, two='hi'):
    """Expected inclusion_one_default_from_template __doc__"""
    return {"result": "inclusion_one_default_from_template - Expected result: %s, %s" % (one, two)}
inclusion_one_default_from_template.anything = "Expected inclusion_one_default_from_template __dict__"


@register.inclusion_tag('inclusion.html')
def inclusion_unlimited_args(one, two='hi', *args):
    """Expected inclusion_unlimited_args __doc__"""
    return {
        "result": (
            "inclusion_unlimited_args - Expected result: %s" % (
                ', '.join(six.text_type(arg) for arg in [one, two] + list(args))
            )
        )
    }
inclusion_unlimited_args.anything = "Expected inclusion_unlimited_args __dict__"


@register.inclusion_tag(engine.get_template('inclusion.html'))
def inclusion_unlimited_args_from_template(one, two='hi', *args):
    """Expected inclusion_unlimited_args_from_template __doc__"""
    return {
        "result": (
            "inclusion_unlimited_args_from_template - Expected result: %s" % (
                ', '.join(six.text_type(arg) for arg in [one, two] + list(args))
            )
        )
    }
inclusion_unlimited_args_from_template.anything = "Expected inclusion_unlimited_args_from_template __dict__"


@register.inclusion_tag('inclusion.html')
def inclusion_only_unlimited_args(*args):
    """Expected inclusion_only_unlimited_args __doc__"""
    return {
        "result": "inclusion_only_unlimited_args - Expected result: %s" % (
            ', '.join(six.text_type(arg) for arg in args)
        )
    }
inclusion_only_unlimited_args.anything = "Expected inclusion_only_unlimited_args __dict__"


@register.inclusion_tag(engine.get_template('inclusion.html'))
def inclusion_only_unlimited_args_from_template(*args):
    """Expected inclusion_only_unlimited_args_from_template __doc__"""
    return {
        "result": "inclusion_only_unlimited_args_from_template - Expected result: %s" % (
            ', '.join(six.text_type(arg) for arg in args)
        )
    }
inclusion_only_unlimited_args_from_template.anything = "Expected inclusion_only_unlimited_args_from_template __dict__"


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
        ', '.join(six.text_type(arg) for arg in [one, two] + list(args)),
        ', '.join('%s=%s' % (k, v) for (k, v) in sorted_kwarg)
    )}
inclusion_unlimited_args_kwargs.anything = "Expected inclusion_unlimited_args_kwargs __dict__"


@register.inclusion_tag('inclusion.html', takes_context=True)
def inclusion_tag_without_context_parameter(arg):
    """Expected inclusion_tag_without_context_parameter __doc__"""
    return {}
inclusion_tag_without_context_parameter.anything = "Expected inclusion_tag_without_context_parameter __dict__"


@register.inclusion_tag('inclusion_extends1.html')
def inclusion_extends1():
    return {}


@register.inclusion_tag('inclusion_extends2.html')
def inclusion_extends2():
    return {}
