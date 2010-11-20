from django.conf import settings
from django.template import Library, Node, Template, TemplateSyntaxError
from django.template.defaulttags import kwarg_re, include_is_allowed, SsiNode, URLNode
from django.utils.encoding import smart_str


register = Library()

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
    filepath = parser.compile_filter(bits[1])
    return SsiNode(filepath, parsed, legacy_filepath=False)

@register.tag
def url(parser, token):
    """
    Returns an absolute URL matching given view with its parameters.

    This is a way to define links that aren't tied to a particular URL
    configuration::

        {% url "path.to.some_view" arg1 arg2 %}

        or

        {% url "path.to.some_view" name1=value1 name2=value2 %}

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

        {% url "app_name.client" client.id %}

    The URL will look like ``/clients/client/123/``.
    """
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'%s' takes at least one argument"
                                  " (path to a view)" % bits[0])
    viewname = parser.compile_filter(bits[1])
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

    return URLNode(viewname, args, kwargs, asvar, legacy_view_name=False)
