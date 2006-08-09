"Misc. utility functions/classes for admin documentation generator."

import re
from email.Parser import HeaderParser
from email.Errors import HeaderParseError
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

def parse_rst(text, default_reference_context, thing_being_parsed=None, link_base='../..'):
    """
    Convert the string from reST to an XHTML fragment.
    """
    overrides = {
        'doctitle_xform' : True,
        'inital_header_level' : 3,
        "default_reference_context" : default_reference_context,
        "link_base" : link_base,
    }
    if thing_being_parsed:
        thing_being_parsed = "<%s>" % thing_being_parsed
    parts = docutils.core.publish_parts(text, source_path=thing_being_parsed,
                destination_path=None, writer_name='html',
                settings_overrides=overrides)
    return parts['fragment']

#
# reST roles
#
ROLES = {
    'model'    : '%s/models/%s/',
    'view'     : '%s/views/%s/',
    'template' : '%s/templates/%s/',
    'filter'   : '%s/filters/#%s',
    'tag'      : '%s/tags/#%s',
}

def create_reference_role(rolename, urlbase):
    def _role(name, rawtext, text, lineno, inliner, options=None, content=None):
        if options is None: options = {}
        if content is None: content = []
        node = docutils.nodes.reference(rawtext, text, refuri=(urlbase % (inliner.document.settings.link_base, text.lower())), **options)
        return [node], []
    docutils.parsers.rst.roles.register_canonical_role(rolename, _role)

def default_reference_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    if options is None: options = {}
    if content is None: content = []
    context = inliner.document.settings.default_reference_context
    node = docutils.nodes.reference(rawtext, text, refuri=(ROLES[context] % (inliner.document.settings.link_base, text.lower())), **options)
    return [node], []

if docutils_is_available:
    docutils.parsers.rst.roles.register_canonical_role('cmsreference', default_reference_role)
    docutils.parsers.rst.roles.DEFAULT_INTERPRETED_ROLE = 'cmsreference'

    for name, urlbase in ROLES.items():
        create_reference_role(name, urlbase)
        
#Based off work by Ian Holsman
#http://svn.zyons.python-hosting.com/trunk/zilbo/common/utils/misc.py

import sha
from django.conf import settings 
from django.contrib.contenttypes.models import ContentType

def verify_objref_hash( content_type_id, object_id, hash ):
    hash_match = sha.new("%s/%s" % (content_type_id, object_id) + settings.SECRET_KEY).hexdigest()
    if hash == hash_match:
        return True
    else:
        return False

def create_objref(object):
    content_type_id = ContentType.objects.get_for_model( object ).id
    object_id = object.id
    return "%s/%d/%s" % ( content_type_id, object_id, sha.new("%s/%d" % (content_type_id, object_id) + settings.SECRET_KEY).hexdigest())