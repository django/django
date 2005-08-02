"Default tags used by the template system, available to all templates."

import sys
import template

class CommentNode(template.Node):
    def render(self, context):
        return ''

class CycleNode(template.Node):
    def __init__(self, cyclevars):
        self.cyclevars = cyclevars
        self.cyclevars_len = len(cyclevars)
        self.counter = -1

    def render(self, context):
        self.counter += 1
        return self.cyclevars[self.counter % self.cyclevars_len]

class DebugNode(template.Node):
    def render(self, context):
        from pprint import pformat
        output = [pformat(val) for val in context]
        output.append('\n\n')
        output.append(pformat(sys.modules))
        return ''.join(output)

class FilterNode(template.Node):
    def __init__(self, filters, nodelist):
        self.filters, self.nodelist = filters, nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        # apply filters
        for f in self.filters:
            output = template.registered_filters[f[0]][0](output, f[1])
        return output

class FirstOfNode(template.Node):
    def __init__(self, vars):
        self.vars = vars

    def render(self, context):
        for var in self.vars:
            value = template.resolve_variable(var, context)
            if value:
                return str(value)
        return ''

class ForNode(template.Node):
    def __init__(self, loopvar, sequence, reversed, nodelist_loop):
        self.loopvar, self.sequence = loopvar, sequence
        self.reversed = reversed
        self.nodelist_loop = nodelist_loop

    def __repr__(self):
        if self.reversed:
            reversed = ' reversed'
        else:
            reversed = ''
        return "<For Node: for %s in %s, tail_len: %d%s>" % \
            (self.loopvar, self.sequence, len(self.nodelist_loop), reversed)

    def __iter__(self):
        for node in self.nodelist_loop:
            yield node

    def get_nodes_by_type(self, nodetype):
        nodes = []
        if isinstance(self, nodetype):
            nodes.append(self)
        nodes.extend(self.nodelist_loop.get_nodes_by_type(nodetype))
        return nodes

    def render(self, context):
        nodelist = template.NodeList()
        if context.has_key('forloop'):
            parentloop = context['forloop']
        else:
            parentloop = {}
        context.push()
        try:
            values = template.resolve_variable_with_filters(self.sequence, context)
        except template.VariableDoesNotExist:
            values = []
        if values is None:
            values = []
        len_values = len(values)
        if self.reversed:
            # From http://www.python.org/doc/current/tut/node11.html
            def reverse(data):
                for index in range(len(data)-1, -1, -1):
                    yield data[index]
            values = reverse(values)
        for i, item in enumerate(values):
            context['forloop'] = {
                # shortcuts for current loop iteration number
                'counter0': i,
                'counter': i+1,
                # boolean values designating first and last times through loop
                'first': (i == 0),
                'last': (i == len_values - 1),
                'parentloop': parentloop,
            }
            context[self.loopvar] = item
            for node in self.nodelist_loop:
                nodelist.append(node.render(context))
        context.pop()
        return nodelist.render(context)

class IfChangedNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
        self._last_seen = None

    def render(self, context):
        content = self.nodelist.render(context)
        if content != self._last_seen:
            firstloop = (self._last_seen == None)
            self._last_seen = content
            context.push()
            context['ifchanged'] = {'firstloop': firstloop}
            content = self.nodelist.render(context)
            context.pop()
            return content
        else:
            return ''

class IfNotEqualNode(template.Node):
    def __init__(self, var1, var2, nodelist):
        self.var1, self.var2, self.nodelist = var1, var2, nodelist

    def __repr__(self):
        return "<IfNotEqualNode>"

    def render(self, context):
        if template.resolve_variable(self.var1, context) != template.resolve_variable(self.var2, context):
            return self.nodelist.render(context)
        else:
            return ''

class IfNode(template.Node):
    def __init__(self, boolvars, nodelist_true, nodelist_false):
        self.boolvars = boolvars
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false

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
        for ifnot, boolvar in self.boolvars:
            try:
                value = template.resolve_variable_with_filters(boolvar, context)
            except template.VariableDoesNotExist:
                value = None
            if (value and not ifnot) or (ifnot and not value):
                return self.nodelist_true.render(context)
        return self.nodelist_false.render(context)

class RegroupNode(template.Node):
    def __init__(self, target_var, expression, var_name):
        self.target_var, self.expression = target_var, expression
        self.var_name = var_name

    def render(self, context):
        obj_list = template.resolve_variable_with_filters(self.target_var, context)
        if obj_list == '': # target_var wasn't found in context; fail silently
            context[self.var_name] = []
            return ''
        output = [] # list of dictionaries in the format {'grouper': 'key', 'list': [list of contents]}
        for obj in obj_list:
            grouper = template.resolve_variable_with_filters('var.%s' % self.expression, \
                template.Context({'var': obj}))
            if output and repr(output[-1]['grouper']) == repr(grouper):
                output[-1]['list'].append(obj)
            else:
                output.append({'grouper': grouper, 'list': [obj]})
        context[self.var_name] = output
        return ''

def include_is_allowed(filepath):
    from django.conf.settings import ALLOWED_INCLUDE_ROOTS
    for root in ALLOWED_INCLUDE_ROOTS:
        if filepath.startswith(root):
            return True
    return False

class SsiNode(template.Node):
    def __init__(self, filepath, parsed):
        self.filepath, self.parsed = filepath, parsed

    def render(self, context):
        if not include_is_allowed(self.filepath):
            return '' # Fail silently for invalid includes.
        try:
            fp = open(self.filepath, 'r')
            output = fp.read()
            fp.close()
        except IOError:
            output = ''
        if self.parsed:
            try:
                t = template.Template(output)
                return t.render(context)
            except template.TemplateSyntaxError:
                return '' # Fail silently for invalid included templates.
        return output

class LoadNode(template.Node):
    def __init__(self, taglib):
        self.taglib = taglib

    def load_taglib(taglib):
        mod = __import__("django.templatetags.%s" % taglib.split('.')[-1], '', '', [''])
        reload(mod)
        return mod
    load_taglib = staticmethod(load_taglib)

    def render(self, context):
        "Import the relevant module"
        try:
            self.__class__.load_taglib(self.taglib)
        except ImportError:
            pass # Fail silently for invalid loads.
        return ''

class NowNode(template.Node):
    def __init__(self, format_string):
        self.format_string = format_string

    def render(self, context):
        from datetime import datetime
        from django.utils.dateformat import DateFormat
        df = DateFormat(datetime.now())
        return df.format(self.format_string)

class TemplateTagNode(template.Node):
    mapping = {'openblock': template.BLOCK_TAG_START,
               'closeblock': template.BLOCK_TAG_END,
               'openvariable': template.VARIABLE_TAG_START,
               'closevariable': template.VARIABLE_TAG_END}

    def __init__(self, tagtype):
        self.tagtype = tagtype

    def render(self, context):
        return self.mapping.get(self.tagtype, '')

class WidthRatioNode(template.Node):
    def __init__(self, val_var, max_var, max_width):
        self.val_var = val_var
        self.max_var = max_var
        self.max_width = max_width

    def render(self, context):
        try:
            value = template.resolve_variable_with_filters(self.val_var, context)
            maxvalue = template.resolve_variable_with_filters(self.max_var, context)
        except template.VariableDoesNotExist:
            return ''
        try:
            value = float(value)
            maxvalue = float(maxvalue)
            ratio = (value / maxvalue) * int(self.max_width)
        except (ValueError, ZeroDivisionError):
            return ''
        return str(int(round(ratio)))

def do_comment(parser, token):
    """
    Ignore everything between ``{% comment %}`` and ``{% endcomment %}``
    """
    nodelist = parser.parse(('endcomment',))
    parser.delete_first_token()
    return CommentNode()

def do_cycle(parser, token):
    """
    Cycle among the given strings each time this tag is encountered

    Within a loop, cycles among the given strings each time through
    the loop::

        {% for o in some_list %}
            <tr class="{% cycle row1,row2 %}">
                ...
            </tr>
        {% endfor %}

    Outside of a loop, give the values a unique name the first time you call
    it, then use that name each sucessive time through::

            <tr class="{% cycle row1,row2,row3 as rowcolors %}">...</tr>
            <tr class="{% cycle rowcolors %}">...</tr>
            <tr class="{% cycle rowcolors %}">...</tr>

    You can use any number of values, seperated by commas. Make sure not to
    put spaces between the values -- only commas.
    """

    # Note: This returns the exact same node on each {% cycle name %} call; that
    # is, the node object returned from {% cycle a,b,c as name %} and the one
    # returned from {% cycle name %} are the exact same object.  This shouldn't
    # cause problems (heh), but if it does, now you know.
    #
    # Ugly hack warning: this stuffs the named template dict into parser so
    # that names are only unique within each template (as opposed to using
    # a global variable, which would make cycle names have to be unique across
    # *all* templates.

    args = token.contents.split()
    if len(args) < 2:
        raise template.TemplateSyntaxError("'Cycle' statement requires at least two arguments")

    elif len(args) == 2 and "," in args[1]:
        # {% cycle a,b,c %}
        cyclevars = [v for v in args[1].split(",") if v]    # split and kill blanks
        return CycleNode(cyclevars)
        # {% cycle name %}

    elif len(args) == 2:
        name = args[1]
        if not parser._namedCycleNodes.has_key(name):
            raise template.TemplateSyntaxError("Named cycle '%s' does not exist" % name)
        return parser._namedCycleNodes[name]

    elif len(args) == 4:
        # {% cycle a,b,c as name %}
        if args[2] != 'as':
            raise template.TemplateSyntaxError("Second 'cycle' argument must be 'as'")
        cyclevars = [v for v in args[1].split(",") if v]    # split and kill blanks
        name = args[3]
        node = CycleNode(cyclevars)

        if not hasattr(parser, '_namedCycleNodes'):
            parser._namedCycleNodes = {}

        parser._namedCycleNodes[name] = node
        return node

    else:
        raise template.TemplateSyntaxError("Invalid arguments to 'cycle': %s" % args)

def do_debug(parser, token):
    "Print a whole load of debugging information, including the context and imported modules"
    return DebugNode()

def do_filter(parser, token):
    """
    Filter the contents of the blog through variable filters.

    Filters can also be piped through each other, and they can have
    arguments -- just like in variable syntax.

    Sample usage::

        {% filter escape|lower %}
            This text will be HTML-escaped, and will appear in lowercase.
        {% endfilter %}
    """
    _, rest = token.contents.split(None, 1)
    _, filters = template.get_filters_from_token('var|%s' % rest)
    nodelist = parser.parse(('endfilter',))
    parser.delete_first_token()
    return FilterNode(filters, nodelist)

def do_firstof(parser, token):
    """
    Outputs the first variable passed that is not False.

    Outputs nothing if all the passed variables are False.

    Sample usage::

        {% firstof var1 var2 var3 %}
        
    This is equivalent to::
    
        {% if var1 %}
            {{ var1 }}
        {% else %}{% if var2 %}
            {{ var2 }}
        {% else %}{% if var3 %}
            {{ var3 }}
        {% endif %}{% endif %}{% endif %}
        
    but obviously much cleaner!
    """
    bits = token.contents.split()[1:]
    if len(bits) < 1:
        raise template.TemplateSyntaxError, "'firstof' statement requires at least one argument"
    return FirstOfNode(bits)


def do_for(parser, token):
    """
    Loop over each item in an array.

    For example, to display a list of athletes given ``athlete_list``::

        <ul>
        {% for athlete in athlete_list %}
            <li>{{ athlete.name }}</li>
        {% endfor %}
        </ul>

    You can also loop over a list in reverse by using
    ``{% for obj in list reversed %}``.

    The for loop sets a number of variables available within the loop:

        ==========================  ================================================
        Variable                    Description
        ==========================  ================================================
        ``forloop.counter``         The current iteration of the loop (1-indexed)
        ``forloop.counter0``        The current iteration of the loop (0-indexed)
        ``forloop.first``           True if this is the first time through the loop
        ``forloop.last``            True if this is the last time through the loop
        ``forloop.parentloop``      For nested loops, this is the loop "above" the
                                    current one
        ==========================  ================================================

    """
    bits = token.contents.split()
    if len(bits) == 5 and bits[4] != 'reversed':
        raise template.TemplateSyntaxError, "'for' statements with five words should end in 'reversed': %s" % token.contents
    if len(bits) not in (4, 5):
        raise template.TemplateSyntaxError, "'for' statements should have either four or five words: %s" % token.contents
    if bits[2] != 'in':
        raise template.TemplateSyntaxError, "'for' statement must contain 'in' as the second word: %s" % token.contents
    loopvar = bits[1]
    sequence = bits[3]
    reversed = (len(bits) == 5)
    nodelist_loop = parser.parse(('endfor',))
    parser.delete_first_token()
    return ForNode(loopvar, sequence, reversed, nodelist_loop)

def do_ifnotequal(parser, token):
    """
    Output the contents of the block if the two arguments do not equal each other.

    Example::

        {% ifnotequal user.id comment.user_id %}
            ...
        {% endifnotequal %}
    """
    bits = token.contents.split()
    if len(bits) != 3:
        raise template.TemplateSyntaxError, "'ifnotequal' takes two arguments"
    nodelist = parser.parse(('endifnotequal',))
    parser.delete_first_token()
    return IfNotEqualNode(bits[1], bits[2], nodelist)

def do_if(parser, token):
    """
    The ``{% if %}`` tag evaluates a variable, and if that variable is "true"
    (i.e. exists, is not empty, and is not a false boolean value) the contents
    of the block are output::
    
        {% if althlete_list %}
            Number of athletes: {{ althete_list|count }}
        {% else %}
            No athletes.
        {% endif %}
        
    In the above, if ``athlete_list`` is not empty, the number of athletes will
    be displayed by the ``{{ athlete_list|count }}`` variable.

    As you can see, the ``if`` tag can take an option ``{% else %} clause that
    will be displayed if the test fails.

    ``if`` tags may use ``or`` or ``not`` to test a number of variables or to
    negate a given variable::
    
        {% if not athlete_list %}
            There are no athletes.
        {% endif %}
        
        {% if athlete_list or coach_list %}
            There are some athletes or some coaches.
        {% endif %}
        
        {% if not athlete_list or coach_list %}
            There are no athletes or there are some coaches (OK, so 
            writing English translations of boolean logic sounds 
            stupid; it's not my fault).
        {% endif %}
    
    For simplicity, ``if`` tags do not allow ``and`` clauses; use nested ``if``s
    instead::
    
        {% if athlete_list %}
            {% if coach_list %}
                Number of athletes: {{ athlete_list|count }}.
                Number of coaches: {{ coach_list|count }}.
            {% endif %}
        {% endif %}
    """
    bits = token.contents.split()
    del bits[0]
    if not bits:
        raise template.TemplateSyntaxError, "'if' statement requires at least one argument"
    # bits now looks something like this: ['a', 'or', 'not', 'b', 'or', 'c.d']
    boolpairs = ' '.join(bits).split(' or ')
    boolvars = []
    for boolpair in boolpairs:
        if ' ' in boolpair:
            not_, boolvar = boolpair.split()
            if not_ != 'not':
                raise template.TemplateSyntaxError, "Expected 'not' in if statement"
            boolvars.append((True, boolvar))
        else:
            boolvars.append((False, boolpair))
    nodelist_true = parser.parse(('else', 'endif'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endif',))
        parser.delete_first_token()
    else:
        nodelist_false = template.NodeList()
    return IfNode(boolvars, nodelist_true, nodelist_false)

def do_ifchanged(parser, token):
    """
    Check if a value has changed from the last iteration of a loop.

    The 'ifchanged' block tag is used within a loop. It checks its own rendered
    contents against its previous state and only displays its content if the
    value has changed::

        <h1>Archive for {{ year }}</h1>

        {% for date in days %}
        {% ifchanged %}<h3>{{ date|date:"F" }}</h3>{% endifchanged %}
        <a href="{{ date|date:"M/d"|lower }}/">{{ date|date:"j" }}</a>
        {% endfor %}
    """
    bits = token.contents.split()
    if len(bits) != 1:
        raise template.TemplateSyntaxError, "'ifchanged' tag takes no arguments"
    nodelist = parser.parse(('endifchanged',))
    parser.delete_first_token()
    return IfChangedNode(nodelist)

def do_ssi(parser, token):
    """
    Output the contents of a given file into the page.

    Like a simple "include" tag, the ``ssi`` tag includes the contents
    of another file -- which must be specified using an absolute page --
    in the current page::

        {% ssi /home/html/ljworld.com/includes/right_generic.html %}

    If the optional "parsed" parameter is given, the contents of the included
    file are evaluated as template code, with the current context::

        {% ssi /home/html/ljworld.com/includes/right_generic.html parsed %}
    """
    bits = token.contents.split()
    parsed = False
    if len(bits) not in (2, 3):
        raise template.TemplateSyntaxError, "'ssi' tag takes one argument: the path to the file to be included"
    if len(bits) == 3:
        if bits[2] == 'parsed':
            parsed = True
        else:
            raise template.TemplateSyntaxError, "Second (optional) argument to %s tag must be 'parsed'" % bits[0]
    return SsiNode(bits[1], parsed)

def do_load(parser, token):
    """
    Load a custom template tag set.

    For example, to load the template tags in ``django/templatetags/news/photos.py``::

        {% load news.photos %}
    """
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError, "'load' statement takes one argument"
    taglib = bits[1]
    # check at compile time that the module can be imported
    try:
        LoadNode.load_taglib(taglib)
    except ImportError:
        raise template.TemplateSyntaxError, "'%s' is not a valid tag library" % taglib
    return LoadNode(taglib)

def do_now(parser, token):
    """
    Display the date, formatted according to the given string.

    Uses the same format as PHP's ``date()`` function; see http://php.net/date
    for all the possible values.

    Sample usage::

        It is {% now "jS F Y H:i" %}
    """
    bits = token.contents.split('"')
    if len(bits) != 3:
        raise template.TemplateSyntaxError, "'now' statement takes one argument"
    format_string = bits[1]
    return NowNode(format_string)

def do_regroup(parser, token):
    """
    Regroup a list of alike objects by a common attribute.

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
            * Janet Reno

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

    Note that `{% regroup %}`` does not work when the list to be grouped is not
    sorted by the key you are grouping by!  This means that if your list of
    people was not sorted by gender, you'd need to make sure it is sorted before
    using it, i.e.::

        {% regroup people|dictsort:"gender" by gender as grouped %}

    """
    firstbits = token.contents.split(None, 3)
    if len(firstbits) != 4:
        raise template.TemplateSyntaxError, "'regroup' tag takes five arguments"
    target_var = firstbits[1]
    if firstbits[2] != 'by':
        raise template.TemplateSyntaxError, "second argument to 'regroup' tag must be 'by'"
    lastbits_reversed = firstbits[3][::-1].split(None, 2)
    if lastbits_reversed[1][::-1] != 'as':
        raise template.TemplateSyntaxError, "next-to-last argument to 'regroup' tag must be 'as'"
    expression = lastbits_reversed[2][::-1]
    var_name = lastbits_reversed[0][::-1]
    return RegroupNode(target_var, expression, var_name)

def do_templatetag(parser, token):
    """
    Output one of the bits used to compose template tags.

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
        ==================  =======
    """
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError, "'templatetag' statement takes one argument"
    tag = bits[1]
    if not TemplateTagNode.mapping.has_key(tag):
        raise template.TemplateSyntaxError, "Invalid templatetag argument: '%s'. Must be one of: %s" % \
            (tag, TemplateTagNode.mapping.keys())
    return TemplateTagNode(tag)

def do_widthratio(parser, token):
    """
    For creating bar charts and such, this tag calculates the ratio of a given
    value to a maximum value, and then applies that ratio to a constant.

    For example::

        <img src='bar.gif' height='10' width='{% widthratio this_value max_value 100 %}' />

    Above, if ``this_value`` is 175 and ``max_value`` is 200, the the image in
    the above example will be 88 pixels wide (because 175/200 = .875; .875 *
    100 = 87.5 which is rounded up to 88).
    """
    bits = token.contents.split()
    if len(bits) != 4:
        raise template.TemplateSyntaxError("widthratio takes three arguments")
    tag, this_value_var, max_value_var, max_width = bits
    try:
        max_width = int(max_width)
    except ValueError:
        raise template.TemplateSyntaxError("widthratio final argument must be an integer")
    return WidthRatioNode(this_value_var, max_value_var, max_width)

template.register_tag('comment', do_comment)
template.register_tag('cycle', do_cycle)
template.register_tag('debug', do_debug)
template.register_tag('filter', do_filter)
template.register_tag('firstof', do_firstof)
template.register_tag('for', do_for)
template.register_tag('ifnotequal', do_ifnotequal)
template.register_tag('if', do_if)
template.register_tag('ifchanged', do_ifchanged)
template.register_tag('regroup', do_regroup)
template.register_tag('ssi', do_ssi)
template.register_tag('load', do_load)
template.register_tag('now', do_now)
template.register_tag('templatetag', do_templatetag)
template.register_tag('widthratio', do_widthratio)
