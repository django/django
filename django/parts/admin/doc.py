"""
Misc. utility functions/classes for documentation generator
"""

import re
from email.Parser import HeaderParser
from email.Errors import HeaderParseError
import docutils.core
import docutils.nodes
import docutils.parsers.rst.roles

#
# reST roles
#
ROLES = {
    # role name,    base role url (in the admin)
    'model'    : '/doc/models/%s/',
    'view'     : '/doc/views/%s/',
    'template' : '/doc/templates/%s/',
    'filter'   : '/doc/filters/#%s',
    'tag'      : '/doc/tags/#%s',
}

def trim_docstring(docstring):
    """
    Uniformly trims leading/trailing whitespace from docstrings.

    Based on http://www.python.org/peps/pep-0257.html#handling-docstring-indentation
    """
    if not docstring or not docstring.strip():
        return ''
    # Convert tabs to spaces and split into lines
    lines = docstring.expandtabs().splitlines()
    indent = min([len(line) - len(line.lstrip()) for line in lines if line.lstrip()])
    trimmed = [lines[0].lstrip()] + [line[indent:].rstrip() for line in lines[1:]]
    return "\n".join(trimmed).strip()

def parse_docstring(docstring):
    """
    Parse out the parts of a docstring.  Returns (title, body, metadata).
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
        'input_encoding' : 'unicode',
        'doctitle_xform' : True,
        'inital_header_level' : 3,
    }
    if thing_being_parsed:
        thing_being_parsed = "<%s>" % thing_being_parsed
    parts = docutils.core.publish_parts(text, source_path=thing_being_parsed,
                destination_path=None, writer_name='html',
                settings_overrides={'default_reference_context' : default_reference_context})
    return parts['fragment']

def create_reference_role(rolename, urlbase):
    def _role(name, rawtext, text, lineno, inliner, options={}, content=[]):
        node = docutils.nodes.reference(rawtext, text, refuri=(urlbase % text), **options)
        return [node], []
    docutils.parsers.rst.roles.register_canonical_role(rolename, _role)

def default_reference_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    context = inliner.document.settings.default_reference_context
    node = docutils.nodes.reference(rawtext, text, refuri=(ROLES[context] % text), **options)
    return [node], []
docutils.parsers.rst.roles.register_canonical_role('cmsreference', default_reference_role)
docutils.parsers.rst.roles.DEFAULT_INTERPRETED_ROLE = 'cmsreference'

for (name, urlbase) in ROLES.items():
    create_reference_role(name, urlbase)
