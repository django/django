# $Id: roles.py 7937 2016-05-24 10:48:48Z milde $
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# Copyright: This module has been placed in the public domain.

"""
This module defines standard interpreted text role functions, a registry for
interpreted text roles, and an API for adding to and retrieving from the
registry.

The interface for interpreted role functions is as follows::

    def role_fn(name, rawtext, text, lineno, inliner,
                options={}, content=[]):
        code...

    # Set function attributes for customization:
    role_fn.options = ...
    role_fn.content = ...

Parameters:

- ``name`` is the local name of the interpreted text role, the role name
  actually used in the document.

- ``rawtext`` is a string containing the entire interpreted text construct.
  Return it as a ``problematic`` node linked to a system message if there is a
  problem.

- ``text`` is the interpreted text content, with backslash escapes converted
  to nulls (``\x00``).

- ``lineno`` is the line number where the interpreted text beings.

- ``inliner`` is the Inliner object that called the role function.
  It defines the following useful attributes: ``reporter``,
  ``problematic``, ``memo``, ``parent``, ``document``.

- ``options``: A dictionary of directive options for customization, to be
  interpreted by the role function.  Used for additional attributes for the
  generated elements and other functionality.

- ``content``: A list of strings, the directive content for customization
  ("role" directive).  To be interpreted by the role function.

Function attributes for customization, interpreted by the "role" directive:

- ``options``: A dictionary, mapping known option names to conversion
  functions such as `int` or `float`.  ``None`` or an empty dict implies no
  options to parse.  Several directive option conversion functions are defined
  in the `directives` module.

  All role functions implicitly support the "class" option, unless disabled
  with an explicit ``{'class': None}``.

- ``content``: A boolean; true if content is allowed.  Client code must handle
  the case where content is required but not supplied (an empty content list
  will be supplied).

Note that unlike directives, the "arguments" function attribute is not
supported for role customization.  Directive arguments are handled by the
"role" directive itself.

Interpreted role functions return a tuple of two values:

- A list of nodes which will be inserted into the document tree at the
  point where the interpreted role was encountered (can be an empty
  list).

- A list of system messages, which will be inserted into the document tree
  immediately after the end of the current inline block (can also be empty).
"""

__docformat__ = 'reStructuredText'

from docutils import nodes, utils
from docutils.parsers.rst import directives
from docutils.parsers.rst.languages import en as _fallback_language_module
from docutils.utils.code_analyzer import Lexer, LexerError

DEFAULT_INTERPRETED_ROLE = 'title-reference'
"""
The canonical name of the default interpreted role.  This role is used
when no role is specified for a piece of interpreted text.
"""

_role_registry = {}
"""Mapping of canonical role names to role functions.  Language-dependent role
names are defined in the ``language`` subpackage."""

_roles = {}
"""Mapping of local or language-dependent interpreted text role names to role
functions."""

def role(role_name, language_module, lineno, reporter):
    """
    Locate and return a role function from its language-dependent name, along
    with a list of system messages.  If the role is not found in the current
    language, check English.  Return a 2-tuple: role function (``None`` if the
    named role cannot be found) and a list of system messages.
    """
    normname = role_name.lower()
    messages = []
    msg_text = []

    if normname in _roles:
        return _roles[normname], messages

    if role_name:
        canonicalname = None
        try:
            canonicalname = language_module.roles[normname]
        except AttributeError as error:
            msg_text.append('Problem retrieving role entry from language '
                            'module %r: %s.' % (language_module, error))
        except KeyError:
            msg_text.append('No role entry for "%s" in module "%s".'
                            % (role_name, language_module.__name__))
    else:
        canonicalname = DEFAULT_INTERPRETED_ROLE

    # If we didn't find it, try English as a fallback.
    if not canonicalname:
        try:
            canonicalname = _fallback_language_module.roles[normname]
            msg_text.append('Using English fallback for role "%s".'
                            % role_name)
        except KeyError:
            msg_text.append('Trying "%s" as canonical role name.'
                            % role_name)
            # The canonical name should be an English name, but just in case:
            canonicalname = normname

    # Collect any messages that we generated.
    if msg_text:
        message = reporter.info('\n'.join(msg_text), line=lineno)
        messages.append(message)

    # Look the role up in the registry, and return it.
    if canonicalname in _role_registry:
        role_fn = _role_registry[canonicalname]
        register_local_role(normname, role_fn)
        return role_fn, messages
    else:
        return None, messages # Error message will be generated by caller.

def register_canonical_role(name, role_fn):
    """
    Register an interpreted text role by its canonical name.

    :Parameters:
      - `name`: The canonical name of the interpreted role.
      - `role_fn`: The role function.  See the module docstring.
    """
    set_implicit_options(role_fn)
    _role_registry[name] = role_fn

def register_local_role(name, role_fn):
    """
    Register an interpreted text role by its local or language-dependent name.

    :Parameters:
      - `name`: The local or language-dependent name of the interpreted role.
      - `role_fn`: The role function.  See the module docstring.
    """
    set_implicit_options(role_fn)
    _roles[name] = role_fn

def set_implicit_options(role_fn):
    """
    Add customization options to role functions, unless explicitly set or
    disabled.
    """
    if not hasattr(role_fn, 'options') or role_fn.options is None:
        role_fn.options = {'class': directives.class_option}
    elif 'class' not in role_fn.options:
        role_fn.options['class'] = directives.class_option

def register_generic_role(canonical_name, node_class):
    """For roles which simply wrap a given `node_class` around the text."""
    role = GenericRole(canonical_name, node_class)
    register_canonical_role(canonical_name, role)


class GenericRole:

    """
    Generic interpreted text role, where the interpreted text is simply
    wrapped with the provided node class.
    """

    def __init__(self, role_name, node_class):
        self.name = role_name
        self.node_class = node_class

    def __call__(self, role, rawtext, text, lineno, inliner,
                 options={}, content=[]):
        set_classes(options)
        return [self.node_class(rawtext, utils.unescape(text), **options)], []


class CustomRole:

    """
    Wrapper for custom interpreted text roles.
    """

    def __init__(self, role_name, base_role, options={}, content=[]):
        self.name = role_name
        self.base_role = base_role
        self.options = None
        if hasattr(base_role, 'options'):
            self.options = base_role.options
        self.content = None
        if hasattr(base_role, 'content'):
            self.content = base_role.content
        self.supplied_options = options
        self.supplied_content = content

    def __call__(self, role, rawtext, text, lineno, inliner,
                 options={}, content=[]):
        opts = self.supplied_options.copy()
        opts.update(options)
        cont = list(self.supplied_content)
        if cont and content:
            cont += '\n'
        cont.extend(content)
        return self.base_role(role, rawtext, text, lineno, inliner,
                              options=opts, content=cont)


def generic_custom_role(role, rawtext, text, lineno, inliner,
                        options={}, content=[]):
    """"""
    # Once nested inline markup is implemented, this and other methods should
    # recursively call inliner.nested_parse().
    set_classes(options)
    return [nodes.inline(rawtext, utils.unescape(text), **options)], []

generic_custom_role.options = {'class': directives.class_option}


######################################################################
# Define and register the standard roles:
######################################################################

register_generic_role('abbreviation', nodes.abbreviation)
register_generic_role('acronym', nodes.acronym)
register_generic_role('emphasis', nodes.emphasis)
register_generic_role('literal', nodes.literal)
register_generic_role('strong', nodes.strong)
register_generic_role('subscript', nodes.subscript)
register_generic_role('superscript', nodes.superscript)
register_generic_role('title-reference', nodes.title_reference)

def pep_reference_role(role, rawtext, text, lineno, inliner,
                       options={}, content=[]):
    try:
        pepnum = int(text)
        if pepnum < 0 or pepnum > 9999:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            'PEP number must be a number from 0 to 9999; "%s" is invalid.'
            % text, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    # Base URL mainly used by inliner.pep_reference; so this is correct:
    ref = (inliner.document.settings.pep_base_url
           + inliner.document.settings.pep_file_url_template % pepnum)
    set_classes(options)
    return [nodes.reference(rawtext, 'PEP ' + utils.unescape(text), refuri=ref,
                            **options)], []

register_canonical_role('pep-reference', pep_reference_role)

def rfc_reference_role(role, rawtext, text, lineno, inliner,
                       options={}, content=[]):
    try:
        rfcnum = int(text)
        if rfcnum <= 0:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            'RFC number must be a number greater than or equal to 1; '
            '"%s" is invalid.' % text, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    # Base URL mainly used by inliner.rfc_reference, so this is correct:
    ref = inliner.document.settings.rfc_base_url + inliner.rfc_url % rfcnum
    set_classes(options)
    node = nodes.reference(rawtext, 'RFC ' + utils.unescape(text), refuri=ref,
                           **options)
    return [node], []

register_canonical_role('rfc-reference', rfc_reference_role)

def raw_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    if not inliner.document.settings.raw_enabled:
        msg = inliner.reporter.warning('raw (and derived) roles disabled')
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    if 'format' not in options:
        msg = inliner.reporter.error(
            'No format (Writer name) is associated with this role: "%s".\n'
            'The "raw" role cannot be used directly.\n'
            'Instead, use the "role" directive to create a new role with '
            'an associated format.' % role, line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]
    set_classes(options)
    node = nodes.raw(rawtext, utils.unescape(text, 1), **options)
    node.source, node.line = inliner.reporter.get_source_and_line(lineno)
    return [node], []

raw_role.options = {'format': directives.unchanged}

register_canonical_role('raw', raw_role)

def code_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    set_classes(options)
    language = options.get('language', '')
    classes = ['code']
    if 'classes' in options:
        classes.extend(options['classes'])
    if language and language not in classes:
        classes.append(language)
    try:
        tokens = Lexer(utils.unescape(text, 1), language,
                       inliner.document.settings.syntax_highlight)
    except LexerError as error:
        msg = inliner.reporter.warning(error)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    node = nodes.literal(rawtext, '', classes=classes)

    # analyse content and add nodes for every token
    for classes, value in tokens:
        # print (classes, value)
        if classes:
            node += nodes.inline(value, value, classes=classes)
        else:
            # insert as Text to decrease the verbosity of the output
            node += nodes.Text(value, value)

    return [node], []

code_role.options = {'class': directives.class_option,
                     'language': directives.unchanged}

register_canonical_role('code', code_role)

def math_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    set_classes(options)
    i = rawtext.find('`')
    text = rawtext.split('`')[1]
    node = nodes.math(rawtext, text, **options)
    return [node], []

register_canonical_role('math', math_role)

######################################################################
# Register roles that are currently unimplemented.
######################################################################

def unimplemented_role(role, rawtext, text, lineno, inliner, attributes={}):
    msg = inliner.reporter.error(
        'Interpreted text role "%s" not implemented.' % role, line=lineno)
    prb = inliner.problematic(rawtext, rawtext, msg)
    return [prb], [msg]

register_canonical_role('index', unimplemented_role)
register_canonical_role('named-reference', unimplemented_role)
register_canonical_role('anonymous-reference', unimplemented_role)
register_canonical_role('uri-reference', unimplemented_role)
register_canonical_role('footnote-reference', unimplemented_role)
register_canonical_role('citation-reference', unimplemented_role)
register_canonical_role('substitution-reference', unimplemented_role)
register_canonical_role('target', unimplemented_role)

# This should remain unimplemented, for testing purposes:
register_canonical_role('restructuredtext-unimplemented-role',
                        unimplemented_role)


def set_classes(options):
    """
    Auxiliary function to set options['classes'] and delete
    options['class'].
    """
    if 'class' in options:
        assert 'classes' not in options
        options['classes'] = options['class']
        del options['class']
