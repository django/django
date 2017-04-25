"Misc. utility functions/classes for admin documentation generator."

import re
from email.errors import HeaderParseError
from email.parser import HeaderParser

from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.safestring import mark_safe
from django.utils.six.moves import zip as izip

try:
    import docutils.core
    import docutils.nodes
    import docutils.parsers.rst.roles
except ImportError:
    docutils_is_available = False
else:
    docutils_is_available = True


def trim_docstring(docstring):
    """
    Uniformly trim leading/trailing whitespace from docstrings.

    Based on https://www.python.org/dev/peps/pep-0257/#handling-docstring-indentation
    """
    if not docstring or not docstring.strip():
        return ''
    # Convert tabs to spaces and split into lines
    lines = docstring.expandtabs().splitlines()
    indent = min(len(line) - len(line.lstrip()) for line in lines if line.lstrip())
    trimmed = [lines[0].lstrip()] + [line[indent:].rstrip() for line in lines[1:]]
    return "\n".join(trimmed).strip()


def parse_docstring(docstring):
    """
    Parse out the parts of a docstring.  Return (title, body, metadata).
    """
    docstring = trim_docstring(docstring)
    parts = re.split(r'\n{2,}', docstring)
    title = parts[0]
    if len(parts) == 1:
        body = ''
        metadata = {}
    else:
        parser = HeaderParser()
        try:
            metadata = parser.parsestr(parts[-1])
        except HeaderParseError:
            metadata = {}
            body = "\n\n".join(parts[1:])
        else:
            metadata = dict(metadata.items())
            if metadata:
                body = "\n\n".join(parts[1:-1])
            else:
                body = "\n\n".join(parts[1:])
    return title, body, metadata


def parse_rst(text, default_reference_context, thing_being_parsed=None):
    """
    Convert the string from reST to an XHTML fragment.
    """
    overrides = {
        'doctitle_xform': True,
        'initial_header_level': 3,
        "default_reference_context": default_reference_context,
        "link_base": reverse('django-admindocs-docroot').rstrip('/'),
        'raw_enabled': False,
        'file_insertion_enabled': False,
    }
    if thing_being_parsed:
        thing_being_parsed = force_bytes("<%s>" % thing_being_parsed)
    # Wrap ``text`` in some reST that sets the default role to ``cmsreference``,
    # then restores it.
    source = """
.. default-role:: cmsreference

%s

.. default-role::
"""
    parts = docutils.core.publish_parts(
        source % text,
        source_path=thing_being_parsed, destination_path=None,
        writer_name='html', settings_overrides=overrides,
    )
    return mark_safe(parts['fragment'])


#
# reST roles
#
ROLES = {
    'model': '%s/models/%s/',
    'view': '%s/views/%s/',
    'template': '%s/templates/%s/',
    'filter': '%s/filters/#%s',
    'tag': '%s/tags/#%s',
}


def create_reference_role(rolename, urlbase):
    def _role(name, rawtext, text, lineno, inliner, options=None, content=None):
        if options is None:
            options = {}
        if content is None:
            content = []
        node = docutils.nodes.reference(
            rawtext,
            text,
            refuri=(urlbase % (
                inliner.document.settings.link_base,
                text.lower(),
            )),
            **options
        )
        return [node], []
    docutils.parsers.rst.roles.register_canonical_role(rolename, _role)


def default_reference_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    if options is None:
        options = {}
    if content is None:
        content = []
    context = inliner.document.settings.default_reference_context
    node = docutils.nodes.reference(
        rawtext,
        text,
        refuri=(ROLES[context] % (
            inliner.document.settings.link_base,
            text.lower(),
        )),
        **options
    )
    return [node], []


if docutils_is_available:
    docutils.parsers.rst.roles.register_canonical_role('cmsreference', default_reference_role)

    for name, urlbase in ROLES.items():
        create_reference_role(name, urlbase)


# Match unescaped parenthesis in a regex, simplify groups and then clean.
parenthesis_matcher = re.compile(r'\\.|([()])')
groups_matcher = re.compile(r'^\((?:\?(?:([iLmsux:])|P(<\w+>)|([P#=!<(]))|(?#empty))(.*)\)$')
cleanup_matcher = re.compile(
    r'(\\0[0-9]{0,3})|\\([^1-9AbBdDsSwWZafnrt])|\\[1-9][0-9]?|\\[AbBdDsSwWZafnrt]|[.^$*+?|]|\[[^]]*\]|\{[^}]*\}')


def simplify_regex(pattern):
    r"""
    Clean up urlpattern regexes into something more readable by humans. For
    example, turn "^(?P<sport_slug>\w+)/athletes/(?P<athlete_slug>\w+)/$"
    into "/<sport_slug>/athletes/<athlete_slug>/".
    """
    indices = [m.start(1) for m in parenthesis_matcher.finditer(pattern) if m.start(1) != -1]
    level = 0
    indices_level = {}
    for start in indices:
        val = pattern[start]
        if val == '(':
            indices_level.setdefault(level, []).append(start)
            level += 1
        else:
            level -= 1
            indices_level.setdefault(level, []).append(start + 1)
    adjustments = [0] * len(pattern)
    for level, indices in sorted(indices_level.items(), reverse=True):
        it = iter(indices)
        for i, (start, end) in enumerate(izip(it, it)):
            adjusted_start = start + sum(adjustments[:start])
            adjusted_end = end + sum(adjustments[:end])
            val = pattern[adjusted_start:adjusted_end]
            match = groups_matcher.match(val)
            non_capturing, named, ignored, content = match.groups()
            if named:
                replacer = named
            elif non_capturing:
                replacer = content
            elif ignored:
                replacer = ''
            else:
                replacer = '<var>'
            adjustments[start] += len(replacer) - (adjusted_end - adjusted_start)
            pattern = pattern[:adjusted_start] + replacer + pattern[adjusted_end:]

    # clean up any outstanding regex-y characters.
    pattern = cleanup_matcher.sub(lambda m: m.group(1) or m.group(2), pattern)
    if not pattern.startswith('/'):
        pattern = '/' + pattern
    return pattern
