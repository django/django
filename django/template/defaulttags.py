"""Default tags used by the template system, available to all templates."""
from __future__ import unicode_literals

import os
import sys
import re
from datetime import datetime
from itertools import groupby, cycle as itertools_cycle

from django.conf import settings
from django.template.base import (Node, NodeList, Template, Context, Library,
    TemplateSyntaxError, VariableDoesNotExist, InvalidTemplateLibrary,
    BLOCK_TAG_START, BLOCK_TAG_END, VARIABLE_TAG_START, VARIABLE_TAG_END,
    SINGLE_BRACE_START, SINGLE_BRACE_END, COMMENT_TAG_START, COMMENT_TAG_END,
    VARIABLE_ATTRIBUTE_SEPARATOR, get_library, token_kwargs, kwarg_re)
from django.template.smartif import IfParser, Literal
from django.template.defaultfilters import date
from django.utils.encoding import smart_text
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils import six
from django.utils import timezone

register = Library()

class AutoEscapeControlNode(Node):
    """Implements the actions of the autoescape tag."""
    def __init__(self, setting, nodelist):
        self.setting, self.nodelist = setting, nodelist

    def render(self, context):
        old_setting = context.autoescape
        context.autoescape = self.setting
        output = self.nodelist.render(context)
        context.autoescape = old_setting
        if self.setting:
            return mark_safe(output)
        else:
            return output

class CommentNode(Node):
    def render(self, context):
        return ''

class CsrfTokenNode(Node):
    def render(self, context):
        csrf_token = context.get('csrf_token', None)
        if csrf_token:
            if csrf_token == 'NOTPROVIDED':
                return format_html("")
            else:
                return format_html("<input type='hidden' name='csrfmiddlewaretoken' value='{0}' />", csrf_token)
        else:
            # It's very probable that the token is missing because of
            # misconfiguration, so we raise a warning
            from django.conf import settings
            if settings.DEBUG:
                import warnings
                warnings.warn("A {% csrf_token %} was used in a template, but the context did not provide the value.  This is usually caused by not using RequestContext.")
            return ''

class CycleNode(Node):
    def __init__(self, cyclevars, variable_name=None, silent=False):
        self.cyclevars = cyclevars
        self.variable_name = variable_name
        self.silent = silent

    def render(self, context):
        if self not in context.render_context:
            # First time the node is rendered in template
            context.render_context[self] = itertools_cycle(self.cyclevars)
        cycle_iter = context.render_context[self]
        value = next(cycle_iter).resolve(context)
        if self.variable_name:
            context[self.variable_name] = value
        if self.silent:
            return ''
        return value

class DebugNode(Node):
    def render(self, context):
        from pprint import pformat
        output = [pformat(val) for val in context]
        output.append('\n\n')
        output.append(pformat(sys.modules))
        return ''.join(output)

class FilterNode(Node):
    def __init__(self, filter_expr, nodelist):
        self.filter_expr, self.nodelist = filter_expr, nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        # Apply filters.
        context.update({'var': output})
        filtered = self.filter_expr.resolve(context)
        context.pop()
        return filtered

class FirstOfNode(Node):
    def __init__(self, vars):
        self.vars = vars

    def render(self, context):
        for var in self.vars:
            value = var.resolve(context, True)
            if value:
                return smart_text(value)
        return ''

class ForNode(Node):
    child_nodelists = ('nodelist_loop', 'nodelist_empty')

    def __init__(self, loopvars, sequence, is_reversed, nodelist_loop, nodelist_empty=None):
        self.loopvars, self.sequence = loopvars, sequence
        self.is_reversed = is_reversed
        self.nodelist_loop = nodelist_loop
        if nodelist_empty is None:
            self.nodelist_empty = NodeList()
        else:
            self.nodelist_empty = nodelist_empty

    def __repr__(self):
        reversed_text = self.is_reversed and ' reversed' or ''
        return "<For Node: for %s in %s, tail_len: %d%s>" % \
            (', '.join(self.loopvars), self.sequence, len(self.nodelist_loop),
             reversed_text)

    def __iter__(self):
        for node in self.nodelist_loop:
            yield node
        for node in self.nodelist_empty:
            yield node

    def render(self, context):
        if 'forloop' in context:
            parentloop = context['forloop']
        else:
            parentloop = {}
        context.push()
        try:
            values = self.sequence.resolve(context, True)
        except VariableDoesNotExist:
            values = []
        if values is None:
            values = []
        if not hasattr(values, '__len__'):
            values = list(values)
        len_values = len(values)
        if len_values < 1:
            context.pop()
            return self.nodelist_empty.render(context)
        nodelist = NodeList()
        if self.is_reversed:
            values = reversed(values)
        unpack = len(self.loopvars) > 1
        # Create a forloop value in the context.  We'll update counters on each
        # iteration just below.
        loop_dict = context['forloop'] = {'parentloop': parentloop}
        for i, item in enumerate(values):
            # Shortcuts for current loop iteration number.
            loop_dict['counter0'] = i
            loop_dict['counter'] = i+1
            # Reverse counter iteration numbers.
            loop_dict['revcounter'] = len_values - i
            loop_dict['revcounter0'] = len_values - i - 1
            # Boolean values designating first and last times through loop.
            loop_dict['first'] = (i == 0)
            loop_dict['last'] = (i == len_values - 1)

            pop_context = False
            if unpack:
                # If there are multiple loop variables, unpack the item into
                # them.
                try:
                    unpacked_vars = dict(zip(self.loopvars, item))
                except TypeError:
                    pass
                else:
                    pop_context = True
                    context.update(unpacked_vars)
            else:
                context[self.loopvars[0]] = item
            # In TEMPLATE_DEBUG mode provide source of the node which
            # actually raised the exception
            if settings.TEMPLATE_DEBUG:
                for node in self.nodelist_loop:
                    try:
                        nodelist.append(node.render(context))
                    except Exception as e:
                        if not hasattr(e, 'django_template_source'):
                            e.django_template_source = node.source
                        raise
            else:
                for node in self.nodelist_loop:
                    nodelist.append(node.render(context))
            if pop_context:
                # The loop variables were pushed on to the context so pop them
                # off again. This is necessary because the tag lets the length
                # of loopvars differ to the length of each set of items and we
                # don't want to leave any vars from the previous loop on the
                # context.
                context.pop()
        context.pop()
        return nodelist.render(context)

class IfChangedNode(Node):
    child_nodelists = ('nodelist_true', 'nodelist_false')

    def __init__(self, nodelist_true, nodelist_false, *varlist):
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self._last_seen = None
        self._varlist = varlist
        self._id = str(id(self))

    def render(self, context):
        if 'forloop' in context and self._id not in context['forloop']:
            self._last_seen = None
            context['forloop'][self._id] = 1
        try:
            if self._varlist:
                # Consider multiple parameters.  This automatically behaves
                # like an OR evaluation of the multiple variables.
                compare_to = [var.resolve(context, True) for var in self._varlist]
            else:
                compare_to = self.nodelist_true.render(context)
        except VariableDoesNotExist:
            compare_to = None

        if compare_to != self._last_seen:
            self._last_seen = compare_to
            content = self.nodelist_true.render(context)
            return content
        elif self.nodelist_false:
            return self.nodelist_false.render(context)
        return ''

class IfEqualNode(Node):
    child_nodelists = ('nodelist_true', 'nodelist_false')

    def __init__(self, var1, var2, nodelist_true, nodelist_false, negate):
        self.var1, self.var2 = var1, var2
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.negate = negate

    def __repr__(self):
        return "<IfEqualNode>"

    def render(self, context):
        val1 = self.var1.resolve(context, True)
        val2 = self.var2.resolve(context, True)
        if (self.negate and val1 != val2) or (not self.negate and val1 == val2):
            return self.nodelist_true.render(context)
        return self.nodelist_false.render(context)

class IfNode(Node):

    def __init__(self, conditions_nodelists):
        self.conditions_nodelists = conditions_nodelists

    def __repr__(self):
        return "<IfNode>"

    def __iter__(self):
        for _, nodelist in self.conditions_nodelists:
            for node in nodelist:
                yield node

    @property
    def nodelist(self):
        return NodeList(node for _, nodelist in self.conditions_nodelists for node in nodelist)

    def render(self, context):
        for condition, nodelist in self.conditions_nodelists:

            if condition is not None:           # if / elif clause
                try:
                    match = condition.eval(context)
                except VariableDoesNotExist:
                    match = None
            else:                               # else clause
                match = True

            if match:
                return nodelist.render(context)

        return ''

class RegroupNode(Node):
    def __init__(self, target, expression, var_name):
        self.target, self.expression = target, expression
        self.var_name = var_name

    def resolve_expression(self, obj, context):
        # This method is called for each object in self.target. See regroup()
        # for the reason why we temporarily put the object in the context.
        context[self.var_name] = obj
        return self.expression.resolve(context, True)

    def render(self, context):
        obj_list = self.target.resolve(context, True)
        if obj_list == None:
            # target variable wasn't found in context; fail silently.
            context[self.var_name] = []
            return ''
        # List of dictionaries in the format:
        # {'grouper': 'key', 'list': [list of contents]}.
        context[self.var_name] = [
            {'grouper': key, 'list': list(val)}
            for key, val in
            groupby(obj_list, lambda obj: self.resolve_expression(obj, context))
        ]
        return ''

def include_is_allowed(filepath):
    filepath = os.path.abspath(filepath)
    for root in settings.ALLOWED_INCLUDE_ROOTS:
        if filepath.startswith(root):
            return True
    return False

class SsiNode(Node):
    def __init__(self, filepath, parsed):
        self.filepath = filepath
        self.parsed = parsed

    def render(self, context):
        filepath = self.filepath.resolve(context)

        if not include_is_allowed(filepath):
            if settings.DEBUG:
                return "[Didn't have permission to include file]"
            else:
                return '' # Fail silently for invalid includes.
        try:
            with open(filepath, 'r') as fp:
                output = fp.read()
        except IOError:
            output = ''
        if self.parsed:
            try:
                t = Template(output, name=filepath)
                return t.render(context)
            except TemplateSyntaxError as e:
                if settings.DEBUG:
                    return "[Included template had syntax error: %s]" % e
                else:
                    return '' # Fail silently for invalid included templates.
        return output

class LoadNode(Node):
    def render(self, context):
        return ''

class NowNode(Node):
    def __init__(self, format_string):
        self.format_string = format_string

    def render(self, context):
        tzinfo = timezone.get_current_timezone() if settings.USE_TZ else None
        return date(datetime.now(tz=tzinfo), self.format_string)

class SpacelessNode(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        from django.utils.html import strip_spaces_between_tags
        return strip_spaces_between_tags(self.nodelist.render(context).strip())

class TemplateTagNode(Node):
    mapping = {'openblock': BLOCK_TAG_START,
               'closeblock': BLOCK_TAG_END,
               'openvariable': VARIABLE_TAG_START,
               'closevariable': VARIABLE_TAG_END,
               'openbrace': SINGLE_BRACE_START,
               'closebrace': SINGLE_BRACE_END,
               'opencomment': COMMENT_TAG_START,
               'closecomment': COMMENT_TAG_END,
               }

    def __init__(self, tagtype):
        self.tagtype = tagtype

    def render(self, context):
        return self.mapping.get(self.tagtype, '')

class URLNode(Node):
    def __init__(self, view_name, args, kwargs, asvar):
        self.view_name = view_name
        self.args = args
        self.kwargs = kwargs
        self.asvar = asvar

    def render(self, context):
        from django.core.urlresolvers import reverse, NoReverseMatch
        args = [arg.resolve(context) for arg in self.args]
        kwargs = dict([(smart_text(k, 'ascii'), v.resolve(context))
                       for k, v in self.kwargs.items()])

        view_name = self.view_name.resolve(context)

        if not view_name:
            raise NoReverseMatch("'url' requires a non-empty first argument. "
                "The syntax changed in Django 1.5, see the docs.")

        # Try to look up the URL twice: once given the view name, and again
        # relative to what we guess is the "main" app. If they both fail,
        # re-raise the NoReverseMatch unless we're using the
        # {% url ... as var %} construct in which case return nothing.
        url = ''
        try:
            url = reverse(view_name, args=args, kwargs=kwargs, current_app=context.current_app)
        except NoReverseMatch as e:
            if settings.SETTINGS_MODULE:
                project_name = settings.SETTINGS_MODULE.split('.')[0]
                try:
                    url = reverse(project_name + '.' + view_name,
                              args=args, kwargs=kwargs,
                              current_app=context.current_app)
                except NoReverseMatch:
                    if self.asvar is None:
                        # Re-raise the original exception, not the one with
                        # the path relative to the project. This makes a
                        # better error message.
                        raise e
            else:
                if self.asvar is None:
                    raise e

        if self.asvar:
            context[self.asvar] = url
            return ''
        else:
            return url

class VerbatimNode(Node):
    def __init__(self, content):
        self.content = content

    def render(self, context):
        return self.content

class WidthRatioNode(Node):
    def __init__(self, val_expr, max_expr, max_width):
        self.val_expr = val_expr
        self.max_expr = max_expr
        self.max_width = max_width

    def render(self, context):
        try:
            value = self.val_expr.resolve(context)
            max_value = self.max_expr.resolve(context)
            max_width = int(self.max_width.resolve(context))
        except VariableDoesNotExist:
            return ''
        except (ValueError, TypeError):
            raise TemplateSyntaxError("widthratio final argument must be an number")
        try:
            value = float(value)
            max_value = float(max_value)
            ratio = (value / max_value) * max_width
        except ZeroDivisionError:
            return '0'
        except (ValueError, TypeError):
            return ''
        return str(int(round(ratio)))

class WithNode(Node):
    def __init__(self, var, name, nodelist, extra_context=None):
        self.nodelist = nodelist
        # var and name are legacy attributes, being left in case they are used
        # by third-party subclasses of this Node.
        self.extra_context = extra_context or {}
        if name:
            self.extra_context[name] = var

    def __repr__(self):
        return "<WithNode>"

    def render(self, context):
        values = dict([(key, val.resolve(context)) for key, val in
                       six.iteritems(self.extra_context)])
        context.update(values)
        output = self.nodelist.render(context)
        context.pop()
        return output

@register.tag
def autoescape(parser, token):
    """
    Force autoescape behavior for this block.
    """
    args = token.contents.split()
    if len(args) != 2:
        raise TemplateSyntaxError("'autoescape' tag requires exactly one argument.")
    arg = args[1]
    if arg not in ('on', 'off'):
        raise TemplateSyntaxError("'autoescape' argument should be 'on' or 'off'")
    nodelist = parser.parse(('endautoescape',))
    parser.delete_first_token()
    return AutoEscapeControlNode((arg == 'on'), nodelist)

@register.tag
def comment(parser, token):
    """
    Ignores everything between ``{% comment %}`` and ``{% endcomment %}``.
    """
    parser.skip_past('endcomment')
    return CommentNode()

@register.tag
def cycle(parser, token):
    """
    Cycles among the given strings each time this tag is encountered.

    Within a loop, cycles among the given strings each time through
    the loop::

        {% for o in some_list %}
            <tr class="{% cycle 'row1' 'row2' %}">
                ...
            </tr>
        {% endfor %}

    Outside of a loop, give the values a unique name the first time you call
    it, then use that name each sucessive time through::

            <tr class="{% cycle 'row1' 'row2' 'row3' as rowcolors %}">...</tr>
            <tr class="{% cycle rowcolors %}">...</tr>
            <tr class="{% cycle rowcolors %}">...</tr>

    You can use any number of values, separated by spaces. Commas can also
    be used to separate values; if a comma is used, the cycle values are
    interpreted as literal strings.

    The optional flag "silent" can be used to prevent the cycle declaration
    from returning any value::

        {% for o in some_list %}
            {% cycle 'row1' 'row2' as rowcolors silent %}
            <tr class="{{ rowcolors }}">{% include "subtemplate.html " %}</tr>
        {% endfor %}

    """

    # Note: This returns the exact same node on each {% cycle name %} call;
    # that is, the node object returned from {% cycle a b c as name %} and the
    # one returned from {% cycle name %} are the exact same object. This
    # shouldn't cause problems (heh), but if it does, now you know.
    #
    # Ugly hack warning: This stuffs the named template dict into parser so
    # that names are only unique within each template (as opposed to using
    # a global variable, which would make cycle names have to be unique across
    # *all* templates.

    args = token.split_contents()

    if len(args) < 2:
        raise TemplateSyntaxError("'cycle' tag requires at least two arguments")

    if ',' in args[1]:
        # Backwards compatibility: {% cycle a,b %} or {% cycle a,b as foo %}
        # case.
        args[1:2] = ['"%s"' % arg for arg in args[1].split(",")]

    if len(args) == 2:
        # {% cycle foo %} case.
        name = args[1]
        if not hasattr(parser, '_namedCycleNodes'):
            raise TemplateSyntaxError("No named cycles in template. '%s' is not defined" % name)
        if not name in parser._namedCycleNodes:
            raise TemplateSyntaxError("Named cycle '%s' does not exist" % name)
        return parser._namedCycleNodes[name]

    as_form = False

    if len(args) > 4:
        # {% cycle ... as foo [silent] %} case.
        if args[-3] == "as":
            if args[-1] != "silent":
                raise TemplateSyntaxError("Only 'silent' flag is allowed after cycle's name, not '%s'." % args[-1])
            as_form = True
            silent = True
            args = args[:-1]
        elif args[-2] == "as":
            as_form = True
            silent = False

    if as_form:
        name = args[-1]
        values = [parser.compile_filter(arg) for arg in args[1:-2]]
        node = CycleNode(values, name, silent=silent)
        if not hasattr(parser, '_namedCycleNodes'):
            parser._namedCycleNodes = {}
        parser._namedCycleNodes[name] = node
    else:
        values = [parser.compile_filter(arg) for arg in args[1:]]
        node = CycleNode(values)
    return node

@register.tag
def csrf_token(parser, token):
    return CsrfTokenNode()

@register.tag
def debug(parser, token):
    """
    Outputs a whole load of debugging information, including the current
    context and imported modules.

    Sample usage::

        <pre>
            {% debug %}
        </pre>
    """
    return DebugNode()

@register.tag('filter')
def do_filter(parser, token):
    """
    Filters the contents of the block through variable filters.

    Filters can also be piped through each other, and they can have
    arguments -- just like in variable syntax.

    Sample usage::

        {% filter force_escape|lower %}
            This text will be HTML-escaped, and will appear in lowercase.
        {% endfilter %}

    Note that the ``escape`` and ``safe`` filters are not acceptable arguments.
    Instead, use the ``autoescape`` tag to manage autoescaping for blocks of
    template code.
    """
    _, rest = token.contents.split(None, 1)
    filter_expr = parser.compile_filter("var|%s" % (rest))
    for func, unused in filter_expr.filters:
        if getattr(func, '_decorated_function', func).__name__ in ('escape', 'safe'):
            raise TemplateSyntaxError('"filter %s" is not permitted.  Use the "autoescape" tag instead.' % func.__name__)
    nodelist = parser.parse(('endfilter',))
    parser.delete_first_token()
    return FilterNode(filter_expr, nodelist)

@register.tag
def firstof(parser, token):
    """
    Outputs the first variable passed that is not False, without escaping.

    Outputs nothing if all the passed variables are False.

    Sample usage::

        {% firstof var1 var2 var3 %}

    This is equivalent to::

        {% if var1 %}
            {{ var1|safe }}
        {% else %}{% if var2 %}
            {{ var2|safe }}
        {% else %}{% if var3 %}
            {{ var3|safe }}
        {% endif %}{% endif %}{% endif %}

    but obviously much cleaner!

    You can also use a literal string as a fallback value in case all
    passed variables are False::

        {% firstof var1 var2 var3 "fallback value" %}

    If you want to escape the output, use a filter tag::

        {% filter force_escape %}
            {% firstof var1 var2 var3 "fallback value" %}
        {% endfilter %}

    """
    bits = token.split_contents()[1:]
    if len(bits) < 1:
        raise TemplateSyntaxError("'firstof' statement requires at least one argument")
    return FirstOfNode([parser.compile_filter(bit) for bit in bits])

@register.tag('for')
def do_for(parser, token):
    """
    Loops over each item in an array.

    For example, to display a list of athletes given ``athlete_list``::

        <ul>
        {% for athlete in athlete_list %}
            <li>{{ athlete.name }}</li>
        {% endfor %}
        </ul>

    You can loop over a list in reverse by using
    ``{% for obj in list reversed %}``.

    You can also unpack multiple values from a two-dimensional array::

        {% for key,value in dict.items %}
            {{ key }}: {{ value }}
        {% endfor %}

    The ``for`` tag can take an optional ``{% empty %}`` clause that will
    be displayed if the given array is empty or could not be found::

        <ul>
          {% for athlete in athlete_list %}
            <li>{{ athlete.name }}</li>
          {% empty %}
            <li>Sorry, no athletes in this list.</li>
          {% endfor %}
        <ul>

    The above is equivalent to -- but shorter, cleaner, and possibly faster
    than -- the following::

        <ul>
          {% if althete_list %}
            {% for athlete in athlete_list %}
              <li>{{ athlete.name }}</li>
            {% endfor %}
          {% else %}
            <li>Sorry, no athletes in this list.</li>
          {% endif %}
        </ul>

    The for loop sets a number of variables available within the loop:

        ==========================  ================================================
        Variable                    Description
        ==========================  ================================================
        ``forloop.counter``         The current iteration of the loop (1-indexed)
        ``forloop.counter0``        The current iteration of the loop (0-indexed)
        ``forloop.revcounter``      The number of iterations from the end of the
                                    loop (1-indexed)
        ``forloop.revcounter0``     The number of iterations from the end of the
                                    loop (0-indexed)
        ``forloop.first``           True if this is the first time through the loop
        ``forloop.last``            True if this is the last time through the loop
        ``forloop.parentloop``      For nested loops, this is the loop "above" the
                                    current one
        ==========================  ================================================

    """
    bits = token.contents.split()
    if len(bits) < 4:
        raise TemplateSyntaxError("'for' statements should have at least four"
                                  " words: %s" % token.contents)

    is_reversed = bits[-1] == 'reversed'
    in_index = is_reversed and -3 or -2
    if bits[in_index] != 'in':
        raise TemplateSyntaxError("'for' statements should use the format"
                                  " 'for x in y': %s" % token.contents)

    loopvars = re.split(r' *, *', ' '.join(bits[1:in_index]))
    for var in loopvars:
        if not var or ' ' in var:
            raise TemplateSyntaxError("'for' tag received an invalid argument:"
                                      " %s" % token.contents)

    sequence = parser.compile_filter(bits[in_index+1])
    nodelist_loop = parser.parse(('empty', 'endfor',))
    token = parser.next_token()
    if token.contents == 'empty':
        nodelist_empty = parser.parse(('endfor',))
        parser.delete_first_token()
    else:
        nodelist_empty = None
    return ForNode(loopvars, sequence, is_reversed, nodelist_loop, nodelist_empty)

def do_ifequal(parser, token, negate):
    bits = list(token.split_contents())
    if len(bits) != 3:
        raise TemplateSyntaxError("%r takes two arguments" % bits[0])
    end_tag = 'end' + bits[0]
    nodelist_true = parser.parse(('else', end_tag))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse((end_tag,))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()
    val1 = parser.compile_filter(bits[1])
    val2 = parser.compile_filter(bits[2])
    return IfEqualNode(val1, val2, nodelist_true, nodelist_false, negate)

@register.tag
def ifequal(parser, token):
    """
    Outputs the contents of the block if the two arguments equal each other.

    Examples::

        {% ifequal user.id comment.user_id %}
            ...
        {% endifequal %}

        {% ifnotequal user.id comment.user_id %}
            ...
        {% else %}
            ...
        {% endifnotequal %}
    """
    return do_ifequal(parser, token, False)

@register.tag
def ifnotequal(parser, token):
    """
    Outputs the contents of the block if the two arguments are not equal.
    See ifequal.
    """
    return do_ifequal(parser, token, True)

class TemplateLiteral(Literal):
    def __init__(self, value, text):
        self.value = value
        self.text = text # for better error messages

    def display(self):
        return self.text

    def eval(self, context):
        return self.value.resolve(context, ignore_failures=True)

class TemplateIfParser(IfParser):
    error_class = TemplateSyntaxError

    def __init__(self, parser, *args, **kwargs):
        self.template_parser = parser
        super(TemplateIfParser, self).__init__(*args, **kwargs)

    def create_var(self, value):
        return TemplateLiteral(self.template_parser.compile_filter(value), value)

@register.tag('if')
def do_if(parser, token):
    """
    The ``{% if %}`` tag evaluates a variable, and if that variable is "true"
    (i.e., exists, is not empty, and is not a false boolean value), the
    contents of the block are output:

    ::

        {% if athlete_list %}
            Number of athletes: {{ athlete_list|count }}
        {% elif athlete_in_locker_room_list %}
            Athletes should be out of the locker room soon!
        {% else %}
            No athletes.
        {% endif %}

    In the above, if ``athlete_list`` is not empty, the number of athletes will
    be displayed by the ``{{ athlete_list|count }}`` variable.

    As you can see, the ``if`` tag may take one or several `` {% elif %}``
    clauses, as well as an ``{% else %}`` clause that will be displayed if all
    previous conditions fail. These clauses are optional.

    ``if`` tags may use ``or``, ``and`` or ``not`` to test a number of
    variables or to negate a given variable::

        {% if not athlete_list %}
            There are no athletes.
        {% endif %}

        {% if athlete_list or coach_list %}
            There are some athletes or some coaches.
        {% endif %}

        {% if athlete_list and coach_list %}
            Both atheletes and coaches are available.
        {% endif %}

        {% if not athlete_list or coach_list %}
            There are no athletes, or there are some coaches.
        {% endif %}

        {% if athlete_list and not coach_list %}
            There are some athletes and absolutely no coaches.
        {% endif %}

    Comparison operators are also available, and the use of filters is also
    allowed, for example::

        {% if articles|length >= 5 %}...{% endif %}

    Arguments and operators _must_ have a space between them, so
    ``{% if 1>2 %}`` is not a valid if tag.

    All supported operators are: ``or``, ``and``, ``in``, ``not in``
    ``==`` (or ``=``), ``!=``, ``>``, ``>=``, ``<`` and ``<=``.

    Operator precedence follows Python.
    """
    # {% if ... %}
    bits = token.split_contents()[1:]
    condition = TemplateIfParser(parser, bits).parse()
    nodelist = parser.parse(('elif', 'else', 'endif'))
    conditions_nodelists = [(condition, nodelist)]
    token = parser.next_token()

    # {% elif ... %} (repeatable)
    while token.contents.startswith('elif'):
        bits = token.split_contents()[1:]
        condition = TemplateIfParser(parser, bits).parse()
        nodelist = parser.parse(('elif', 'else', 'endif'))
        conditions_nodelists.append((condition, nodelist))
        token = parser.next_token()

    # {% else %} (optional)
    if token.contents == 'else':
        nodelist = parser.parse(('endif',))
        conditions_nodelists.append((None, nodelist))
        token = parser.next_token()

    # {% endif %}
    assert token.contents == 'endif'

    return IfNode(conditions_nodelists)


@register.tag
def ifchanged(parser, token):
    """
    Checks if a value has changed from the last iteration of a loop.

    The ``{% ifchanged %}`` block tag is used within a loop. It has two
    possible uses.

    1. Checks its own rendered contents against its previous state and only
       displays the content if it has changed. For example, this displays a
       list of days, only displaying the month if it changes::

            <h1>Archive for {{ year }}</h1>

            {% for date in days %}
                {% ifchanged %}<h3>{{ date|date:"F" }}</h3>{% endifchanged %}
                <a href="{{ date|date:"M/d"|lower }}/">{{ date|date:"j" }}</a>
            {% endfor %}

    2. If given one or more variables, check whether any variable has changed.
       For example, the following shows the date every time it changes, while
       showing the hour if either the hour or the date has changed::

            {% for date in days %}
                {% ifchanged date.date %} {{ date.date }} {% endifchanged %}
                {% ifchanged date.hour date.date %}
                    {{ date.hour }}
                {% endifchanged %}
            {% endfor %}
    """
    bits = token.contents.split()
    nodelist_true = parser.parse(('else', 'endifchanged'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endifchanged',))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()
    values = [parser.compile_filter(bit) for bit in bits[1:]]
    return IfChangedNode(nodelist_true, nodelist_false, *values)

@register.tag
def ssi(parser, token):
    """
    Outputs the contents of a given file into the page.

    Like a simple "include" tag, the ``ssi`` tag includes the contents
    of another file -- which must be specified using an absolute path --
    in the current page::

        {% ssi "/home/html/ljworld.com/includes/right_generic.html" %}

    If the optional "parsed" parameter is given, the contents of the included
    file are evaluated as template code, with the current context::

        {% ssi "/home/html/ljworld.com/includes/right_generic.html" parsed %}
    """
    bits = token.split_contents()
    parsed = False
    if len(bits) not in (2, 3):
        raise TemplateSyntaxError("'ssi' tag takes one argument: the path to"
                                  " the file to be included")
    if len(bits) == 3:
        if bits[2] == 'parsed':
            parsed = True
        else:
            raise TemplateSyntaxError("Second (optional) argument to %s tag"
                                      " must be 'parsed'" % bits[0])
    filepath = parser.compile_filter(bits[1])
    return SsiNode(filepath, parsed)

@register.tag
def load(parser, token):
    """
    Loads a custom template tag set.

    For example, to load the template tags in
    ``django/templatetags/news/photos.py``::

        {% load news.photos %}

    Can also be used to load an individual tag/filter from
    a library::

        {% load byline from news %}

    """
    bits = token.contents.split()
    if len(bits) >= 4 and bits[-2] == "from":
        try:
            taglib = bits[-1]
            lib = get_library(taglib)
        except InvalidTemplateLibrary as e:
            raise TemplateSyntaxError("'%s' is not a valid tag library: %s" %
                                      (taglib, e))
        else:
            temp_lib = Library()
            for name in bits[1:-2]:
                if name in lib.tags:
                    temp_lib.tags[name] = lib.tags[name]
                    # a name could be a tag *and* a filter, so check for both
                    if name in lib.filters:
                        temp_lib.filters[name] = lib.filters[name]
                elif name in lib.filters:
                    temp_lib.filters[name] = lib.filters[name]
                else:
                    raise TemplateSyntaxError("'%s' is not a valid tag or filter in tag library '%s'" %
                                              (name, taglib))
            parser.add_library(temp_lib)
    else:
        for taglib in bits[1:]:
            # add the library to the parser
            try:
                lib = get_library(taglib)
                parser.add_library(lib)
            except InvalidTemplateLibrary as e:
                raise TemplateSyntaxError("'%s' is not a valid tag library: %s" %
                                          (taglib, e))
    return LoadNode()

@register.tag
def now(parser, token):
    """
    Displays the date, formatted according to the given string.

    Uses the same format as PHP's ``date()`` function; see http://php.net/date
    for all the possible values.

    Sample usage::

        It is {% now "jS F Y H:i" %}
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("'now' statement takes one argument")
    format_string = bits[1][1:-1]
    return NowNode(format_string)

@register.tag
def regroup(parser, token):
    """
    Regroups a list of alike objects by a common attribute.

    This complex tag is best illustrated by use of an example:  say that
    ``people`` is a list of ``Person`` objects that have ``first_name``,
    ``last_name``, and ``gender`` attributes, and you'd like to display a list
    that looks like:

        * Male:
            * George Bush
            * Bill Clinton
        * Female:
            * Margaret Thatcher
            * Colendeeza Rice
        * Unknown:
            * Pat Smith

    The following snippet of template code would accomplish this dubious task::

        {% regroup people by gender as grouped %}
        <ul>
        {% for group in grouped %}
            <li>{{ group.grouper }}
            <ul>
                {% for item in group.list %}
                <li>{{ item }}</li>
                {% endfor %}
            </ul>
        {% endfor %}
        </ul>

    As you can see, ``{% regroup %}`` populates a variable with a list of
    objects with ``grouper`` and ``list`` attributes.  ``grouper`` contains the
    item that was grouped by; ``list`` contains the list of objects that share
    that ``grouper``.  In this case, ``grouper`` would be ``Male``, ``Female``
    and ``Unknown``, and ``list`` is the list of people with those genders.

    Note that ``{% regroup %}`` does not work when the list to be grouped is not
    sorted by the key you are grouping by!  This means that if your list of
    people was not sorted by gender, you'd need to make sure it is sorted
    before using it, i.e.::

        {% regroup people|dictsort:"gender" by gender as grouped %}

    """
    firstbits = token.contents.split(None, 3)
    if len(firstbits) != 4:
        raise TemplateSyntaxError("'regroup' tag takes five arguments")
    target = parser.compile_filter(firstbits[1])
    if firstbits[2] != 'by':
        raise TemplateSyntaxError("second argument to 'regroup' tag must be 'by'")
    lastbits_reversed = firstbits[3][::-1].split(None, 2)
    if lastbits_reversed[1][::-1] != 'as':
        raise TemplateSyntaxError("next-to-last argument to 'regroup' tag must"
                                  " be 'as'")
    var_name = lastbits_reversed[0][::-1]
    # RegroupNode will take each item in 'target', put it in the context under
    # 'var_name', evaluate 'var_name'.'expression' in the current context, and
    # group by the resulting value. After all items are processed, it will
    # save the final result in the context under 'var_name', thus clearing the
    # temporary values. This hack is necessary because the template engine
    # doesn't provide a context-aware equivalent of Python's getattr.
    expression = parser.compile_filter(var_name +
                                       VARIABLE_ATTRIBUTE_SEPARATOR +
                                       lastbits_reversed[2][::-1])
    return RegroupNode(target, expression, var_name)

@register.tag
def spaceless(parser, token):
    """
    Removes whitespace between HTML tags, including tab and newline characters.

    Example usage::

        {% spaceless %}
            <p>
                <a href="foo/">Foo</a>
            </p>
        {% endspaceless %}

    This example would return this HTML::

        <p><a href="foo/">Foo</a></p>

    Only space between *tags* is normalized -- not space between tags and text.
    In this example, the space around ``Hello`` won't be stripped::

        {% spaceless %}
            <strong>
                Hello
            </strong>
        {% endspaceless %}
    """
    nodelist = parser.parse(('endspaceless',))
    parser.delete_first_token()
    return SpacelessNode(nodelist)

@register.tag
def templatetag(parser, token):
    """
    Outputs one of the bits used to compose template tags.

    Since the template system has no concept of "escaping", to display one of
    the bits used in template tags, you must use the ``{% templatetag %}`` tag.

    The argument tells which template bit to output:

        ==================  =======
        Argument            Outputs
        ==================  =======
        ``openblock``       ``{%``
        ``closeblock``      ``%}``
        ``openvariable``    ``{{``
        ``closevariable``   ``}}``
        ``openbrace``       ``{``
        ``closebrace``      ``}``
        ``opencomment``     ``{#``
        ``closecomment``    ``#}``
        ==================  =======
    """
    bits = token.contents.split()
    if len(bits) != 2:
        raise TemplateSyntaxError("'templatetag' statement takes one argument")
    tag = bits[1]
    if tag not in TemplateTagNode.mapping:
        raise TemplateSyntaxError("Invalid templatetag argument: '%s'."
                                  " Must be one of: %s" %
                                  (tag, list(TemplateTagNode.mapping)))
    return TemplateTagNode(tag)

@register.tag
def url(parser, token):
    """
    Returns an absolute URL matching given view with its parameters.

    This is a way to define links that aren't tied to a particular URL
    configuration::

        {% url "path.to.some_view" arg1 arg2 %}

        or

        {% url "path.to.some_view" name1=value1 name2=value2 %}

    The first argument is a path to a view. It can be an absolute Python path
    or just ``app_name.view_name`` without the project name if the view is
    located inside the project.

    Other arguments are space-separated values that will be filled in place of
    positional and keyword arguments in the URL. Don't mix positional and
    keyword arguments.

    All arguments for the URL should be present.

    For example if you have a view ``app_name.client`` taking client's id and
    the corresponding line in a URLconf looks like this::

        ('^client/(\d+)/$', 'app_name.client')

    and this app's URLconf is included into the project's URLconf under some
    path::

        ('^clients/', include('project_name.app_name.urls'))

    then in a template you can create a link for a certain client like this::

        {% url "app_name.client" client.id %}

    The URL will look like ``/clients/client/123/``.

    The first argument can also be a named URL instead of the Python path to
    the view callable. For example if the URLconf entry looks like this::

        url('^client/(\d+)/$', name='client-detail-view')

    then in the template you can use::

        {% url "client-detail-view" client.id %}

    There is even another possible value type for the first argument. It can be
    the name of a template variable that will be evaluated to obtain the view
    name or the URL name, e.g.::

        {% with view_path="app_name.client" %}
        {% url view_path client.id %}
        {% endwith %}

        or,

        {% with url_name="client-detail-view" %}
        {% url url_name client.id %}
        {% endwith %}

    """
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least one argument"
                                  " (path to a view)" % bits[0])
    try:
        viewname = parser.compile_filter(bits[1])
    except TemplateSyntaxError as exc:
        exc.args = (exc.args[0] + ". "
                "The syntax of 'url' changed in Django 1.5, see the docs."),
        raise
    args = []
    kwargs = {}
    asvar = None
    bits = bits[2:]
    if len(bits) >= 2 and bits[-2] == 'as':
        asvar = bits[-1]
        bits = bits[:-2]

    if len(bits):
        for bit in bits:
            match = kwarg_re.match(bit)
            if not match:
                raise TemplateSyntaxError("Malformed arguments to url tag")
            name, value = match.groups()
            if name:
                kwargs[name] = parser.compile_filter(value)
            else:
                args.append(parser.compile_filter(value))

    return URLNode(viewname, args, kwargs, asvar)

@register.tag
def verbatim(parser, token):
    """
    Stops the template engine from rendering the contents of this block tag.

    Usage::

        {% verbatim %}
            {% don't process this %}
        {% endverbatim %}

    You can also designate a specific closing tag block (allowing the
    unrendered use of ``{% endverbatim %}``)::

        {% verbatim myblock %}
            ...
        {% endverbatim myblock %}
    """
    nodelist = parser.parse(('endverbatim',))
    parser.delete_first_token()
    return VerbatimNode(nodelist.render(Context()))

@register.tag
def widthratio(parser, token):
    """
    For creating bar charts and such, this tag calculates the ratio of a given
    value to a maximum value, and then applies that ratio to a constant.

    For example::

        <img src='bar.gif' height='10' width='{% widthratio this_value max_value max_width %}' />

    If ``this_value`` is 175, ``max_value`` is 200, and ``max_width`` is 100,
    the image in the above example will be 88 pixels wide
    (because 175/200 = .875; .875 * 100 = 87.5 which is rounded up to 88).
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise TemplateSyntaxError("widthratio takes three arguments")
    tag, this_value_expr, max_value_expr, max_width = bits

    return WidthRatioNode(parser.compile_filter(this_value_expr),
                          parser.compile_filter(max_value_expr),
                          parser.compile_filter(max_width))

@register.tag('with')
def do_with(parser, token):
    """
    Adds one or more values to the context (inside of this block) for caching
    and easy access.

    For example::

        {% with total=person.some_sql_method %}
            {{ total }} object{{ total|pluralize }}
        {% endwith %}

    Multiple values can be added to the context::

        {% with foo=1 bar=2 %}
            ...
        {% endwith %}

    The legacy format of ``{% with person.some_sql_method as total %}`` is
    still accepted.
    """
    bits = token.split_contents()
    remaining_bits = bits[1:]
    extra_context = token_kwargs(remaining_bits, parser, support_legacy=True)
    if not extra_context:
        raise TemplateSyntaxError("%r expected at least one variable "
                                  "assignment" % bits[0])
    if remaining_bits:
        raise TemplateSyntaxError("%r received an invalid token: %r" %
                                  (bits[0], remaining_bits[0]))
    nodelist = parser.parse(('endwith',))
    parser.delete_first_token()
    return WithNode(None, None, nodelist, extra_context=extra_context)
