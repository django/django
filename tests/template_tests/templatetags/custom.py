import operator

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
@stringfilter
def trim(value, num):
    return value[:num]


@register.filter
@mark_safe
def make_data_div(value):
    """A filter that uses a decorator (@mark_safe)."""
    return '<div data-name="%s"></div>' % value


@register.filter
def noop(value, param=None):
    """A noop filter that always return its first argument and does nothing with
    its second (optional) one.
    Useful for testing out whitespace in filter arguments (see #19882)."""
    return value


@register.simple_tag(takes_context=True)
def context_stack_length(context):
    return len(context.dicts)


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
def simple_keyword_only_param(*, kwarg):
    return "simple_keyword_only_param - Expected result: %s" % kwarg


@register.simple_tag
def simple_keyword_only_default(*, kwarg=42):
    return "simple_keyword_only_default - Expected result: %s" % kwarg


@register.simple_tag
def simple_one_default(one, two='hi'):
    """Expected simple_one_default __doc__"""
    return "simple_one_default - Expected result: %s, %s" % (one, two)


simple_one_default.anything = "Expected simple_one_default __dict__"


@register.simple_tag
def simple_unlimited_args(one, two='hi', *args):
    """Expected simple_unlimited_args __doc__"""
    return "simple_unlimited_args - Expected result: %s" % (
        ', '.join(str(arg) for arg in [one, two, *args])
    )


simple_unlimited_args.anything = "Expected simple_unlimited_args __dict__"


@register.simple_tag
def simple_only_unlimited_args(*args):
    """Expected simple_only_unlimited_args __doc__"""
    return "simple_only_unlimited_args - Expected result: %s" % ', '.join(str(arg) for arg in args)


simple_only_unlimited_args.anything = "Expected simple_only_unlimited_args __dict__"


@register.simple_tag
def simple_unlimited_args_kwargs(one, two='hi', *args, **kwargs):
    """Expected simple_unlimited_args_kwargs __doc__"""
    # Sort the dictionary by key to guarantee the order for testing.
    sorted_kwarg = sorted(kwargs.items(), key=operator.itemgetter(0))
    return "simple_unlimited_args_kwargs - Expected result: %s / %s" % (
        ', '.join(str(arg) for arg in [one, two, *args]),
        ', '.join('%s=%s' % (k, v) for (k, v) in sorted_kwarg)
    )


simple_unlimited_args_kwargs.anything = "Expected simple_unlimited_args_kwargs __dict__"


@register.simple_tag(takes_context=True)
def simple_tag_without_context_parameter(arg):
    """Expected simple_tag_without_context_parameter __doc__"""
    return "Expected result"


simple_tag_without_context_parameter.anything = "Expected simple_tag_without_context_parameter __dict__"


@register.simple_tag(takes_context=True)
def escape_naive(context):
    """A tag that doesn't even think about escaping issues"""
    return "Hello {0}!".format(context['name'])


@register.simple_tag(takes_context=True)
def escape_explicit(context):
    """A tag that uses escape explicitly"""
    return escape("Hello {0}!".format(context['name']))


@register.simple_tag(takes_context=True)
def escape_format_html(context):
    """A tag that uses format_html"""
    return format_html("Hello {0}!", context['name'])


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


@register.tag('counter')
def counter(parser, token):
    return CounterNode()


class CounterNode(template.Node):
    def __init__(self):
        self.count = 0

    def render(self, context):
        count = self.count
        self.count = count + 1
        return count
