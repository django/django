from django import template
from django.template.base import TextNode
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


@register.simple_block_tag
def div(content, id="test"):
    return format_html("<div id='{}'>{}</div>", id, content)


@register.simple_block_tag(end_name="divend")
def div_custom_end(content):
    return format_html("<div>{}</div>", content)


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


@register.simple_block_tag
def one_param_block(content, arg):
    """Expected one_param_block __doc__"""
    return f"one_param_block - Expected result: {arg} with content {content}"


@register.simple_tag(takes_context=False)
def explicit_no_context(arg):
    """Expected explicit_no_context __doc__"""
    return "explicit_no_context - Expected result: %s" % arg


explicit_no_context.anything = "Expected explicit_no_context __dict__"


@register.simple_block_tag(takes_context=False)
def explicit_no_context_block(content, arg):
    """Expected explicit_no_context_block __doc__"""
    return f"explicit_no_context_block - Expected result: {arg} with content {content}"


@register.simple_tag(takes_context=True)
def no_params_with_context(context):
    """Expected no_params_with_context __doc__"""
    return (
        "no_params_with_context - Expected result (context value: %s)"
        % context["value"]
    )


no_params_with_context.anything = "Expected no_params_with_context __dict__"


@register.simple_block_tag(takes_context=True)
def no_params_with_context_block(context, content):
    """Expected no_params_with_context_block __doc__"""
    return (
        "no_params_with_context_block - Expected result (context value: %s) "
        "(content value: %s)" % (context["value"], content)
    )


@register.simple_tag(takes_context=True)
def params_and_context(context, arg):
    """Expected params_and_context __doc__"""
    return "params_and_context - Expected result (context value: %s): %s" % (
        context["value"],
        arg,
    )


params_and_context.anything = "Expected params_and_context __dict__"


@register.simple_block_tag(takes_context=True)
def params_and_context_block(context, content, arg):
    """Expected params_and_context_block __doc__"""
    return (
        "params_and_context_block - Expected result (context value: %s) "
        "(content value: %s): %s"
        % (
            context["value"],
            content,
            arg,
        )
    )


@register.simple_tag
def simple_two_params(one, two):
    """Expected simple_two_params __doc__"""
    return "simple_two_params - Expected result: %s, %s" % (one, two)


simple_two_params.anything = "Expected simple_two_params __dict__"


@register.simple_block_tag
def simple_two_params_block(content, one, two):
    """Expected simple_two_params_block __doc__"""
    return "simple_two_params_block - Expected result (content value: %s): %s, %s" % (
        content,
        one,
        two,
    )


@register.simple_tag
def simple_keyword_only_param(*, kwarg):
    return "simple_keyword_only_param - Expected result: %s" % kwarg


@register.simple_block_tag
def simple_keyword_only_param_block(content, *, kwarg):
    return (
        "simple_keyword_only_param_block - Expected result (content value: %s): %s"
        % (
            content,
            kwarg,
        )
    )


@register.simple_tag
def simple_keyword_only_default(*, kwarg=42):
    return "simple_keyword_only_default - Expected result: %s" % kwarg


@register.simple_block_tag
def simple_keyword_only_default_block(content, *, kwarg=42):
    return (
        "simple_keyword_only_default_block - Expected result (content value: %s): %s"
        % (
            content,
            kwarg,
        )
    )


@register.simple_tag
def simple_one_default(one, two="hi"):
    """Expected simple_one_default __doc__"""
    return "simple_one_default - Expected result: %s, %s" % (one, two)


simple_one_default.anything = "Expected simple_one_default __dict__"


@register.simple_block_tag
def simple_one_default_block(content, one, two="hi"):
    """Expected simple_one_default_block __doc__"""
    return "simple_one_default_block - Expected result (content value: %s): %s, %s" % (
        content,
        one,
        two,
    )


@register.simple_tag
def simple_unlimited_args(one, two="hi", *args):
    """Expected simple_unlimited_args __doc__"""
    return "simple_unlimited_args - Expected result: %s" % (
        ", ".join(str(arg) for arg in [one, two, *args])
    )


simple_unlimited_args.anything = "Expected simple_unlimited_args __dict__"


@register.simple_block_tag
def simple_unlimited_args_block(content, one, two="hi", *args):
    """Expected simple_unlimited_args_block __doc__"""
    return "simple_unlimited_args_block - Expected result (content value: %s): %s" % (
        content,
        ", ".join(str(arg) for arg in [one, two, *args]),
    )


@register.simple_tag
def simple_only_unlimited_args(*args):
    """Expected simple_only_unlimited_args __doc__"""
    return "simple_only_unlimited_args - Expected result: %s" % ", ".join(
        str(arg) for arg in args
    )


simple_only_unlimited_args.anything = "Expected simple_only_unlimited_args __dict__"


@register.simple_block_tag
def simple_only_unlimited_args_block(content, *args):
    """Expected simple_only_unlimited_args_block __doc__"""
    return (
        "simple_only_unlimited_args_block - Expected result (content value: %s): %s"
        % (
            content,
            ", ".join(str(arg) for arg in args),
        )
    )


@register.simple_tag
def simple_unlimited_args_kwargs(one, two="hi", *args, **kwargs):
    """Expected simple_unlimited_args_kwargs __doc__"""
    return "simple_unlimited_args_kwargs - Expected result: %s / %s" % (
        ", ".join(str(arg) for arg in [one, two, *args]),
        ", ".join("%s=%s" % (k, v) for (k, v) in kwargs.items()),
    )


simple_unlimited_args_kwargs.anything = "Expected simple_unlimited_args_kwargs __dict__"


@register.simple_block_tag
def simple_unlimited_args_kwargs_block(content, one, two="hi", *args, **kwargs):
    """Expected simple_unlimited_args_kwargs_block __doc__"""
    return (
        "simple_unlimited_args_kwargs_block - Expected result (content value: %s): "
        "%s / %s"
        % (
            content,
            ", ".join(str(arg) for arg in [one, two, *args]),
            ", ".join("%s=%s" % (k, v) for (k, v) in kwargs.items()),
        )
    )


@register.simple_block_tag(takes_context=True)
def simple_block_tag_without_context_parameter(arg):
    """Expected simple_block_tag_without_context_parameter __doc__"""
    return "Expected result"


@register.simple_block_tag
def simple_tag_without_content_parameter(arg):
    """Expected simple_tag_without_content_parameter __doc__"""
    return "Expected result"


@register.simple_block_tag(takes_context=True)
def simple_tag_with_context_without_content_parameter(context, arg):
    """Expected simple_tag_with_context_without_content_parameter __doc__"""
    return "Expected result"


@register.simple_tag(takes_context=True)
def simple_tag_without_context_parameter(arg):
    """Expected simple_tag_without_context_parameter __doc__"""
    return "Expected result"


simple_tag_without_context_parameter.anything = (
    "Expected simple_tag_without_context_parameter __dict__"
)


@register.simple_block_tag(takes_context=True)
def simple_tag_takes_context_without_params_block():
    """Expected simple_tag_takes_context_without_params_block __doc__"""
    return "Expected result"


@register.simple_tag(takes_context=True)
def simple_tag_takes_context_without_params():
    """Expected simple_tag_takes_context_without_params __doc__"""
    return "Expected result"


simple_tag_takes_context_without_params.anything = (
    "Expected simple_tag_takes_context_without_params __dict__"
)


@register.simple_block_tag
def simple_block_tag_without_content():
    return "Expected result"


@register.simple_block_tag(takes_context=True)
def simple_block_tag_with_context_without_content():
    return "Expected result"


@register.simple_tag(takes_context=True)
def escape_naive(context):
    """A tag that doesn't even think about escaping issues"""
    return "Hello {}!".format(context["name"])


@register.simple_block_tag(takes_context=True)
def escape_naive_block(context, content):
    """A block tag that doesn't even think about escaping issues"""
    return "Hello {}: {}!".format(context["name"], content)


@register.simple_tag(takes_context=True)
def escape_explicit(context):
    """A tag that uses escape explicitly"""
    return escape("Hello {}!".format(context["name"]))


@register.simple_block_tag(takes_context=True)
def escape_explicit_block(context, content):
    """A block tag that uses escape explicitly"""
    return escape("Hello {}: {}!".format(context["name"], content))


@register.simple_tag(takes_context=True)
def escape_format_html(context):
    """A tag that uses format_html"""
    return format_html("Hello {0}!", context["name"])


@register.simple_block_tag(takes_context=True)
def escape_format_html_block(context, content):
    """A block tag that uses format_html"""
    return format_html("Hello {0}: {1}!", context["name"], content)


@register.simple_tag(takes_context=True)
def current_app(context):
    return str(context.current_app)


@register.simple_tag(takes_context=True)
def use_l10n(context):
    return str(context.use_l10n)


@register.simple_tag(name="minustwo")
def minustwo_overridden_name(value):
    return value - 2


register.simple_tag(lambda x: x - 1, name="minusone")


@register.tag("counter")
def counter(parser, token):
    return CounterNode()


class CounterNode(template.Node):
    def __init__(self):
        self.count = 0

    def render(self, context):
        count = self.count
        self.count = count + 1
        return str(count)


@register.tag("extra_data")
def do_extra_data(parser, token):
    parser.extra_data["extra_data"] = "CUSTOM_DATA"
    return TextNode("")
