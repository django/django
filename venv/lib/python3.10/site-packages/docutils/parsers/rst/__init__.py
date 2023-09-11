# $Id: __init__.py 9258 2022-11-21 14:51:43Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
This is ``docutils.parsers.rst`` package. It exports a single class, `Parser`,
the reStructuredText parser.


Usage
=====

1. Create a parser::

       parser = docutils.parsers.rst.Parser()

   Several optional arguments may be passed to modify the parser's behavior.
   Please see `Customizing the Parser`_ below for details.

2. Gather input (a multi-line string), by reading a file or the standard
   input::

       input = sys.stdin.read()

3. Create a new empty `docutils.nodes.document` tree::

       document = docutils.utils.new_document(source, settings)

   See `docutils.utils.new_document()` for parameter details.

4. Run the parser, populating the document tree::

       parser.parse(input, document)


Parser Overview
===============

The reStructuredText parser is implemented as a state machine, examining its
input one line at a time. To understand how the parser works, please first
become familiar with the `docutils.statemachine` module, then see the
`states` module.


Customizing the Parser
----------------------

Anything that isn't already customizable is that way simply because that type
of customizability hasn't been implemented yet.  Patches welcome!

When instantiating an object of the `Parser` class, two parameters may be
passed: ``rfc2822`` and ``inliner``.  Pass ``rfc2822=True`` to enable an
initial RFC-2822 style header block, parsed as a "field_list" element (with
"class" attribute set to "rfc2822").  Currently this is the only body-level
element which is customizable without subclassing.  (Tip: subclass `Parser`
and change its "state_classes" and "initial_state" attributes to refer to new
classes. Contact the author if you need more details.)

The ``inliner`` parameter takes an instance of `states.Inliner` or a subclass.
It handles inline markup recognition.  A common extension is the addition of
further implicit hyperlinks, like "RFC 2822".  This can be done by subclassing
`states.Inliner`, adding a new method for the implicit markup, and adding a
``(pattern, method)`` pair to the "implicit_dispatch" attribute of the
subclass.  See `states.Inliner.implicit_inline()` for details.  Explicit
inline markup can be customized in a `states.Inliner` subclass via the
``patterns.initial`` and ``dispatch`` attributes (and new methods as
appropriate).
"""

__docformat__ = 'reStructuredText'


import docutils.parsers
import docutils.statemachine
from docutils.parsers.rst import roles, states
from docutils import frontend, nodes
from docutils.transforms import universal


class Parser(docutils.parsers.Parser):

    """The reStructuredText parser."""

    supported = ('rst', 'restructuredtext', 'rest', 'restx', 'rtxt', 'rstx')
    """Aliases this parser supports."""

    settings_spec = docutils.parsers.Parser.settings_spec + (
        'reStructuredText Parser Options',
        None,
        (('Recognize and link to standalone PEP references (like "PEP 258").',
          ['--pep-references'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         ('Base URL for PEP references '
          '(default "https://peps.python.org/").',
          ['--pep-base-url'],
          {'metavar': '<URL>', 'default': 'https://peps.python.org/',
           'validator': frontend.validate_url_trailing_slash}),
         ('Template for PEP file part of URL. (default "pep-%04d")',
          ['--pep-file-url-template'],
          {'metavar': '<URL>', 'default': 'pep-%04d'}),
         ('Recognize and link to standalone RFC references (like "RFC 822").',
          ['--rfc-references'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         ('Base URL for RFC references '
          '(default "https://tools.ietf.org/html/").',
          ['--rfc-base-url'],
          {'metavar': '<URL>', 'default': 'https://tools.ietf.org/html/',
           'validator': frontend.validate_url_trailing_slash}),
         ('Set number of spaces for tab expansion (default 8).',
          ['--tab-width'],
          {'metavar': '<width>', 'type': 'int', 'default': 8,
           'validator': frontend.validate_nonnegative_int}),
         ('Remove spaces before footnote references.',
          ['--trim-footnote-reference-space'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         ('Leave spaces before footnote references.',
          ['--leave-footnote-reference-space'],
          {'action': 'store_false', 'dest': 'trim_footnote_reference_space'}),
         ('Token name set for parsing code with Pygments: one of '
          '"long", "short", or "none" (no parsing). Default is "long".',
          ['--syntax-highlight'],
          {'choices': ['long', 'short', 'none'],
           'default': 'long', 'metavar': '<format>'}),
         ('Change straight quotation marks to typographic form: '
          'one of "yes", "no", "alt[ernative]" (default "no").',
          ['--smart-quotes'],
          {'default': False, 'metavar': '<yes/no/alt>',
           'validator': frontend.validate_ternary}),
         ('Characters to use as "smart quotes" for <language>. ',
          ['--smartquotes-locales'],
          {'metavar': '<language:quotes[,language:quotes,...]>',
           'action': 'append',
           'validator': frontend.validate_smartquotes_locales}),
         ('Inline markup recognized at word boundaries only '
          '(adjacent to punctuation or whitespace). '
          'Force character-level inline markup recognition with '
          '"\\ " (backslash + space). Default.',
          ['--word-level-inline-markup'],
          {'action': 'store_false', 'dest': 'character_level_inline_markup'}),
         ('Inline markup recognized anywhere, regardless of surrounding '
          'characters. Backslash-escapes must be used to avoid unwanted '
          'markup recognition. Useful for East Asian languages. '
          'Experimental.',
          ['--character-level-inline-markup'],
          {'action': 'store_true', 'default': False,
           'dest': 'character_level_inline_markup'}),
         )
        )

    config_section = 'restructuredtext parser'
    config_section_dependencies = ('parsers',)

    def __init__(self, rfc2822=False, inliner=None):
        if rfc2822:
            self.initial_state = 'RFC2822Body'
        else:
            self.initial_state = 'Body'
        self.state_classes = states.state_classes
        self.inliner = inliner

    def get_transforms(self):
        return super().get_transforms() + [universal.SmartQuotes]

    def parse(self, inputstring, document):
        """Parse `inputstring` and populate `document`, a document tree."""
        self.setup_parse(inputstring, document)
        # provide fallbacks in case the document has only generic settings
        self.document.settings.setdefault('tab_width', 8)
        self.document.settings.setdefault('syntax_highlight', 'long')
        self.statemachine = states.RSTStateMachine(
              state_classes=self.state_classes,
              initial_state=self.initial_state,
              debug=document.reporter.debug_flag)
        inputlines = docutils.statemachine.string2lines(
              inputstring, tab_width=document.settings.tab_width,
              convert_whitespace=True)
        for i, line in enumerate(inputlines):
            if len(line) > self.document.settings.line_length_limit:
                error = self.document.reporter.error(
                            'Line %d exceeds the line-length-limit.'%(i+1))
                self.document.append(error)
                break
        else:
            self.statemachine.run(inputlines, document, inliner=self.inliner)
        # restore the "default" default role after parsing a document
        if '' in roles._roles:
            del roles._roles['']
        self.finish_parse()


class DirectiveError(Exception):

    """
    Store a message and a system message level.

    To be thrown from inside directive code.

    Do not instantiate directly -- use `Directive.directive_error()`
    instead!
    """

    def __init__(self, level, message):
        """Set error `message` and `level`"""
        Exception.__init__(self)
        self.level = level
        self.msg = message


class Directive:

    """
    Base class for reStructuredText directives.

    The following attributes may be set by subclasses.  They are
    interpreted by the directive parser (which runs the directive
    class):

    - `required_arguments`: The number of required arguments (default:
      0).

    - `optional_arguments`: The number of optional arguments (default:
      0).

    - `final_argument_whitespace`: A boolean, indicating if the final
      argument may contain whitespace (default: False).

    - `option_spec`: A dictionary, mapping known option names to
      conversion functions such as `int` or `float` (default: {}, no
      options).  Several conversion functions are defined in the
      directives/__init__.py module.

      Option conversion functions take a single parameter, the option
      argument (a string or ``None``), validate it and/or convert it
      to the appropriate form.  Conversion functions may raise
      `ValueError` and `TypeError` exceptions.

    - `has_content`: A boolean; True if content is allowed.  Client
      code must handle the case where content is required but not
      supplied (an empty content list will be supplied).

    Arguments are normally single whitespace-separated words.  The
    final argument may contain whitespace and/or newlines if
    `final_argument_whitespace` is True.

    If the form of the arguments is more complex, specify only one
    argument (either required or optional) and set
    `final_argument_whitespace` to True; the client code must do any
    context-sensitive parsing.

    When a directive implementation is being run, the directive class
    is instantiated, and the `run()` method is executed.  During
    instantiation, the following instance variables are set:

    - ``name`` is the directive type or name (string).

    - ``arguments`` is the list of positional arguments (strings).

    - ``options`` is a dictionary mapping option names (strings) to
      values (type depends on option conversion functions; see
      `option_spec` above).

    - ``content`` is a list of strings, the directive content line by line.

    - ``lineno`` is the absolute line number of the first line
      of the directive.

    - ``content_offset`` is the line offset of the first line
      of the content from the beginning of the current input.
      Used when initiating a nested parse.

    - ``block_text`` is a string containing the entire directive.

    - ``state`` is the state which called the directive function.

    - ``state_machine`` is the state machine which controls the state
      which called the directive function.

    - ``reporter`` is the state machine's `reporter` instance.

    Directive functions return a list of nodes which will be inserted
    into the document tree at the point where the directive was
    encountered.  This can be an empty list if there is nothing to
    insert.

    For ordinary directives, the list must contain body elements or
    structural elements.  Some directives are intended specifically
    for substitution definitions, and must return a list of `Text`
    nodes and/or inline elements (suitable for inline insertion, in
    place of the substitution reference).  Such directives must verify
    substitution definition context, typically using code like this::

        if not isinstance(state, states.SubstitutionDef):
            error = self.reporter.error(
                'Invalid context: the "%s" directive can only be used '
                'within a substitution definition.' % (name),
                nodes.literal_block(block_text, block_text), line=lineno)
            return [error]
    """

    # There is a "Creating reStructuredText Directives" how-to at
    # <https://docutils.sourceforge.io/docs/howto/rst-directives.html>.  If you
    # update this docstring, please update the how-to as well.

    required_arguments = 0
    """Number of required directive arguments."""

    optional_arguments = 0
    """Number of optional arguments after the required arguments."""

    final_argument_whitespace = False
    """May the final argument contain whitespace?"""

    option_spec = None
    """Mapping of option names to validator functions."""

    has_content = False
    """May the directive have content?"""

    def __init__(self, name, arguments, options, content, lineno,
                 content_offset, block_text, state, state_machine):
        self.name = name
        self.arguments = arguments
        self.options = options
        self.content = content
        self.lineno = lineno
        self.content_offset = content_offset
        self.block_text = block_text
        self.state = state
        self.state_machine = state_machine
        self.reporter = state_machine.reporter

    def run(self):
        raise NotImplementedError('Must override run() in subclass.')

    # Directive errors:

    def directive_error(self, level, message):
        """
        Return a DirectiveError suitable for being thrown as an exception.

        Call "raise self.directive_error(level, message)" from within
        a directive implementation to return one single system message
        at level `level`, which automatically gets the directive block
        and the line number added.

        Preferably use the `debug`, `info`, `warning`, `error`, or `severe`
        wrapper methods, e.g. ``self.error(message)`` to generate an
        ERROR-level directive error.
        """
        return DirectiveError(level, message)

    def debug(self, message):
        return self.directive_error(0, message)

    def info(self, message):
        return self.directive_error(1, message)

    def warning(self, message):
        return self.directive_error(2, message)

    def error(self, message):
        return self.directive_error(3, message)

    def severe(self, message):
        return self.directive_error(4, message)

    # Convenience methods:

    def assert_has_content(self):
        """
        Throw an ERROR-level DirectiveError if the directive doesn't
        have contents.
        """
        if not self.content:
            raise self.error('Content block expected for the "%s" directive; '
                             'none found.' % self.name)

    def add_name(self, node):
        """Append self.options['name'] to node['names'] if it exists.

        Also normalize the name string and register it as explicit target.
        """
        if 'name' in self.options:
            name = nodes.fully_normalize_name(self.options.pop('name'))
            if 'name' in node:
                del node['name']
            node['names'].append(name)
            self.state.document.note_explicit_target(node, node)


def convert_directive_function(directive_fn):
    """
    Define & return a directive class generated from `directive_fn`.

    `directive_fn` uses the old-style, functional interface.
    """

    class FunctionalDirective(Directive):

        option_spec = getattr(directive_fn, 'options', None)
        has_content = getattr(directive_fn, 'content', False)
        _argument_spec = getattr(directive_fn, 'arguments', (0, 0, False))
        required_arguments, optional_arguments, final_argument_whitespace \
            = _argument_spec

        def run(self):
            return directive_fn(
                self.name, self.arguments, self.options, self.content,
                self.lineno, self.content_offset, self.block_text,
                self.state, self.state_machine)

    # Return new-style directive.
    return FunctionalDirective
