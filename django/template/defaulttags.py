"""Default tags used by the template system, available to all templates."""

import sys
import re
from itertools import cycle as itertools_cycle

from django.template import Node, NodeList, Template, Context, Variable
from django.template import TemplateSyntaxError, VariableDoesNotExist, BLOCK_TAG_START, BLOCK_TAG_END, VARIABLE_TAG_START, VARIABLE_TAG_END, SINGLE_BRACE_START, SINGLE_BRACE_END, COMMENT_TAG_START, COMMENT_TAG_END
from django.template import get_library, Library, InvalidTemplateLibrary
from django.template.smartif import IfParser, Literal
from django.conf import settings
from django.utils.encoding import smart_str, smart_unicode
from django.utils.itercompat import groupby
from django.utils.safestring import mark_safe

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
                return mark_safe(u"")
            else:
                return mark_safe(u"<div style='display:none'><input type='hidden' name='csrfmiddlewaretoken' value='%s' /></div>" % (csrf_token))
        else:
            # It's very probable that the token is missing because of
            # misconfiguration, so we raise a warning
            from django.conf import settings
            if settings.DEBUG:
                import warnings
                warnings.warn("A {% csrf_token %} was used in a template, but the context did not provide the value.  This is usually caused by not using RequestContext.")
            return u''

class CycleNode(Node):
    def __init__(self, cyclevars, variable_name=None):
        self.cyclevars = cyclevars
        self.variable_name = variable_name

    def render(self, context):
        if self not in context.render_context:
            context.render_context[self] = itertools_cycle(self.cyclevars)
        cycle_iter = context.render_context[self]
        value = cycle_iter.next().resolve(context)
        if self.variable_name:
            context[self.variable_name] = value
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
                return smart_unicode(value)
        return u''

class ForNode(Node):
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

    def get_nodes_by_type(self, nodetype):
        nodes = []
        if isinstance(self, nodetype):
            nodes.append(self)
        nodes.extend(self.nodelist_loop.get_nodes_by_type(nodetype))
        nodes.extend(self.nodelist_empty.get_nodes_by_type(nodetype))
        return nodes

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

            if unpack:
                # If there are multiple loop variables, unpack the item into
                # them.
                context.update(dict(zip(self.loopvars, item)))
            else:
                context[self.loopvars[0]] = item
            for node in self.nodelist_loop:
                nodelist.append(node.render(context))
            if unpack:
                # The loop variables were pushed on to the context so pop them
                # off again. This is necessary because the tag lets the length
                # of loopvars differ to the length of each set of items and we
                # don't want to leave any vars from the previous loop on the
                # context.
                context.pop()
        context.pop()
        return nodelist.render(context)

class IfChangedNode(Node):
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
            firstloop = (self._last_seen == None)
            self._last_seen = compare_to
            content = self.nodelist_true.render(context)
            return content
        elif self.nodelist_false:
            return self.nodelist_false.render(context)
        return ''

class IfEqualNode(Node):
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
    def __init__(self, var, nodelist_true, nodelist_false=None):
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.var = var

    def __repr__(self):
        return "<If node>"

    def __iter__(self):
        for node in self.nodelist_true:
            yield node
        for node in self.nodelist_false:
            yield node

    def get_nodes_by_type(self, nodetype):
        nodes = []
        if isinstance(self, nodetype):
            nodes.append(self)
        nodes.extend(self.nodelist_true.get_nodes_by_type(nodetype))
        nodes.extend(self.nodelist_false.get_nodes_by_type(nodetype))
        return nodes

    def render(self, context):
        if self.var.eval(context):
            return self.nodelist_true.render(context)
        else:
            return self.nodelist_false.render(context)

class RegroupNode(Node):
    def __init__(self, target, expression, var_name):
        self.target, self.expression = target, expression
        self.var_name = var_name

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
            groupby(obj_list, lambda v, f=self.expression.resolve: f(v, True))
        ]
        return ''

def include_is_allowed(filepath):
    for root in settings.ALLOWED_INCLUDE_ROOTS:
        if filepath.startswith(root):
            return True
    return False

class SsiNode(Node):
    def __init__(self, filepath, parsed):
        self.filepath, self.parsed = filepath, parsed

    def render(self, context):
        if not include_is_allowed(self.filepath):
            if settings.DEBUG:
                return "[Didn't have permission to include file]"
            else:
                return '' # Fail silently for invalid includes.
        try:
            fp = open(self.filepath, 'r')
            output = fp.read()
            fp.close()
        except IOError:
            output = ''
        if self.parsed:
            try:
                t = Template(output, name=self.filepath)
                return t.render(context)
            except TemplateSyntaxError, e:
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
        from datetime import datetime
        from django.utils.dateformat import DateFormat
        df = DateFormat(datetime.now())
        return df.format(self.format_string)

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
        kwargs = dict([(smart_str(k,'ascii'), v.resolve(context))
                       for k, v in self.kwargs.items()])

        # Try to look up the URL twice: once given the view name, and again
        # relative to what we guess is the "main" app. If they both fail,
        # re-raise the NoReverseMatch unless we're using the
        # {% url ... as var %} construct in which cause return nothing.
        url = ''
        try:
            url = reverse(self.view_name, args=args, kwargs=kwargs, current_app=context.current_app)
        except NoReverseMatch, e:
            if settings.SETTINGS_MODULE:
                project_name = settings.SETTINGS_MODULE.split('.')[0]
                try:
                    url = reverse(project_name + '.' + self.view_name,
                              args=args, kwargs=kwargs, current_app=context.current_app)
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

class WidthRatioNode(Node):
    def __init__(self, val_expr, max_expr, max_width):
        self.val_expr = val_expr
        self.max_expr = max_expr
        self.max_width = max_width

    def render(self, context):
        try:
            value = self.val_expr.resolve(context)
            maxvalue = self.max_expr.resolve(context)
            max_width = int(self.max_width.resolve(context))
        except VariableDoesNotExist:
            return ''
        except ValueError:
            raise TemplateSyntaxError("widthratio final argument must be an number")
        try:
            value = float(value)
            maxvalue = float(maxvalue)
            ratio = (value / maxvalue) * max_width
        except (ValueError, ZeroDivisionError):
            return ''
        return str(int(round(ratio)))

class WithNode(Node):
    def __init__(self, var, name, nodelist):
        self.var = var
        self.name = name
        self.nodelist = nodelist

    def __repr__(self):
        return "<WithNode>"

    def render(self, context):
        val = self.var.resolve(context)
        context.push()
        context[self.name] = val
        output = self.nodelist.render(context)
        context.pop()
        return output

#@register.tag
def autoescape(parser, token):
    """
    Force autoescape behaviour for this block.
    """
    args = token.contents.split()
    if len(args) != 2:
        raise TemplateSyntaxError("'autoescape' tag requires exactly one argument.")
    arg = args[1]
    if arg not in (u'on', u'off'):
        raise TemplateSyntaxError("'autoescape' argument should be 'on' or 'off'")
    nodelist = parser.parse(('endautoescape',))
    parser.delete_first_token()
    return AutoEscapeControlNode((arg == 'on'), nodelist)
autoescape = register.tag(autoescape)

#@register.tag
def comment(parser, token):
    """
    Ignores everything between ``{% comment %}`` and ``{% endcomment %}``.
    """
    parser.skip_past('endcomment')
    return CommentNode()
comment = register.tag(comment)

#@register.tag
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

    if len(args) > 4 and args[-2] == 'as':
        name = args[-1]
        values = [parser.compile_filter(arg) for arg in args[1:-2]]
        node = CycleNode(values, name)
        if not hasattr(parser, '_namedCycleNodes'):
            parser._namedCycleNodes = {}
        parser._namedCycleNodes[name] = node
    else:
        values = [parser.compile_filter(arg) for arg in args[1:]]
        node = CycleNode(values)
    return node
cycle = register.tag(cycle)

def csrf_token(parser, token):
    return CsrfTokenNode()
register.tag(csrf_token)

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
debug = register.tag(debug)

#@register.tag(name="filter")
def do_filter(parser, token):
    """
    Filters the contents of the block through variable filters.

    Filters can also be piped through each other, and they can have
    arguments -- just like in variable syntax.

    Sample usage::

        {% filter force_escape|lower %}
            This text will be HTML-escaped, and will appear in lowercase.
        {% endfilter %}
    """
    _, rest = token.contents.split(None, 1)
    filter_expr = parser.compile_filter("var|%s" % (rest))
    for func, unused in filter_expr.filters:
        if getattr(func, '_decorated_function', func).__name__ in ('escape', 'safe'):
            raise TemplateSyntaxError('"filter %s" is not permitted.  Use the "autoescape" tag instead.' % func.__name__)
    nodelist = parser.parse(('endfilter',))
    parser.delete_first_token()
    return FilterNode(filter_expr, nodelist)
do_filter = register.tag("filter", do_filter)

#@register.tag
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
firstof = register.tag(firstof)

#@register.tag(name="for")
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

    loopvars = re.sub(r' *, *', ',', ' '.join(bits[1:in_index])).split(',')
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
do_for = register.tag("for", do_for)

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

#@register.tag
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
ifequal = register.tag(ifequal)

#@register.tag
def ifnotequal(parser, token):
    """
    Outputs the contents of the block if the two arguments are not equal.
    See ifequal.
    """
    return do_ifequal(parser, token, True)
ifnotequal = register.tag(ifnotequal)

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
        return super(TemplateIfParser, self).__init__(*args, **kwargs)

    def create_var(self, value):
        return TemplateLiteral(self.template_parser.compile_filter(value), value)

#@register.tag(name="if")
def do_if(parser, token):
    """
    The ``{% if %}`` tag evaluates a variable, and if that variable is "true"
    (i.e., exists, is not empty, and is not a false boolean value), the
    contents of the block are output:

    ::

        {% if athlete_list %}
            Number of athletes: {{ athlete_list|count }}
        {% else %}
            No athletes.
        {% endif %}

    In the above, if ``athlete_list`` is not empty, the number of athletes will
    be displayed by the ``{{ athlete_list|count }}`` variable.

    As you can see, the ``if`` tag can take an option ``{% else %}`` clause
    that will be displayed if the test fails.

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
    allowed, for example:

        {% if articles|length >= 5 %}...{% endif %}

    Arguments and operators _must_ have a space between them, so
    ``{% if 1>2 %}`` is not a valid if tag.

    All supported operators are: ``or``, ``and``, ``in``, ``==`` (or ``=``),
    ``!=``, ``>``, ``>=``, ``<`` and ``<=``.

    Operator precedence follows Python.
    """
    bits = token.split_contents()[1:]
    var = TemplateIfParser(parser, bits).parse()
    nodelist_true = parser.parse(('else', 'endif'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endif',))
        parser.delete_first_token()
    else:
        nodelist_false = NodeList()
    return IfNode(var, nodelist_true, nodelist_false)
do_if = register.tag("if", do_if)

#@register.tag
def ifchanged(parser, token):
    """
    Checks if a value has changed from the last iteration of a loop.

    The 'ifchanged' block tag is used within a loop. It has two possible uses.

    1. Checks its own rendered contents against its previous state and only
       displays the content if it has changed. For example, this displays a
       list of days, only displaying the month if it changes::

            <h1>Archive for {{ year }}</h1>

            {% for date in days %}
                {% ifchanged %}<h3>{{ date|date:"F" }}</h3>{% endifchanged %}
                <a href="{{ date|date:"M/d"|lower }}/">{{ date|date:"j" }}</a>
            {% endfor %}

    2. If given a variable, check whether that variable has changed.
       For example, the following shows the date every time it changes, but
       only shows the hour if both the hour and the date have changed::

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
ifchanged = register.tag(ifchanged)

#@register.tag
def ssi(parser, token):
    """
    Outputs the contents of a given file into the page.

    Like a simple "include" tag, the ``ssi`` tag includes the contents
    of another file -- which must be specified using an absolute path --
    in the current page::

        {% ssi /home/html/ljworld.com/includes/right_generic.html %}

    If the optional "parsed" parameter is given, the contents of the included
    file are evaluated as template code, with the current context::

        {% ssi /home/html/ljworld.com/includes/right_generic.html parsed %}
    """
    bits = token.contents.split()
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
    return SsiNode(bits[1], parsed)
ssi = register.tag(ssi)

#@register.tag
def load(parser, token):
    """
    Loads a custom template tag set.

    For example, to load the template tags in
    ``django/templatetags/news/photos.py``::

        {% load news.photos %}
    """
    bits = token.contents.split()
    for taglib in bits[1:]:
        # add the library to the parser
        try:
            lib = get_library(taglib)
            parser.add_library(lib)
        except InvalidTemplateLibrary, e:
            raise TemplateSyntaxError("'%s' is not a valid tag library: %s" %
                                      (taglib, e))
    return LoadNode()
load = register.tag(load)

#@register.tag
def now(parser, token):
    """
    Displays the date, formatted according to the given string.

    Uses the same format as PHP's ``date()`` function; see http://php.net/date
    for all the possible values.

    Sample usage::

        It is {% now "jS F Y H:i" %}
    """
    bits = token.contents.split('"')
    if len(bits) != 3:
        raise TemplateSyntaxError("'now' statement takes one argument")
    format_string = bits[1]
    return NowNode(format_string)
now = register.tag(now)

#@register.tag
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

    expression = parser.compile_filter(lastbits_reversed[2][::-1])

    var_name = lastbits_reversed[0][::-1]
    return RegroupNode(target, expression, var_name)
regroup = register.tag(regroup)

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
spaceless = register.tag(spaceless)

#@register.tag
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
                                  (tag, TemplateTagNode.mapping.keys()))
    return TemplateTagNode(tag)
templatetag = register.tag(templatetag)

def url(parser, token):
    """
    Returns an absolute URL matching given view with its parameters.

    This is a way to define links that aren't tied to a particular URL
    configuration::

        {% url path.to.some_view arg1,arg2,name1=value1 %}

    The first argument is a path to a view. It can be an absolute python path
    or just ``app_name.view_name`` without the project name if the view is
    located inside the project.  Other arguments are comma-separated values
    that will be filled in place of positional and keyword arguments in the
    URL. All arguments for the URL should be present.

    For example if you have a view ``app_name.client`` taking client's id and
    the corresponding line in a URLconf looks like this::

        ('^client/(\d+)/$', 'app_name.client')

    and this app's URLconf is included into the project's URLconf under some
    path::

        ('^clients/', include('project_name.app_name.urls'))

    then in a template you can create a link for a certain client like this::

        {% url app_name.client client.id %}

    The URL will look like ``/clients/client/123/``.
    """
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least one argument"
                                  " (path to a view)" % bits[0])
    viewname = bits[1]
    args = []
    kwargs = {}
    asvar = None

    if len(bits) > 2:
        bits = iter(bits[2:])
        for bit in bits:
            if bit == 'as':
                asvar = bits.next()
                break
            else:
                for arg in bit.split(","):
                    if '=' in arg:
                        k, v = arg.split('=', 1)
                        k = k.strip()
                        kwargs[k] = parser.compile_filter(v)
                    elif arg:
                        args.append(parser.compile_filter(arg))
    return URLNode(viewname, args, kwargs, asvar)
url = register.tag(url)

#@register.tag
def widthratio(parser, token):
    """
    For creating bar charts and such, this tag calculates the ratio of a given
    value to a maximum value, and then applies that ratio to a constant.

    For example::

        <img src='bar.gif' height='10' width='{% widthratio this_value max_value 100 %}' />

    Above, if ``this_value`` is 175 and ``max_value`` is 200, the image in
    the above example will be 88 pixels wide (because 175/200 = .875;
    .875 * 100 = 87.5 which is rounded up to 88).
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise TemplateSyntaxError("widthratio takes three arguments")
    tag, this_value_expr, max_value_expr, max_width = bits

    return WidthRatioNode(parser.compile_filter(this_value_expr),
                          parser.compile_filter(max_value_expr),
                          parser.compile_filter(max_width))
widthratio = register.tag(widthratio)

#@register.tag
def do_with(parser, token):
    """
    Adds a value to the context (inside of this block) for caching and easy
    access.

    For example::

        {% with person.some_sql_method as total %}
            {{ total }} object{{ total|pluralize }}
        {% endwith %}
    """
    bits = list(token.split_contents())
    if len(bits) != 4 or bits[2] != "as":
        raise TemplateSyntaxError("%r expected format is 'value as name'" %
                                  bits[0])
    var = parser.compile_filter(bits[1])
    name = bits[3]
    nodelist = parser.parse(('endwith',))
    parser.delete_first_token()
    return WithNode(var, name, nodelist)
do_with = register.tag('with', do_with)
