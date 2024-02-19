# $Id: states.py 9037 2022-03-05 23:31:10Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
This is the ``docutils.parsers.rst.states`` module, the core of
the reStructuredText parser.  It defines the following:

:Classes:
    - `RSTStateMachine`: reStructuredText parser's entry point.
    - `NestedStateMachine`: recursive StateMachine.
    - `RSTState`: reStructuredText State superclass.
    - `Inliner`: For parsing inline markup.
    - `Body`: Generic classifier of the first line of a block.
    - `SpecializedBody`: Superclass for compound element members.
    - `BulletList`: Second and subsequent bullet_list list_items
    - `DefinitionList`: Second+ definition_list_items.
    - `EnumeratedList`: Second+ enumerated_list list_items.
    - `FieldList`: Second+ fields.
    - `OptionList`: Second+ option_list_items.
    - `RFC2822List`: Second+ RFC2822-style fields.
    - `ExtensionOptions`: Parses directive option fields.
    - `Explicit`: Second+ explicit markup constructs.
    - `SubstitutionDef`: For embedded directives in substitution definitions.
    - `Text`: Classifier of second line of a text block.
    - `SpecializedText`: Superclass for continuation lines of Text-variants.
    - `Definition`: Second line of potential definition_list_item.
    - `Line`: Second line of overlined section title or transition marker.
    - `Struct`: An auxiliary collection class.

:Exception classes:
    - `MarkupError`
    - `ParserError`
    - `MarkupMismatch`

:Functions:
    - `escape2null()`: Return a string, escape-backslashes converted to nulls.
    - `unescape()`: Return a string, nulls removed or restored to backslashes.

:Attributes:
    - `state_classes`: set of State classes used with `RSTStateMachine`.

Parser Overview
===============

The reStructuredText parser is implemented as a recursive state machine,
examining its input one line at a time.  To understand how the parser works,
please first become familiar with the `docutils.statemachine` module.  In the
description below, references are made to classes defined in this module;
please see the individual classes for details.

Parsing proceeds as follows:

1. The state machine examines each line of input, checking each of the
   transition patterns of the state `Body`, in order, looking for a match.
   The implicit transitions (blank lines and indentation) are checked before
   any others.  The 'text' transition is a catch-all (matches anything).

2. The method associated with the matched transition pattern is called.

   A. Some transition methods are self-contained, appending elements to the
      document tree (`Body.doctest` parses a doctest block).  The parser's
      current line index is advanced to the end of the element, and parsing
      continues with step 1.

   B. Other transition methods trigger the creation of a nested state machine,
      whose job is to parse a compound construct ('indent' does a block quote,
      'bullet' does a bullet list, 'overline' does a section [first checking
      for a valid section header], etc.).

      - In the case of lists and explicit markup, a one-off state machine is
        created and run to parse contents of the first item.

      - A new state machine is created and its initial state is set to the
        appropriate specialized state (`BulletList` in the case of the
        'bullet' transition; see `SpecializedBody` for more detail).  This
        state machine is run to parse the compound element (or series of
        explicit markup elements), and returns as soon as a non-member element
        is encountered.  For example, the `BulletList` state machine ends as
        soon as it encounters an element which is not a list item of that
        bullet list.  The optional omission of inter-element blank lines is
        enabled by this nested state machine.

      - The current line index is advanced to the end of the elements parsed,
        and parsing continues with step 1.

   C. The result of the 'text' transition depends on the next line of text.
      The current state is changed to `Text`, under which the second line is
      examined.  If the second line is:

      - Indented: The element is a definition list item, and parsing proceeds
        similarly to step 2.B, using the `DefinitionList` state.

      - A line of uniform punctuation characters: The element is a section
        header; again, parsing proceeds as in step 2.B, and `Body` is still
        used.

      - Anything else: The element is a paragraph, which is examined for
        inline markup and appended to the parent element.  Processing
        continues with step 1.
"""

__docformat__ = 'reStructuredText'


import re
from types import FunctionType, MethodType

from docutils import nodes, statemachine, utils
from docutils import ApplicationError, DataError
from docutils.statemachine import StateMachineWS, StateWS
from docutils.nodes import fully_normalize_name as normalize_name
from docutils.nodes import unescape, whitespace_normalize_name
import docutils.parsers.rst
from docutils.parsers.rst import directives, languages, tableparser, roles
from docutils.utils import escape2null, column_width
from docutils.utils import punctuation_chars, roman, urischemes
from docutils.utils import split_escaped_whitespace


class MarkupError(DataError): pass
class UnknownInterpretedRoleError(DataError): pass
class InterpretedRoleNotImplementedError(DataError): pass
class ParserError(ApplicationError): pass
class MarkupMismatch(Exception): pass


class Struct:

    """Stores data attributes for dotted-attribute access."""

    def __init__(self, **keywordargs):
        self.__dict__.update(keywordargs)


class RSTStateMachine(StateMachineWS):

    """
    reStructuredText's master StateMachine.

    The entry point to reStructuredText parsing is the `run()` method.
    """

    def run(self, input_lines, document, input_offset=0, match_titles=True,
            inliner=None):
        """
        Parse `input_lines` and modify the `document` node in place.

        Extend `StateMachineWS.run()`: set up parse-global data and
        run the StateMachine.
        """
        self.language = languages.get_language(
            document.settings.language_code, document.reporter)
        self.match_titles = match_titles
        if inliner is None:
            inliner = Inliner()
        inliner.init_customizations(document.settings)
        self.memo = Struct(document=document,
                           reporter=document.reporter,
                           language=self.language,
                           title_styles=[],
                           section_level=0,
                           section_bubble_up_kludge=False,
                           inliner=inliner)
        self.document = document
        self.attach_observer(document.note_source)
        self.reporter = self.memo.reporter
        self.node = document
        results = StateMachineWS.run(self, input_lines, input_offset,
                                     input_source=document['source'])
        assert results == [], 'RSTStateMachine.run() results should be empty!'
        self.node = self.memo = None    # remove unneeded references


class NestedStateMachine(StateMachineWS):

    """
    StateMachine run from within other StateMachine runs, to parse nested
    document structures.
    """

    def run(self, input_lines, input_offset, memo, node, match_titles=True):
        """
        Parse `input_lines` and populate a `docutils.nodes.document` instance.

        Extend `StateMachineWS.run()`: set up document-wide data.
        """
        self.match_titles = match_titles
        self.memo = memo
        self.document = memo.document
        self.attach_observer(self.document.note_source)
        self.reporter = memo.reporter
        self.language = memo.language
        self.node = node
        results = StateMachineWS.run(self, input_lines, input_offset)
        assert results == [], ('NestedStateMachine.run() results should be '
                               'empty!')
        return results


class RSTState(StateWS):

    """
    reStructuredText State superclass.

    Contains methods used by all State subclasses.
    """

    nested_sm = NestedStateMachine
    nested_sm_cache = []

    def __init__(self, state_machine, debug=False):
        self.nested_sm_kwargs = {'state_classes': state_classes,
                                 'initial_state': 'Body'}
        StateWS.__init__(self, state_machine, debug)

    def runtime_init(self):
        StateWS.runtime_init(self)
        memo = self.state_machine.memo
        self.memo = memo
        self.reporter = memo.reporter
        self.inliner = memo.inliner
        self.document = memo.document
        self.parent = self.state_machine.node
        # enable the reporter to determine source and source-line
        if not hasattr(self.reporter, 'get_source_and_line'):
            self.reporter.get_source_and_line = self.state_machine.get_source_and_line  # noqa:E501

    def goto_line(self, abs_line_offset):
        """
        Jump to input line `abs_line_offset`, ignoring jumps past the end.
        """
        try:
            self.state_machine.goto_line(abs_line_offset)
        except EOFError:
            pass

    def no_match(self, context, transitions):
        """
        Override `StateWS.no_match` to generate a system message.

        This code should never be run.
        """
        self.reporter.severe(
            'Internal error: no transition pattern match.  State: "%s"; '
            'transitions: %s; context: %s; current line: %r.'
            % (self.__class__.__name__, transitions, context,
               self.state_machine.line))
        return context, None, []

    def bof(self, context):
        """Called at beginning of file."""
        return [], []

    def nested_parse(self, block, input_offset, node, match_titles=False,
                     state_machine_class=None, state_machine_kwargs=None):
        """
        Create a new StateMachine rooted at `node` and run it over the input
        `block`.
        """
        use_default = 0
        if state_machine_class is None:
            state_machine_class = self.nested_sm
            use_default += 1
        if state_machine_kwargs is None:
            state_machine_kwargs = self.nested_sm_kwargs
            use_default += 1
        block_length = len(block)

        state_machine = None
        if use_default == 2:
            try:
                state_machine = self.nested_sm_cache.pop()
            except IndexError:
                pass
        if not state_machine:
            state_machine = state_machine_class(debug=self.debug,
                                                **state_machine_kwargs)
        state_machine.run(block, input_offset, memo=self.memo,
                          node=node, match_titles=match_titles)
        if use_default == 2:
            self.nested_sm_cache.append(state_machine)
        else:
            state_machine.unlink()
        new_offset = state_machine.abs_line_offset()
        # No `block.parent` implies disconnected -- lines aren't in sync:
        if block.parent and (len(block) - block_length) != 0:
            # Adjustment for block if modified in nested parse:
            self.state_machine.next_line(len(block) - block_length)
        return new_offset

    def nested_list_parse(self, block, input_offset, node, initial_state,
                          blank_finish,
                          blank_finish_state=None,
                          extra_settings={},
                          match_titles=False,
                          state_machine_class=None,
                          state_machine_kwargs=None):
        """
        Create a new StateMachine rooted at `node` and run it over the input
        `block`. Also keep track of optional intermediate blank lines and the
        required final one.
        """
        if state_machine_class is None:
            state_machine_class = self.nested_sm
        if state_machine_kwargs is None:
            state_machine_kwargs = self.nested_sm_kwargs.copy()
        state_machine_kwargs['initial_state'] = initial_state
        state_machine = state_machine_class(debug=self.debug,
                                            **state_machine_kwargs)
        if blank_finish_state is None:
            blank_finish_state = initial_state
        state_machine.states[blank_finish_state].blank_finish = blank_finish
        for key, value in extra_settings.items():
            setattr(state_machine.states[initial_state], key, value)
        state_machine.run(block, input_offset, memo=self.memo,
                          node=node, match_titles=match_titles)
        blank_finish = state_machine.states[blank_finish_state].blank_finish
        state_machine.unlink()
        return state_machine.abs_line_offset(), blank_finish

    def section(self, title, source, style, lineno, messages):
        """Check for a valid subsection and create one if it checks out."""
        if self.check_subsection(source, style, lineno):
            self.new_subsection(title, lineno, messages)

    def check_subsection(self, source, style, lineno):
        """
        Check for a valid subsection header.  Return True or False.

        When a new section is reached that isn't a subsection of the current
        section, back up the line count (use ``previous_line(-x)``), then
        ``raise EOFError``.  The current StateMachine will finish, then the
        calling StateMachine can re-examine the title.  This will work its way
        back up the calling chain until the correct section level isreached.

        @@@ Alternative: Evaluate the title, store the title info & level, and
        back up the chain until that level is reached.  Store in memo? Or
        return in results?

        :Exception: `EOFError` when a sibling or supersection encountered.
        """
        memo = self.memo
        title_styles = memo.title_styles
        mylevel = memo.section_level
        try:                            # check for existing title style
            level = title_styles.index(style) + 1
        except ValueError:              # new title style
            if len(title_styles) == memo.section_level:  # new subsection
                title_styles.append(style)
                return True
            else:                       # not at lowest level
                self.parent += self.title_inconsistent(source, lineno)
                return False
        if level <= mylevel:            # sibling or supersection
            memo.section_level = level   # bubble up to parent section
            if len(style) == 2:
                memo.section_bubble_up_kludge = True
            # back up 2 lines for underline title, 3 for overline title
            self.state_machine.previous_line(len(style) + 1)
            raise EOFError              # let parent section re-evaluate
        if level == mylevel + 1:        # immediate subsection
            return True
        else:                           # invalid subsection
            self.parent += self.title_inconsistent(source, lineno)
            return False

    def title_inconsistent(self, sourcetext, lineno):
        error = self.reporter.severe(
            'Title level inconsistent:', nodes.literal_block('', sourcetext),
            line=lineno)
        return error

    def new_subsection(self, title, lineno, messages):
        """Append new subsection to document tree. On return, check level."""
        memo = self.memo
        mylevel = memo.section_level
        memo.section_level += 1
        section_node = nodes.section()
        self.parent += section_node
        textnodes, title_messages = self.inline_text(title, lineno)
        titlenode = nodes.title(title, '', *textnodes)
        name = normalize_name(titlenode.astext())
        section_node['names'].append(name)
        section_node += titlenode
        section_node += messages
        section_node += title_messages
        self.document.note_implicit_target(section_node, section_node)
        offset = self.state_machine.line_offset + 1
        absoffset = self.state_machine.abs_line_offset() + 1
        newabsoffset = self.nested_parse(
              self.state_machine.input_lines[offset:], input_offset=absoffset,
              node=section_node, match_titles=True)
        self.goto_line(newabsoffset)
        if memo.section_level <= mylevel:  # can't handle next section?
            raise EOFError                 # bubble up to supersection
        # reset section_level; next pass will detect it properly
        memo.section_level = mylevel

    def paragraph(self, lines, lineno):
        """
        Return a list (paragraph & messages) & a boolean: literal_block next?
        """
        data = '\n'.join(lines).rstrip()
        if re.search(r'(?<!\\)(\\\\)*::$', data):
            if len(data) == 2:
                return [], 1
            elif data[-3] in ' \n':
                text = data[:-3].rstrip()
            else:
                text = data[:-1]
            literalnext = 1
        else:
            text = data
            literalnext = 0
        textnodes, messages = self.inline_text(text, lineno)
        p = nodes.paragraph(data, '', *textnodes)
        p.source, p.line = self.state_machine.get_source_and_line(lineno)
        return [p] + messages, literalnext

    def inline_text(self, text, lineno):
        """
        Return 2 lists: nodes (text and inline elements), and system_messages.
        """
        nodes, messages = self.inliner.parse(text, lineno,
                                             self.memo, self.parent)
        return nodes, messages

    def unindent_warning(self, node_name):
        # the actual problem is one line below the current line
        lineno = self.state_machine.abs_line_number() + 1
        return self.reporter.warning('%s ends without a blank line; '
                                     'unexpected unindent.' % node_name,
                                     line=lineno)


def build_regexp(definition, compile=True):
    """
    Build, compile and return a regular expression based on `definition`.

    :Parameter: `definition`: a 4-tuple (group name, prefix, suffix, parts),
        where "parts" is a list of regular expressions and/or regular
        expression definitions to be joined into an or-group.
    """
    name, prefix, suffix, parts = definition
    part_strings = []
    for part in parts:
        if isinstance(part, tuple):
            part_strings.append(build_regexp(part, None))
        else:
            part_strings.append(part)
    or_group = '|'.join(part_strings)
    regexp = '%(prefix)s(?P<%(name)s>%(or_group)s)%(suffix)s' % locals()
    if compile:
        return re.compile(regexp)
    else:
        return regexp


class Inliner:

    """
    Parse inline markup; call the `parse()` method.
    """

    def __init__(self):
        self.implicit_dispatch = []
        """List of (pattern, bound method) tuples, used by
        `self.implicit_inline`."""

    def init_customizations(self, settings):
        # lookahead and look-behind expressions for inline markup rules
        if getattr(settings, 'character_level_inline_markup', False):
            start_string_prefix = '(^|(?<!\x00))'
            end_string_suffix = ''
        else:
            start_string_prefix = ('(^|(?<=\\s|[%s%s]))' %
                                   (punctuation_chars.openers,
                                    punctuation_chars.delimiters))
            end_string_suffix = ('($|(?=\\s|[\x00%s%s%s]))' %
                                 (punctuation_chars.closing_delimiters,
                                  punctuation_chars.delimiters,
                                  punctuation_chars.closers))
        args = locals().copy()
        args.update(vars(self.__class__))

        parts = ('initial_inline', start_string_prefix, '',
           [
            ('start', '', self.non_whitespace_after,  # simple start-strings
             [r'\*\*',                # strong
              r'\*(?!\*)',            # emphasis but not strong
              r'``',                  # literal
              r'_`',                  # inline internal target
              r'\|(?!\|)']            # substitution reference
             ),
            ('whole', '', end_string_suffix,  # whole constructs
             [  # reference name & end-string
              r'(?P<refname>%s)(?P<refend>__?)' % self.simplename,
              ('footnotelabel', r'\[', r'(?P<fnend>\]_)',
               [r'[0-9]+',                     # manually numbered
                r'\#(%s)?' % self.simplename,  # auto-numbered (w/ label?)
                r'\*',                         # auto-symbol
                r'(?P<citationlabel>%s)' % self.simplename,  # citation ref
                ]
               )
              ]
             ),
            ('backquote',             # interpreted text or phrase reference
             '(?P<role>(:%s:)?)' % self.simplename,  # optional role
             self.non_whitespace_after,
             ['`(?!`)']               # but not literal
             )
            ]
        )
        self.start_string_prefix = start_string_prefix
        self.end_string_suffix = end_string_suffix
        self.parts = parts

        self.patterns = Struct(
          initial=build_regexp(parts),
          emphasis=re.compile(self.non_whitespace_escape_before
                              + r'(\*)' + end_string_suffix),
          strong=re.compile(self.non_whitespace_escape_before
                            + r'(\*\*)' + end_string_suffix),
          interpreted_or_phrase_ref=re.compile(
              r"""
              %(non_unescaped_whitespace_escape_before)s
              (
                `
                (?P<suffix>
                  (?P<role>:%(simplename)s:)?
                  (?P<refend>__?)?
                )
              )
              %(end_string_suffix)s
              """ % args, re.VERBOSE),
          embedded_link=re.compile(
              r"""
              (
                (?:[ \n]+|^)            # spaces or beginning of line/string
                <                       # open bracket
                %(non_whitespace_after)s
                (([^<>]|\x00[<>])+)     # anything but unescaped angle brackets
                %(non_whitespace_escape_before)s
                >                       # close bracket
              )
              $                         # end of string
              """ % args, re.VERBOSE),
          literal=re.compile(self.non_whitespace_before + '(``)'
                             + end_string_suffix),
          target=re.compile(self.non_whitespace_escape_before
                            + r'(`)' + end_string_suffix),
          substitution_ref=re.compile(self.non_whitespace_escape_before
                                      + r'(\|_{0,2})'
                                      + end_string_suffix),
          email=re.compile(self.email_pattern % args + '$',
                           re.VERBOSE),
          uri=re.compile(
                (r"""
                %(start_string_prefix)s
                (?P<whole>
                  (?P<absolute>           # absolute URI
                    (?P<scheme>             # scheme (http, ftp, mailto)
                      [a-zA-Z][a-zA-Z0-9.+-]*
                    )
                    :
                    (
                      (                       # either:
                        (//?)?                  # hierarchical URI
                        %(uric)s*               # URI characters
                        %(uri_end)s             # final URI char
                      )
                      (                       # optional query
                        \?%(uric)s*
                        %(uri_end)s
                      )?
                      (                       # optional fragment
                        \#%(uric)s*
                        %(uri_end)s
                      )?
                    )
                  )
                |                       # *OR*
                  (?P<email>              # email address
                    """ + self.email_pattern + r"""
                  )
                )
                %(end_string_suffix)s
                """) % args, re.VERBOSE),
          pep=re.compile(
                r"""
                %(start_string_prefix)s
                (
                  (pep-(?P<pepnum1>\d+)(.txt)?) # reference to source file
                |
                  (PEP\s+(?P<pepnum2>\d+))      # reference by name
                )
                %(end_string_suffix)s""" % args, re.VERBOSE),
          rfc=re.compile(
                r"""
                %(start_string_prefix)s
                (RFC(-|\s+)?(?P<rfcnum>\d+))
                %(end_string_suffix)s""" % args, re.VERBOSE))

        self.implicit_dispatch.append((self.patterns.uri,
                                       self.standalone_uri))
        if settings.pep_references:
            self.implicit_dispatch.append((self.patterns.pep,
                                           self.pep_reference))
        if settings.rfc_references:
            self.implicit_dispatch.append((self.patterns.rfc,
                                           self.rfc_reference))

    def parse(self, text, lineno, memo, parent):
        # Needs to be refactored for nested inline markup.
        # Add nested_parse() method?
        """
        Return 2 lists: nodes (text and inline elements), and system_messages.

        Using `self.patterns.initial`, a pattern which matches start-strings
        (emphasis, strong, interpreted, phrase reference, literal,
        substitution reference, and inline target) and complete constructs
        (simple reference, footnote reference), search for a candidate.  When
        one is found, check for validity (e.g., not a quoted '*' character).
        If valid, search for the corresponding end string if applicable, and
        check it for validity.  If not found or invalid, generate a warning
        and ignore the start-string.  Implicit inline markup (e.g. standalone
        URIs) is found last.

        :text: source string
        :lineno: absolute line number (cf. statemachine.get_source_and_line())
        """
        self.reporter = memo.reporter
        self.document = memo.document
        self.language = memo.language
        self.parent = parent
        pattern_search = self.patterns.initial.search
        dispatch = self.dispatch
        remaining = escape2null(text)
        processed = []
        unprocessed = []
        messages = []
        while remaining:
            match = pattern_search(remaining)
            if match:
                groups = match.groupdict()
                method = dispatch[groups['start'] or groups['backquote']
                                  or groups['refend'] or groups['fnend']]
                before, inlines, remaining, sysmessages = method(self, match,
                                                                 lineno)
                unprocessed.append(before)
                messages += sysmessages
                if inlines:
                    processed += self.implicit_inline(''.join(unprocessed),
                                                      lineno)
                    processed += inlines
                    unprocessed = []
            else:
                break
        remaining = ''.join(unprocessed) + remaining
        if remaining:
            processed += self.implicit_inline(remaining, lineno)
        return processed, messages

    # Inline object recognition
    # -------------------------
    # See also init_customizations().
    non_whitespace_before = r'(?<!\s)'
    non_whitespace_escape_before = r'(?<![\s\x00])'
    non_unescaped_whitespace_escape_before = r'(?<!(?<!\x00)[\s\x00])'
    non_whitespace_after = r'(?!\s)'
    # Alphanumerics with isolated internal [-._+:] chars (i.e. not 2 together):
    simplename = r'(?:(?!_)\w)+(?:[-._+:](?:(?!_)\w)+)*'
    # Valid URI characters (see RFC 2396 & RFC 2732);
    # final \x00 allows backslash escapes in URIs:
    uric = r"""[-_.!~*'()[\];/:@&=+$,%a-zA-Z0-9\x00]"""
    # Delimiter indicating the end of a URI (not part of the URI):
    uri_end_delim = r"""[>]"""
    # Last URI character; same as uric but no punctuation:
    urilast = r"""[_~*/=+a-zA-Z0-9]"""
    # End of a URI (either 'urilast' or 'uric followed by a
    # uri_end_delim'):
    uri_end = r"""(?:%(urilast)s|%(uric)s(?=%(uri_end_delim)s))""" % locals()
    emailc = r"""[-_!~*'{|}/#?^`&=+$%a-zA-Z0-9\x00]"""
    email_pattern = r"""
          %(emailc)s+(?:\.%(emailc)s+)*   # name
          (?<!\x00)@                      # at
          %(emailc)s+(?:\.%(emailc)s*)*   # host
          %(uri_end)s                     # final URI char
          """

    def quoted_start(self, match):
        """Test if inline markup start-string is 'quoted'.

        'Quoted' in this context means the start-string is enclosed in a pair
        of matching opening/closing delimiters (not necessarily quotes)
        or at the end of the match.
        """
        string = match.string
        start = match.start()
        if start == 0:                  # start-string at beginning of text
            return False
        prestart = string[start - 1]
        try:
            poststart = string[match.end()]
        except IndexError:          # start-string at end of text
            return True  # not "quoted" but no markup start-string either
        return punctuation_chars.match_chars(prestart, poststart)

    def inline_obj(self, match, lineno, end_pattern, nodeclass,
                   restore_backslashes=False):
        string = match.string
        matchstart = match.start('start')
        matchend = match.end('start')
        if self.quoted_start(match):
            return string[:matchend], [], string[matchend:], [], ''
        endmatch = end_pattern.search(string[matchend:])
        if endmatch and endmatch.start(1):  # 1 or more chars
            text = endmatch.string[:endmatch.start(1)]
            if restore_backslashes:
                text = unescape(text, True)
            textend = matchend + endmatch.end(1)
            rawsource = unescape(string[matchstart:textend], True)
            node = nodeclass(rawsource, text)
            return (string[:matchstart], [node],
                    string[textend:], [], endmatch.group(1))
        msg = self.reporter.warning(
              'Inline %s start-string without end-string.'
              % nodeclass.__name__, line=lineno)
        text = unescape(string[matchstart:matchend], True)
        prb = self.problematic(text, text, msg)
        return string[:matchstart], [prb], string[matchend:], [msg], ''

    def problematic(self, text, rawsource, message):
        msgid = self.document.set_id(message, self.parent)
        problematic = nodes.problematic(rawsource, text, refid=msgid)
        prbid = self.document.set_id(problematic)
        message.add_backref(prbid)
        return problematic

    def emphasis(self, match, lineno):
        before, inlines, remaining, sysmessages, endstring = self.inline_obj(
              match, lineno, self.patterns.emphasis, nodes.emphasis)
        return before, inlines, remaining, sysmessages

    def strong(self, match, lineno):
        before, inlines, remaining, sysmessages, endstring = self.inline_obj(
              match, lineno, self.patterns.strong, nodes.strong)
        return before, inlines, remaining, sysmessages

    def interpreted_or_phrase_ref(self, match, lineno):
        end_pattern = self.patterns.interpreted_or_phrase_ref
        string = match.string
        matchstart = match.start('backquote')
        matchend = match.end('backquote')
        rolestart = match.start('role')
        role = match.group('role')
        position = ''
        if role:
            role = role[1:-1]
            position = 'prefix'
        elif self.quoted_start(match):
            return string[:matchend], [], string[matchend:], []
        endmatch = end_pattern.search(string[matchend:])
        if endmatch and endmatch.start(1):  # 1 or more chars
            textend = matchend + endmatch.end()
            if endmatch.group('role'):
                if role:
                    msg = self.reporter.warning(
                        'Multiple roles in interpreted text (both '
                        'prefix and suffix present; only one allowed).',
                        line=lineno)
                    text = unescape(string[rolestart:textend], True)
                    prb = self.problematic(text, text, msg)
                    return string[:rolestart], [prb], string[textend:], [msg]
                role = endmatch.group('suffix')[1:-1]
                position = 'suffix'
            escaped = endmatch.string[:endmatch.start(1)]
            rawsource = unescape(string[matchstart:textend], True)
            if rawsource[-1:] == '_':
                if role:
                    msg = self.reporter.warning(
                          'Mismatch: both interpreted text role %s and '
                          'reference suffix.' % position, line=lineno)
                    text = unescape(string[rolestart:textend], True)
                    prb = self.problematic(text, text, msg)
                    return string[:rolestart], [prb], string[textend:], [msg]
                return self.phrase_ref(string[:matchstart], string[textend:],
                                       rawsource, escaped)
            else:
                rawsource = unescape(string[rolestart:textend], True)
                nodelist, messages = self.interpreted(rawsource, escaped, role,
                                                      lineno)
                return (string[:rolestart], nodelist,
                        string[textend:], messages)
        msg = self.reporter.warning(
              'Inline interpreted text or phrase reference start-string '
              'without end-string.', line=lineno)
        text = unescape(string[matchstart:matchend], True)
        prb = self.problematic(text, text, msg)
        return string[:matchstart], [prb], string[matchend:], [msg]

    def phrase_ref(self, before, after, rawsource, escaped, text=None):
        # `text` is ignored (since 0.16)
        match = self.patterns.embedded_link.search(escaped)
        if match:  # embedded <URI> or <alias_>
            text = escaped[:match.start(0)]
            unescaped = unescape(text)
            rawtext = unescape(text, True)
            aliastext = match.group(2)
            rawaliastext = unescape(aliastext, True)
            underscore_escaped = rawaliastext.endswith(r'\_')
            if (aliastext.endswith('_')
                and not (underscore_escaped
                         or self.patterns.uri.match(aliastext))):
                aliastype = 'name'
                alias = normalize_name(unescape(aliastext[:-1]))
                target = nodes.target(match.group(1), refname=alias)
                target.indirect_reference_name = whitespace_normalize_name(
                                                    unescape(aliastext[:-1]))
            else:
                aliastype = 'uri'
                # remove unescaped whitespace
                alias_parts = split_escaped_whitespace(match.group(2))
                alias = ' '.join(''.join(part.split())
                                 for part in alias_parts)
                alias = self.adjust_uri(unescape(alias))
                if alias.endswith(r'\_'):
                    alias = alias[:-2] + '_'
                target = nodes.target(match.group(1), refuri=alias)
                target.referenced = 1
            if not aliastext:
                raise ApplicationError('problem with embedded link: %r'
                                       % aliastext)
            if not text:
                text = alias
                unescaped = unescape(text)
                rawtext = rawaliastext
        else:
            text = escaped
            unescaped = unescape(text)
            target = None
            rawtext = unescape(escaped, True)

        refname = normalize_name(unescaped)
        reference = nodes.reference(rawsource, text,
                                    name=whitespace_normalize_name(unescaped))
        reference[0].rawsource = rawtext

        node_list = [reference]

        if rawsource[-2:] == '__':
            if target and (aliastype == 'name'):
                reference['refname'] = alias
                self.document.note_refname(reference)
                # self.document.note_indirect_target(target) # required?
            elif target and (aliastype == 'uri'):
                reference['refuri'] = alias
            else:
                reference['anonymous'] = 1
        else:
            if target:
                target['names'].append(refname)
                if aliastype == 'name':
                    reference['refname'] = alias
                    self.document.note_indirect_target(target)
                    self.document.note_refname(reference)
                else:
                    reference['refuri'] = alias
                    self.document.note_explicit_target(target, self.parent)
                # target.note_referenced_by(name=refname)
                node_list.append(target)
            else:
                reference['refname'] = refname
                self.document.note_refname(reference)
        return before, node_list, after, []

    def adjust_uri(self, uri):
        match = self.patterns.email.match(uri)
        if match:
            return 'mailto:' + uri
        else:
            return uri

    def interpreted(self, rawsource, text, role, lineno):
        role_fn, messages = roles.role(role, self.language, lineno,
                                       self.reporter)
        if role_fn:
            nodes, messages2 = role_fn(role, rawsource, text, lineno, self)
            return nodes, messages + messages2
        else:
            msg = self.reporter.error(
                'Unknown interpreted text role "%s".' % role,
                line=lineno)
            return ([self.problematic(rawsource, rawsource, msg)],
                    messages + [msg])

    def literal(self, match, lineno):
        before, inlines, remaining, sysmessages, endstring = self.inline_obj(
              match, lineno, self.patterns.literal, nodes.literal,
              restore_backslashes=True)
        return before, inlines, remaining, sysmessages

    def inline_internal_target(self, match, lineno):
        before, inlines, remaining, sysmessages, endstring = self.inline_obj(
              match, lineno, self.patterns.target, nodes.target)
        if inlines and isinstance(inlines[0], nodes.target):
            assert len(inlines) == 1
            target = inlines[0]
            name = normalize_name(target.astext())
            target['names'].append(name)
            self.document.note_explicit_target(target, self.parent)
        return before, inlines, remaining, sysmessages

    def substitution_reference(self, match, lineno):
        before, inlines, remaining, sysmessages, endstring = self.inline_obj(
              match, lineno, self.patterns.substitution_ref,
              nodes.substitution_reference)
        if len(inlines) == 1:
            subref_node = inlines[0]
            if isinstance(subref_node, nodes.substitution_reference):
                subref_text = subref_node.astext()
                self.document.note_substitution_ref(subref_node, subref_text)
                if endstring[-1:] == '_':
                    reference_node = nodes.reference(
                        '|%s%s' % (subref_text, endstring), '')
                    if endstring[-2:] == '__':
                        reference_node['anonymous'] = 1
                    else:
                        reference_node['refname'] = normalize_name(subref_text)
                        self.document.note_refname(reference_node)
                    reference_node += subref_node
                    inlines = [reference_node]
        return before, inlines, remaining, sysmessages

    def footnote_reference(self, match, lineno):
        """
        Handles `nodes.footnote_reference` and `nodes.citation_reference`
        elements.
        """
        label = match.group('footnotelabel')
        refname = normalize_name(label)
        string = match.string
        before = string[:match.start('whole')]
        remaining = string[match.end('whole'):]
        if match.group('citationlabel'):
            refnode = nodes.citation_reference('[%s]_' % label,
                                               refname=refname)
            refnode += nodes.Text(label)
            self.document.note_citation_ref(refnode)
        else:
            refnode = nodes.footnote_reference('[%s]_' % label)
            if refname[0] == '#':
                refname = refname[1:]
                refnode['auto'] = 1
                self.document.note_autofootnote_ref(refnode)
            elif refname == '*':
                refname = ''
                refnode['auto'] = '*'
                self.document.note_symbol_footnote_ref(
                      refnode)
            else:
                refnode += nodes.Text(label)
            if refname:
                refnode['refname'] = refname
                self.document.note_footnote_ref(refnode)
            if utils.get_trim_footnote_ref_space(self.document.settings):
                before = before.rstrip()
        return before, [refnode], remaining, []

    def reference(self, match, lineno, anonymous=False):
        referencename = match.group('refname')
        refname = normalize_name(referencename)
        referencenode = nodes.reference(
            referencename + match.group('refend'), referencename,
            name=whitespace_normalize_name(referencename))
        referencenode[0].rawsource = referencename
        if anonymous:
            referencenode['anonymous'] = 1
        else:
            referencenode['refname'] = refname
            self.document.note_refname(referencenode)
        string = match.string
        matchstart = match.start('whole')
        matchend = match.end('whole')
        return string[:matchstart], [referencenode], string[matchend:], []

    def anonymous_reference(self, match, lineno):
        return self.reference(match, lineno, anonymous=True)

    def standalone_uri(self, match, lineno):
        if (not match.group('scheme')
                or match.group('scheme').lower() in urischemes.schemes):
            if match.group('email'):
                addscheme = 'mailto:'
            else:
                addscheme = ''
            text = match.group('whole')
            refuri = addscheme + unescape(text)
            reference = nodes.reference(unescape(text, True), text,
                                        refuri=refuri)
            return [reference]
        else:                   # not a valid scheme
            raise MarkupMismatch

    def pep_reference(self, match, lineno):
        text = match.group(0)
        if text.startswith('pep-'):
            pepnum = int(unescape(match.group('pepnum1')))
        elif text.startswith('PEP'):
            pepnum = int(unescape(match.group('pepnum2')))
        else:
            raise MarkupMismatch
        ref = (self.document.settings.pep_base_url
               + self.document.settings.pep_file_url_template % pepnum)
        return [nodes.reference(unescape(text, True), text, refuri=ref)]

    rfc_url = 'rfc%d.html'

    def rfc_reference(self, match, lineno):
        text = match.group(0)
        if text.startswith('RFC'):
            rfcnum = int(unescape(match.group('rfcnum')))
            ref = self.document.settings.rfc_base_url + self.rfc_url % rfcnum
        else:
            raise MarkupMismatch
        return [nodes.reference(unescape(text, True), text, refuri=ref)]

    def implicit_inline(self, text, lineno):
        """
        Check each of the patterns in `self.implicit_dispatch` for a match,
        and dispatch to the stored method for the pattern.  Recursively check
        the text before and after the match.  Return a list of `nodes.Text`
        and inline element nodes.
        """
        if not text:
            return []
        for pattern, method in self.implicit_dispatch:
            match = pattern.search(text)
            if match:
                try:
                    # Must recurse on strings before *and* after the match;
                    # there may be multiple patterns.
                    return (self.implicit_inline(text[:match.start()], lineno)
                            + method(match, lineno)
                            + self.implicit_inline(text[match.end():], lineno))
                except MarkupMismatch:
                    pass
        return [nodes.Text(text)]

    dispatch = {'*': emphasis,
                '**': strong,
                '`': interpreted_or_phrase_ref,
                '``': literal,
                '_`': inline_internal_target,
                ']_': footnote_reference,
                '|': substitution_reference,
                '_': reference,
                '__': anonymous_reference}


def _loweralpha_to_int(s, _zero=(ord('a')-1)):
    return ord(s) - _zero


def _upperalpha_to_int(s, _zero=(ord('A')-1)):
    return ord(s) - _zero


def _lowerroman_to_int(s):
    return roman.fromRoman(s.upper())


class Body(RSTState):

    """
    Generic classifier of the first line of a block.
    """

    double_width_pad_char = tableparser.TableParser.double_width_pad_char
    """Padding character for East Asian double-width text."""

    enum = Struct()
    """Enumerated list parsing information."""

    enum.formatinfo = {
          'parens': Struct(prefix='(', suffix=')', start=1, end=-1),
          'rparen': Struct(prefix='', suffix=')', start=0, end=-1),
          'period': Struct(prefix='', suffix='.', start=0, end=-1)}
    enum.formats = enum.formatinfo.keys()
    enum.sequences = ['arabic', 'loweralpha', 'upperalpha',
                      'lowerroman', 'upperroman']  # ORDERED!
    enum.sequencepats = {'arabic': '[0-9]+',
                         'loweralpha': '[a-z]',
                         'upperalpha': '[A-Z]',
                         'lowerroman': '[ivxlcdm]+',
                         'upperroman': '[IVXLCDM]+'}
    enum.converters = {'arabic': int,
                       'loweralpha': _loweralpha_to_int,
                       'upperalpha': _upperalpha_to_int,
                       'lowerroman': _lowerroman_to_int,
                       'upperroman': roman.fromRoman}

    enum.sequenceregexps = {}
    for sequence in enum.sequences:
        enum.sequenceregexps[sequence] = re.compile(
              enum.sequencepats[sequence] + '$')

    grid_table_top_pat = re.compile(r'\+-[-+]+-\+ *$')
    """Matches the top (& bottom) of a full table)."""

    simple_table_top_pat = re.compile('=+( +=+)+ *$')
    """Matches the top of a simple table."""

    simple_table_border_pat = re.compile('=+[ =]*$')
    """Matches the bottom & header bottom of a simple table."""

    pats = {}
    """Fragments of patterns used by transitions."""

    pats['nonalphanum7bit'] = '[!-/:-@[-`{-~]'
    pats['alpha'] = '[a-zA-Z]'
    pats['alphanum'] = '[a-zA-Z0-9]'
    pats['alphanumplus'] = '[a-zA-Z0-9_-]'
    pats['enum'] = ('(%(arabic)s|%(loweralpha)s|%(upperalpha)s|%(lowerroman)s'
                    '|%(upperroman)s|#)' % enum.sequencepats)
    pats['optname'] = '%(alphanum)s%(alphanumplus)s*' % pats
    # @@@ Loosen up the pattern?  Allow Unicode?
    pats['optarg'] = '(%(alpha)s%(alphanumplus)s*|<[^<>]+>)' % pats
    pats['shortopt'] = r'(-|\+)%(alphanum)s( ?%(optarg)s)?' % pats
    pats['longopt'] = r'(--|/)%(optname)s([ =]%(optarg)s)?' % pats
    pats['option'] = r'(%(shortopt)s|%(longopt)s)' % pats

    for format in enum.formats:
        pats[format] = '(?P<%s>%s%s%s)' % (
              format, re.escape(enum.formatinfo[format].prefix),
              pats['enum'], re.escape(enum.formatinfo[format].suffix))

    patterns = {
          'bullet': '[-+*\u2022\u2023\u2043]( +|$)',
          'enumerator': r'(%(parens)s|%(rparen)s|%(period)s)( +|$)' % pats,
          'field_marker': r':(?![: ])([^:\\]|\\.|:(?!([ `]|$)))*(?<! ):( +|$)',
          'option_marker': r'%(option)s(, %(option)s)*(  +| ?$)' % pats,
          'doctest': r'>>>( +|$)',
          'line_block': r'\|( +|$)',
          'grid_table_top': grid_table_top_pat,
          'simple_table_top': simple_table_top_pat,
          'explicit_markup': r'\.\.( +|$)',
          'anonymous': r'__( +|$)',
          'line': r'(%(nonalphanum7bit)s)\1* *$' % pats,
          'text': r''}
    initial_transitions = (
          'bullet',
          'enumerator',
          'field_marker',
          'option_marker',
          'doctest',
          'line_block',
          'grid_table_top',
          'simple_table_top',
          'explicit_markup',
          'anonymous',
          'line',
          'text')

    def indent(self, match, context, next_state):
        """Block quote."""
        (indented, indent, line_offset, blank_finish
         ) = self.state_machine.get_indented()
        elements = self.block_quote(indented, line_offset)
        self.parent += elements
        if not blank_finish:
            self.parent += self.unindent_warning('Block quote')
        return context, next_state, []

    def block_quote(self, indented, line_offset):
        elements = []
        while indented:
            blockquote = nodes.block_quote(rawsource='\n'.join(indented))
            (blockquote.source, blockquote.line
             ) = self.state_machine.get_source_and_line(line_offset+1)
            (blockquote_lines,
             attribution_lines,
             attribution_offset,
             indented,
             new_line_offset) = self.split_attribution(indented, line_offset)
            self.nested_parse(blockquote_lines, line_offset, blockquote)
            elements.append(blockquote)
            if attribution_lines:
                attribution, messages = self.parse_attribution(
                    attribution_lines, line_offset+attribution_offset)
                blockquote += attribution
                elements += messages
            line_offset = new_line_offset
            while indented and not indented[0]:
                indented = indented[1:]
                line_offset += 1
        return elements

    # U+2014 is an em-dash:
    attribution_pattern = re.compile('(---?(?!-)|\u2014) *(?=[^ \\n])')

    def split_attribution(self, indented, line_offset):
        """
        Check for a block quote attribution and split it off:

        * First line after a blank line must begin with a dash ("--", "---",
          em-dash; matches `self.attribution_pattern`).
        * Every line after that must have consistent indentation.
        * Attributions must be preceded by block quote content.

        Return a tuple of: (block quote content lines, attribution lines,
        attribution offset, remaining indented lines, remaining lines offset).
        """
        blank = None
        nonblank_seen = False
        for i in range(len(indented)):
            line = indented[i].rstrip()
            if line:
                if nonblank_seen and blank == i - 1:  # last line blank
                    match = self.attribution_pattern.match(line)
                    if match:
                        attribution_end, indent = self.check_attribution(
                            indented, i)
                        if attribution_end:
                            a_lines = indented[i:attribution_end]
                            a_lines.trim_left(match.end(), end=1)
                            a_lines.trim_left(indent, start=1)
                            return (indented[:i], a_lines,
                                    i, indented[attribution_end:],
                                    line_offset + attribution_end)
                nonblank_seen = True
            else:
                blank = i
        else:
            return indented, None, None, None, None

    def check_attribution(self, indented, attribution_start):
        """
        Check attribution shape.
        Return the index past the end of the attribution, and the indent.
        """
        indent = None
        i = attribution_start + 1
        for i in range(attribution_start + 1, len(indented)):
            line = indented[i].rstrip()
            if not line:
                break
            if indent is None:
                indent = len(line) - len(line.lstrip())
            elif len(line) - len(line.lstrip()) != indent:
                return None, None       # bad shape; not an attribution
        else:
            # return index of line after last attribution line:
            i += 1
        return i, (indent or 0)

    def parse_attribution(self, indented, line_offset):
        text = '\n'.join(indented).rstrip()
        lineno = 1 + line_offset  # line_offset is zero-based
        textnodes, messages = self.inline_text(text, lineno)
        node = nodes.attribution(text, '', *textnodes)
        node.source, node.line = self.state_machine.get_source_and_line(lineno)
        return node, messages

    def bullet(self, match, context, next_state):
        """Bullet list item."""
        bulletlist = nodes.bullet_list()
        (bulletlist.source,
         bulletlist.line) = self.state_machine.get_source_and_line()
        self.parent += bulletlist
        bulletlist['bullet'] = match.string[0]
        i, blank_finish = self.list_item(match.end())
        bulletlist += i
        offset = self.state_machine.line_offset + 1   # next line
        new_line_offset, blank_finish = self.nested_list_parse(
              self.state_machine.input_lines[offset:],
              input_offset=self.state_machine.abs_line_offset() + 1,
              node=bulletlist, initial_state='BulletList',
              blank_finish=blank_finish)
        self.goto_line(new_line_offset)
        if not blank_finish:
            self.parent += self.unindent_warning('Bullet list')
        return [], next_state, []

    def list_item(self, indent):
        if self.state_machine.line[indent:]:
            indented, line_offset, blank_finish = (
                self.state_machine.get_known_indented(indent))
        else:
            indented, indent, line_offset, blank_finish = (
                self.state_machine.get_first_known_indented(indent))
        listitem = nodes.list_item('\n'.join(indented))
        if indented:
            self.nested_parse(indented, input_offset=line_offset,
                              node=listitem)
        return listitem, blank_finish

    def enumerator(self, match, context, next_state):
        """Enumerated List Item"""
        format, sequence, text, ordinal = self.parse_enumerator(match)
        if not self.is_enumerated_list_item(ordinal, sequence, format):
            raise statemachine.TransitionCorrection('text')
        enumlist = nodes.enumerated_list()
        self.parent += enumlist
        if sequence == '#':
            enumlist['enumtype'] = 'arabic'
        else:
            enumlist['enumtype'] = sequence
        enumlist['prefix'] = self.enum.formatinfo[format].prefix
        enumlist['suffix'] = self.enum.formatinfo[format].suffix
        if ordinal != 1:
            enumlist['start'] = ordinal
            msg = self.reporter.info(
                'Enumerated list start value not ordinal-1: "%s" (ordinal %s)'
                % (text, ordinal))
            self.parent += msg
        listitem, blank_finish = self.list_item(match.end())
        enumlist += listitem
        offset = self.state_machine.line_offset + 1   # next line
        newline_offset, blank_finish = self.nested_list_parse(
              self.state_machine.input_lines[offset:],
              input_offset=self.state_machine.abs_line_offset() + 1,
              node=enumlist, initial_state='EnumeratedList',
              blank_finish=blank_finish,
              extra_settings={'lastordinal': ordinal,
                              'format': format,
                              'auto': sequence == '#'})
        self.goto_line(newline_offset)
        if not blank_finish:
            self.parent += self.unindent_warning('Enumerated list')
        return [], next_state, []

    def parse_enumerator(self, match, expected_sequence=None):
        """
        Analyze an enumerator and return the results.

        :Return:
            - the enumerator format ('period', 'parens', or 'rparen'),
            - the sequence used ('arabic', 'loweralpha', 'upperroman', etc.),
            - the text of the enumerator, stripped of formatting, and
            - the ordinal value of the enumerator ('a' -> 1, 'ii' -> 2, etc.;
              ``None`` is returned for invalid enumerator text).

        The enumerator format has already been determined by the regular
        expression match. If `expected_sequence` is given, that sequence is
        tried first. If not, we check for Roman numeral 1. This way,
        single-character Roman numerals (which are also alphabetical) can be
        matched. If no sequence has been matched, all sequences are checked in
        order.
        """
        groupdict = match.groupdict()
        sequence = ''
        for format in self.enum.formats:
            if groupdict[format]:       # was this the format matched?
                break                   # yes; keep `format`
        else:                           # shouldn't happen
            raise ParserError('enumerator format not matched')
        text = groupdict[format][self.enum.formatinfo[format].start     # noqa: E203,E501
                                 : self.enum.formatinfo[format].end]
        if text == '#':
            sequence = '#'
        elif expected_sequence:
            try:
                if self.enum.sequenceregexps[expected_sequence].match(text):
                    sequence = expected_sequence
            except KeyError:            # shouldn't happen
                raise ParserError('unknown enumerator sequence: %s'
                                  % sequence)
        elif text == 'i':
            sequence = 'lowerroman'
        elif text == 'I':
            sequence = 'upperroman'
        if not sequence:
            for sequence in self.enum.sequences:
                if self.enum.sequenceregexps[sequence].match(text):
                    break
            else:                       # shouldn't happen
                raise ParserError('enumerator sequence not matched')
        if sequence == '#':
            ordinal = 1
        else:
            try:
                ordinal = self.enum.converters[sequence](text)
            except roman.InvalidRomanNumeralError:
                ordinal = None
        return format, sequence, text, ordinal

    def is_enumerated_list_item(self, ordinal, sequence, format):
        """
        Check validity based on the ordinal value and the second line.

        Return true if the ordinal is valid and the second line is blank,
        indented, or starts with the next enumerator or an auto-enumerator.
        """
        if ordinal is None:
            return None
        try:
            next_line = self.state_machine.next_line()
        except EOFError:              # end of input lines
            self.state_machine.previous_line()
            return 1
        else:
            self.state_machine.previous_line()
        if not next_line[:1].strip():   # blank or indented
            return 1
        result = self.make_enumerator(ordinal + 1, sequence, format)
        if result:
            next_enumerator, auto_enumerator = result
            try:
                if (next_line.startswith(next_enumerator)
                    or next_line.startswith(auto_enumerator)):
                    return 1
            except TypeError:
                pass
        return None

    def make_enumerator(self, ordinal, sequence, format):
        """
        Construct and return the next enumerated list item marker, and an
        auto-enumerator ("#" instead of the regular enumerator).

        Return ``None`` for invalid (out of range) ordinals.
        """
        if sequence == '#':
            enumerator = '#'
        elif sequence == 'arabic':
            enumerator = str(ordinal)
        else:
            if sequence.endswith('alpha'):
                if ordinal > 26:
                    return None
                enumerator = chr(ordinal + ord('a') - 1)
            elif sequence.endswith('roman'):
                try:
                    enumerator = roman.toRoman(ordinal)
                except roman.RomanError:
                    return None
            else:                       # shouldn't happen
                raise ParserError('unknown enumerator sequence: "%s"'
                                  % sequence)
            if sequence.startswith('lower'):
                enumerator = enumerator.lower()
            elif sequence.startswith('upper'):
                enumerator = enumerator.upper()
            else:                       # shouldn't happen
                raise ParserError('unknown enumerator sequence: "%s"'
                                  % sequence)
        formatinfo = self.enum.formatinfo[format]
        next_enumerator = (formatinfo.prefix + enumerator + formatinfo.suffix
                           + ' ')
        auto_enumerator = formatinfo.prefix + '#' + formatinfo.suffix + ' '
        return next_enumerator, auto_enumerator

    def field_marker(self, match, context, next_state):
        """Field list item."""
        field_list = nodes.field_list()
        self.parent += field_list
        field, blank_finish = self.field(match)
        field_list += field
        offset = self.state_machine.line_offset + 1   # next line
        newline_offset, blank_finish = self.nested_list_parse(
              self.state_machine.input_lines[offset:],
              input_offset=self.state_machine.abs_line_offset() + 1,
              node=field_list, initial_state='FieldList',
              blank_finish=blank_finish)
        self.goto_line(newline_offset)
        if not blank_finish:
            self.parent += self.unindent_warning('Field list')
        return [], next_state, []

    def field(self, match):
        name = self.parse_field_marker(match)
        src, srcline = self.state_machine.get_source_and_line()
        lineno = self.state_machine.abs_line_number()
        (indented, indent, line_offset, blank_finish
         ) = self.state_machine.get_first_known_indented(match.end())
        field_node = nodes.field()
        field_node.source = src
        field_node.line = srcline
        name_nodes, name_messages = self.inline_text(name, lineno)
        field_node += nodes.field_name(name, '', *name_nodes)
        field_body = nodes.field_body('\n'.join(indented), *name_messages)
        field_node += field_body
        if indented:
            self.parse_field_body(indented, line_offset, field_body)
        return field_node, blank_finish

    def parse_field_marker(self, match):
        """Extract & return field name from a field marker match."""
        field = match.group()[1:]         # strip off leading ':'
        field = field[:field.rfind(':')]  # strip off trailing ':' etc.
        return field

    def parse_field_body(self, indented, offset, node):
        self.nested_parse(indented, input_offset=offset, node=node)

    def option_marker(self, match, context, next_state):
        """Option list item."""
        optionlist = nodes.option_list()
        (optionlist.source, optionlist.line
         ) = self.state_machine.get_source_and_line()
        try:
            listitem, blank_finish = self.option_list_item(match)
        except MarkupError as error:
            # This shouldn't happen; pattern won't match.
            msg = self.reporter.error('Invalid option list marker: %s'
                                      % error)
            self.parent += msg
            (indented, indent, line_offset, blank_finish
             ) = self.state_machine.get_first_known_indented(match.end())
            elements = self.block_quote(indented, line_offset)
            self.parent += elements
            if not blank_finish:
                self.parent += self.unindent_warning('Option list')
            return [], next_state, []
        self.parent += optionlist
        optionlist += listitem
        offset = self.state_machine.line_offset + 1   # next line
        newline_offset, blank_finish = self.nested_list_parse(
              self.state_machine.input_lines[offset:],
              input_offset=self.state_machine.abs_line_offset() + 1,
              node=optionlist, initial_state='OptionList',
              blank_finish=blank_finish)
        self.goto_line(newline_offset)
        if not blank_finish:
            self.parent += self.unindent_warning('Option list')
        return [], next_state, []

    def option_list_item(self, match):
        offset = self.state_machine.abs_line_offset()
        options = self.parse_option_marker(match)
        (indented, indent, line_offset, blank_finish
         ) = self.state_machine.get_first_known_indented(match.end())
        if not indented:                # not an option list item
            self.goto_line(offset)
            raise statemachine.TransitionCorrection('text')
        option_group = nodes.option_group('', *options)
        description = nodes.description('\n'.join(indented))
        option_list_item = nodes.option_list_item('', option_group,
                                                  description)
        if indented:
            self.nested_parse(indented, input_offset=line_offset,
                              node=description)
        return option_list_item, blank_finish

    def parse_option_marker(self, match):
        """
        Return a list of `node.option` and `node.option_argument` objects,
        parsed from an option marker match.

        :Exception: `MarkupError` for invalid option markers.
        """
        optlist = []
        optionstrings = match.group().rstrip().split(', ')
        for optionstring in optionstrings:
            tokens = optionstring.split()
            delimiter = ' '
            firstopt = tokens[0].split('=', 1)
            if len(firstopt) > 1:
                # "--opt=value" form
                tokens[:1] = firstopt
                delimiter = '='
            elif (len(tokens[0]) > 2
                  and ((tokens[0].startswith('-')
                        and not tokens[0].startswith('--'))
                       or tokens[0].startswith('+'))):
                # "-ovalue" form
                tokens[:1] = [tokens[0][:2], tokens[0][2:]]
                delimiter = ''
            if len(tokens) > 1 and (tokens[1].startswith('<')
                                    and tokens[-1].endswith('>')):
                # "-o <value1 value2>" form; join all values into one token
                tokens[1:] = [' '.join(tokens[1:])]
            if 0 < len(tokens) <= 2:
                option = nodes.option(optionstring)
                option += nodes.option_string(tokens[0], tokens[0])
                if len(tokens) > 1:
                    option += nodes.option_argument(tokens[1], tokens[1],
                                                    delimiter=delimiter)
                optlist.append(option)
            else:
                raise MarkupError(
                    'wrong number of option tokens (=%s), should be 1 or 2: '
                    '"%s"' % (len(tokens), optionstring))
        return optlist

    def doctest(self, match, context, next_state):
        data = '\n'.join(self.state_machine.get_text_block())
        # TODO: prepend class value ['pycon'] (Python Console)
        # parse with `directives.body.CodeBlock` (returns literal-block
        # with class "code" and syntax highlight markup).
        self.parent += nodes.doctest_block(data, data)
        return [], next_state, []

    def line_block(self, match, context, next_state):
        """First line of a line block."""
        block = nodes.line_block()
        self.parent += block
        lineno = self.state_machine.abs_line_number()
        line, messages, blank_finish = self.line_block_line(match, lineno)
        block += line
        self.parent += messages
        if not blank_finish:
            offset = self.state_machine.line_offset + 1   # next line
            new_line_offset, blank_finish = self.nested_list_parse(
                  self.state_machine.input_lines[offset:],
                  input_offset=self.state_machine.abs_line_offset() + 1,
                  node=block, initial_state='LineBlock',
                  blank_finish=0)
            self.goto_line(new_line_offset)
        if not blank_finish:
            self.parent += self.reporter.warning(
                'Line block ends without a blank line.',
                line=lineno+1)
        if len(block):
            if block[0].indent is None:
                block[0].indent = 0
            self.nest_line_block_lines(block)
        return [], next_state, []

    def line_block_line(self, match, lineno):
        """Return one line element of a line_block."""
        (indented, indent, line_offset, blank_finish
         ) = self.state_machine.get_first_known_indented(match.end(),
                                                         until_blank=True)
        text = '\n'.join(indented)
        text_nodes, messages = self.inline_text(text, lineno)
        line = nodes.line(text, '', *text_nodes)
        if match.string.rstrip() != '|':  # not empty
            line.indent = len(match.group(1)) - 1
        return line, messages, blank_finish

    def nest_line_block_lines(self, block):
        for index in range(1, len(block)):
            if getattr(block[index], 'indent', None) is None:
                block[index].indent = block[index - 1].indent
        self.nest_line_block_segment(block)

    def nest_line_block_segment(self, block):
        indents = [item.indent for item in block]
        least = min(indents)
        new_items = []
        new_block = nodes.line_block()
        for item in block:
            if item.indent > least:
                new_block.append(item)
            else:
                if len(new_block):
                    self.nest_line_block_segment(new_block)
                    new_items.append(new_block)
                    new_block = nodes.line_block()
                new_items.append(item)
        if len(new_block):
            self.nest_line_block_segment(new_block)
            new_items.append(new_block)
        block[:] = new_items

    def grid_table_top(self, match, context, next_state):
        """Top border of a full table."""
        return self.table_top(match, context, next_state,
                              self.isolate_grid_table,
                              tableparser.GridTableParser)

    def simple_table_top(self, match, context, next_state):
        """Top border of a simple table."""
        return self.table_top(match, context, next_state,
                              self.isolate_simple_table,
                              tableparser.SimpleTableParser)

    def table_top(self, match, context, next_state,
                  isolate_function, parser_class):
        """Top border of a generic table."""
        nodelist, blank_finish = self.table(isolate_function, parser_class)
        self.parent += nodelist
        if not blank_finish:
            msg = self.reporter.warning(
                'Blank line required after table.',
                line=self.state_machine.abs_line_number()+1)
            self.parent += msg
        return [], next_state, []

    def table(self, isolate_function, parser_class):
        """Parse a table."""
        block, messages, blank_finish = isolate_function()
        if block:
            try:
                parser = parser_class()
                tabledata = parser.parse(block)
                tableline = (self.state_machine.abs_line_number() - len(block)
                             + 1)
                table = self.build_table(tabledata, tableline)
                nodelist = [table] + messages
            except tableparser.TableMarkupError as err:
                nodelist = self.malformed_table(block, ' '.join(err.args),
                                                offset=err.offset) + messages
        else:
            nodelist = messages
        return nodelist, blank_finish

    def isolate_grid_table(self):
        messages = []
        blank_finish = 1
        try:
            block = self.state_machine.get_text_block(flush_left=True)
        except statemachine.UnexpectedIndentationError as err:
            block, src, srcline = err.args
            messages.append(self.reporter.error('Unexpected indentation.',
                                                source=src, line=srcline))
            blank_finish = 0
        block.disconnect()
        # for East Asian chars:
        block.pad_double_width(self.double_width_pad_char)
        width = len(block[0].strip())
        for i in range(len(block)):
            block[i] = block[i].strip()
            if block[i][0] not in '+|':  # check left edge
                blank_finish = 0
                self.state_machine.previous_line(len(block) - i)
                del block[i:]
                break
        if not self.grid_table_top_pat.match(block[-1]):  # find bottom
            blank_finish = 0
            # from second-last to third line of table:
            for i in range(len(block) - 2, 1, -1):
                if self.grid_table_top_pat.match(block[i]):
                    self.state_machine.previous_line(len(block) - i + 1)
                    del block[i+1:]
                    break
            else:
                messages.extend(self.malformed_table(block))
                return [], messages, blank_finish
        for i in range(len(block)):     # check right edge
            if len(block[i]) != width or block[i][-1] not in '+|':
                messages.extend(self.malformed_table(block))
                return [], messages, blank_finish
        return block, messages, blank_finish

    def isolate_simple_table(self):
        start = self.state_machine.line_offset
        lines = self.state_machine.input_lines
        limit = len(lines) - 1
        toplen = len(lines[start].strip())
        pattern_match = self.simple_table_border_pat.match
        found = 0
        found_at = None
        i = start + 1
        while i <= limit:
            line = lines[i]
            match = pattern_match(line)
            if match:
                if len(line.strip()) != toplen:
                    self.state_machine.next_line(i - start)
                    messages = self.malformed_table(
                        lines[start:i+1], 'Bottom/header table border does '
                        'not match top border.')
                    return [], messages, i == limit or not lines[i+1].strip()
                found += 1
                found_at = i
                if found == 2 or i == limit or not lines[i+1].strip():
                    end = i
                    break
            i += 1
        else:                           # reached end of input_lines
            if found:
                extra = ' or no blank line after table bottom'
                self.state_machine.next_line(found_at - start)
                block = lines[start:found_at+1]
            else:
                extra = ''
                self.state_machine.next_line(i - start - 1)
                block = lines[start:]
            messages = self.malformed_table(
                block, 'No bottom table border found%s.' % extra)
            return [], messages, not extra
        self.state_machine.next_line(end - start)
        block = lines[start:end+1]
        # for East Asian chars:
        block.pad_double_width(self.double_width_pad_char)
        return block, [], end == limit or not lines[end+1].strip()

    def malformed_table(self, block, detail='', offset=0):
        block.replace(self.double_width_pad_char, '')
        data = '\n'.join(block)
        message = 'Malformed table.'
        startline = self.state_machine.abs_line_number() - len(block) + 1
        if detail:
            message += '\n' + detail
        error = self.reporter.error(message, nodes.literal_block(data, data),
                                    line=startline+offset)
        return [error]

    def build_table(self, tabledata, tableline, stub_columns=0, widths=None):
        colwidths, headrows, bodyrows = tabledata
        table = nodes.table()
        if widths == 'auto':
            table['classes'] += ['colwidths-auto']
        elif widths:  # "grid" or list of integers
            table['classes'] += ['colwidths-given']
        tgroup = nodes.tgroup(cols=len(colwidths))
        table += tgroup
        for colwidth in colwidths:
            colspec = nodes.colspec(colwidth=colwidth)
            if stub_columns:
                colspec.attributes['stub'] = 1
                stub_columns -= 1
            tgroup += colspec
        if headrows:
            thead = nodes.thead()
            tgroup += thead
            for row in headrows:
                thead += self.build_table_row(row, tableline)
        tbody = nodes.tbody()
        tgroup += tbody
        for row in bodyrows:
            tbody += self.build_table_row(row, tableline)
        return table

    def build_table_row(self, rowdata, tableline):
        row = nodes.row()
        for cell in rowdata:
            if cell is None:
                continue
            morerows, morecols, offset, cellblock = cell
            attributes = {}
            if morerows:
                attributes['morerows'] = morerows
            if morecols:
                attributes['morecols'] = morecols
            entry = nodes.entry(**attributes)
            row += entry
            if ''.join(cellblock):
                self.nested_parse(cellblock, input_offset=tableline+offset,
                                  node=entry)
        return row

    explicit = Struct()
    """Patterns and constants used for explicit markup recognition."""

    explicit.patterns = Struct(
          target=re.compile(r"""
                            (
                              _               # anonymous target
                            |               # *OR*
                              (?!_)           # no underscore at the beginning
                              (?P<quote>`?)   # optional open quote
                              (?![ `])        # first char. not space or
                                              # backquote
                              (?P<name>       # reference name
                                .+?
                              )
                              %(non_whitespace_escape_before)s
                              (?P=quote)      # close quote if open quote used
                            )
                            (?<!(?<!\x00):) # no unescaped colon at end
                            %(non_whitespace_escape_before)s
                            [ ]?            # optional space
                            :               # end of reference name
                            ([ ]+|$)        # followed by whitespace
                            """ % vars(Inliner), re.VERBOSE),
          reference=re.compile(r"""
                               (
                                 (?P<simple>%(simplename)s)_
                               |                  # *OR*
                                 `                  # open backquote
                                 (?![ ])            # not space
                                 (?P<phrase>.+?)    # hyperlink phrase
                                 %(non_whitespace_escape_before)s
                                 `_                 # close backquote,
                                                    # reference mark
                               )
                               $                  # end of string
                               """ % vars(Inliner), re.VERBOSE),
          substitution=re.compile(r"""
                                  (
                                    (?![ ])          # first char. not space
                                    (?P<name>.+?)    # substitution text
                                    %(non_whitespace_escape_before)s
                                    \|               # close delimiter
                                  )
                                  ([ ]+|$)           # followed by whitespace
                                  """ % vars(Inliner),
                                  re.VERBOSE),)

    def footnote(self, match):
        src, srcline = self.state_machine.get_source_and_line()
        (indented, indent, offset, blank_finish
         ) = self.state_machine.get_first_known_indented(match.end())
        label = match.group(1)
        name = normalize_name(label)
        footnote = nodes.footnote('\n'.join(indented))
        footnote.source = src
        footnote.line = srcline
        if name[0] == '#':              # auto-numbered
            name = name[1:]             # autonumber label
            footnote['auto'] = 1
            if name:
                footnote['names'].append(name)
            self.document.note_autofootnote(footnote)
        elif name == '*':               # auto-symbol
            name = ''
            footnote['auto'] = '*'
            self.document.note_symbol_footnote(footnote)
        else:                           # manually numbered
            footnote += nodes.label('', label)
            footnote['names'].append(name)
            self.document.note_footnote(footnote)
        if name:
            self.document.note_explicit_target(footnote, footnote)
        else:
            self.document.set_id(footnote, footnote)
        if indented:
            self.nested_parse(indented, input_offset=offset, node=footnote)
        return [footnote], blank_finish

    def citation(self, match):
        src, srcline = self.state_machine.get_source_and_line()
        (indented, indent, offset, blank_finish
         ) = self.state_machine.get_first_known_indented(match.end())
        label = match.group(1)
        name = normalize_name(label)
        citation = nodes.citation('\n'.join(indented))
        citation.source = src
        citation.line = srcline
        citation += nodes.label('', label)
        citation['names'].append(name)
        self.document.note_citation(citation)
        self.document.note_explicit_target(citation, citation)
        if indented:
            self.nested_parse(indented, input_offset=offset, node=citation)
        return [citation], blank_finish

    def hyperlink_target(self, match):
        pattern = self.explicit.patterns.target
        lineno = self.state_machine.abs_line_number()
        (block, indent, offset, blank_finish
         ) = self.state_machine.get_first_known_indented(
                 match.end(), until_blank=True, strip_indent=False)
        blocktext = match.string[:match.end()] + '\n'.join(block)
        block = [escape2null(line) for line in block]
        escaped = block[0]
        blockindex = 0
        while True:
            targetmatch = pattern.match(escaped)
            if targetmatch:
                break
            blockindex += 1
            try:
                escaped += block[blockindex]
            except IndexError:
                raise MarkupError('malformed hyperlink target.')
        del block[:blockindex]
        block[0] = (block[0] + ' ')[targetmatch.end()-len(escaped)-1:].strip()
        target = self.make_target(block, blocktext, lineno,
                                  targetmatch.group('name'))
        return [target], blank_finish

    def make_target(self, block, block_text, lineno, target_name):
        target_type, data = self.parse_target(block, block_text, lineno)
        if target_type == 'refname':
            target = nodes.target(block_text, '', refname=normalize_name(data))
            target.indirect_reference_name = data
            self.add_target(target_name, '', target, lineno)
            self.document.note_indirect_target(target)
            return target
        elif target_type == 'refuri':
            target = nodes.target(block_text, '')
            self.add_target(target_name, data, target, lineno)
            return target
        else:
            return data

    def parse_target(self, block, block_text, lineno):
        """
        Determine the type of reference of a target.

        :Return: A 2-tuple, one of:

            - 'refname' and the indirect reference name
            - 'refuri' and the URI
            - 'malformed' and a system_message node
        """
        if block and block[-1].strip()[-1:] == '_':  # possible indirect target
            reference = ' '.join(line.strip() for line in block)
            refname = self.is_reference(reference)
            if refname:
                return 'refname', refname
        ref_parts = split_escaped_whitespace(' '.join(block))
        reference = ' '.join(''.join(unescape(part).split())
                             for part in ref_parts)
        return 'refuri', reference

    def is_reference(self, reference):
        match = self.explicit.patterns.reference.match(
            whitespace_normalize_name(reference))
        if not match:
            return None
        return unescape(match.group('simple') or match.group('phrase'))

    def add_target(self, targetname, refuri, target, lineno):
        target.line = lineno
        if targetname:
            name = normalize_name(unescape(targetname))
            target['names'].append(name)
            if refuri:
                uri = self.inliner.adjust_uri(refuri)
                if uri:
                    target['refuri'] = uri
                else:
                    raise ApplicationError('problem with URI: %r' % refuri)
            self.document.note_explicit_target(target, self.parent)
        else:                       # anonymous target
            if refuri:
                target['refuri'] = refuri
            target['anonymous'] = 1
            self.document.note_anonymous_target(target)

    def substitution_def(self, match):
        pattern = self.explicit.patterns.substitution
        src, srcline = self.state_machine.get_source_and_line()
        (block, indent, offset, blank_finish
         ) = self.state_machine.get_first_known_indented(match.end(),
                                                         strip_indent=False)
        blocktext = (match.string[:match.end()] + '\n'.join(block))
        block.disconnect()
        escaped = escape2null(block[0].rstrip())
        blockindex = 0
        while True:
            subdefmatch = pattern.match(escaped)
            if subdefmatch:
                break
            blockindex += 1
            try:
                escaped = escaped + ' ' + escape2null(
                                              block[blockindex].strip())
            except IndexError:
                raise MarkupError('malformed substitution definition.')
        del block[:blockindex]          # strip out the substitution marker
        start = subdefmatch.end()-len(escaped)-1
        block[0] = (block[0].strip() + ' ')[start:-1]
        if not block[0]:
            del block[0]
            offset += 1
        while block and not block[-1].strip():
            block.pop()
        subname = subdefmatch.group('name')
        substitution_node = nodes.substitution_definition(blocktext)
        substitution_node.source = src
        substitution_node.line = srcline
        if not block:
            msg = self.reporter.warning(
                'Substitution definition "%s" missing contents.' % subname,
                nodes.literal_block(blocktext, blocktext),
                source=src, line=srcline)
            return [msg], blank_finish
        block[0] = block[0].strip()
        substitution_node['names'].append(
            nodes.whitespace_normalize_name(subname))
        new_abs_offset, blank_finish = self.nested_list_parse(
              block, input_offset=offset, node=substitution_node,
              initial_state='SubstitutionDef', blank_finish=blank_finish)
        i = 0
        for node in substitution_node[:]:
            if not (isinstance(node, nodes.Inline)
                    or isinstance(node, nodes.Text)):
                self.parent += substitution_node[i]
                del substitution_node[i]
            else:
                i += 1
        for node in substitution_node.findall(nodes.Element):
            if self.disallowed_inside_substitution_definitions(node):
                pformat = nodes.literal_block('', node.pformat().rstrip())
                msg = self.reporter.error(
                    'Substitution definition contains illegal element <%s>:'
                    % node.tagname,
                    pformat, nodes.literal_block(blocktext, blocktext),
                    source=src, line=srcline)
                return [msg], blank_finish
        if len(substitution_node) == 0:
            msg = self.reporter.warning(
                  'Substitution definition "%s" empty or invalid.' % subname,
                  nodes.literal_block(blocktext, blocktext),
                  source=src, line=srcline)
            return [msg], blank_finish
        self.document.note_substitution_def(
            substitution_node, subname, self.parent)
        return [substitution_node], blank_finish

    def disallowed_inside_substitution_definitions(self, node):
        if (node['ids']
            or isinstance(node, nodes.reference) and node.get('anonymous')
            or isinstance(node, nodes.footnote_reference) and node.get('auto')):  # noqa: E501
            return True
        else:
            return False

    def directive(self, match, **option_presets):
        """Returns a 2-tuple: list of nodes, and a "blank finish" boolean."""
        type_name = match.group(1)
        directive_class, messages = directives.directive(
            type_name, self.memo.language, self.document)
        self.parent += messages
        if directive_class:
            return self.run_directive(
                directive_class, match, type_name, option_presets)
        else:
            return self.unknown_directive(type_name)

    def run_directive(self, directive, match, type_name, option_presets):
        """
        Parse a directive then run its directive function.

        Parameters:

        - `directive`: The class implementing the directive.  Must be
          a subclass of `rst.Directive`.

        - `match`: A regular expression match object which matched the first
          line of the directive.

        - `type_name`: The directive name, as used in the source text.

        - `option_presets`: A dictionary of preset options, defaults for the
          directive options.  Currently, only an "alt" option is passed by
          substitution definitions (value: the substitution name), which may
          be used by an embedded image directive.

        Returns a 2-tuple: list of nodes, and a "blank finish" boolean.
        """
        if isinstance(directive, (FunctionType, MethodType)):
            from docutils.parsers.rst import convert_directive_function
            directive = convert_directive_function(directive)
        lineno = self.state_machine.abs_line_number()
        initial_line_offset = self.state_machine.line_offset
        (indented, indent, line_offset, blank_finish
         ) = self.state_machine.get_first_known_indented(match.end(),
                                                         strip_top=0)
        block_text = '\n'.join(self.state_machine.input_lines[
            initial_line_offset : self.state_machine.line_offset + 1])  # noqa: E203,E501
        try:
            arguments, options, content, content_offset = (
                self.parse_directive_block(indented, line_offset,
                                           directive, option_presets))
        except MarkupError as detail:
            error = self.reporter.error(
                'Error in "%s" directive:\n%s.' % (type_name,
                                                   ' '.join(detail.args)),
                nodes.literal_block(block_text, block_text), line=lineno)
            return [error], blank_finish
        directive_instance = directive(
            type_name, arguments, options, content, lineno,
            content_offset, block_text, self, self.state_machine)
        try:
            result = directive_instance.run()
        except docutils.parsers.rst.DirectiveError as error:
            msg_node = self.reporter.system_message(error.level, error.msg,
                                                    line=lineno)
            msg_node += nodes.literal_block(block_text, block_text)
            result = [msg_node]
        assert isinstance(result, list), \
               'Directive "%s" must return a list of nodes.' % type_name
        for i in range(len(result)):
            assert isinstance(result[i], nodes.Node), \
                   ('Directive "%s" returned non-Node object (index %s): %r'
                    % (type_name, i, result[i]))
        return (result,
                blank_finish or self.state_machine.is_next_line_blank())

    def parse_directive_block(self, indented, line_offset, directive,
                              option_presets):
        option_spec = directive.option_spec
        has_content = directive.has_content
        if indented and not indented[0].strip():
            indented.trim_start()
            line_offset += 1
        while indented and not indented[-1].strip():
            indented.trim_end()
        if indented and (directive.required_arguments
                         or directive.optional_arguments
                         or option_spec):
            for i, line in enumerate(indented):
                if not line.strip():
                    break
            else:
                i += 1
            arg_block = indented[:i]
            content = indented[i+1:]
            content_offset = line_offset + i + 1
        else:
            content = indented
            content_offset = line_offset
            arg_block = []
        if option_spec:
            options, arg_block = self.parse_directive_options(
                option_presets, option_spec, arg_block)
        else:
            options = {}
        if arg_block and not (directive.required_arguments
                              or directive.optional_arguments):
            content = arg_block + indented[i:]
            content_offset = line_offset
            arg_block = []
        while content and not content[0].strip():
            content.trim_start()
            content_offset += 1
        if directive.required_arguments or directive.optional_arguments:
            arguments = self.parse_directive_arguments(
                directive, arg_block)
        else:
            arguments = []
        if content and not has_content:
            raise MarkupError('no content permitted')
        return arguments, options, content, content_offset

    def parse_directive_options(self, option_presets, option_spec, arg_block):
        options = option_presets.copy()
        for i, line in enumerate(arg_block):
            if re.match(Body.patterns['field_marker'], line):
                opt_block = arg_block[i:]
                arg_block = arg_block[:i]
                break
        else:
            opt_block = []
        if opt_block:
            success, data = self.parse_extension_options(option_spec,
                                                         opt_block)
            if success:                 # data is a dict of options
                options.update(data)
            else:                       # data is an error string
                raise MarkupError(data)
        return options, arg_block

    def parse_directive_arguments(self, directive, arg_block):
        required = directive.required_arguments
        optional = directive.optional_arguments
        arg_text = '\n'.join(arg_block)
        arguments = arg_text.split()
        if len(arguments) < required:
            raise MarkupError('%s argument(s) required, %s supplied'
                              % (required, len(arguments)))
        elif len(arguments) > required + optional:
            if directive.final_argument_whitespace:
                arguments = arg_text.split(None, required + optional - 1)
            else:
                raise MarkupError(
                    'maximum %s argument(s) allowed, %s supplied'
                    % (required + optional, len(arguments)))
        return arguments

    def parse_extension_options(self, option_spec, datalines):
        """
        Parse `datalines` for a field list containing extension options
        matching `option_spec`.

        :Parameters:
            - `option_spec`: a mapping of option name to conversion
              function, which should raise an exception on bad input.
            - `datalines`: a list of input strings.

        :Return:
            - Success value, 1 or 0.
            - An option dictionary on success, an error string on failure.
        """
        node = nodes.field_list()
        newline_offset, blank_finish = self.nested_list_parse(
              datalines, 0, node, initial_state='ExtensionOptions',
              blank_finish=True)
        if newline_offset != len(datalines):  # incomplete parse of block
            return 0, 'invalid option block'
        try:
            options = utils.extract_extension_options(node, option_spec)
        except KeyError as detail:
            return 0, 'unknown option: "%s"' % detail.args[0]
        except (ValueError, TypeError) as detail:
            return 0, 'invalid option value: %s' % ' '.join(detail.args)
        except utils.ExtensionOptionError as detail:
            return 0, 'invalid option data: %s' % ' '.join(detail.args)
        if blank_finish:
            return 1, options
        else:
            return 0, 'option data incompletely parsed'

    def unknown_directive(self, type_name):
        lineno = self.state_machine.abs_line_number()
        (indented, indent, offset, blank_finish
         ) = self.state_machine.get_first_known_indented(0, strip_indent=False)
        text = '\n'.join(indented)
        error = self.reporter.error('Unknown directive type "%s".' % type_name,
                                    nodes.literal_block(text, text),
                                    line=lineno)
        return [error], blank_finish

    def comment(self, match):
        if self.state_machine.is_next_line_blank():
            first_comment_line = match.string[match.end():]
            if not first_comment_line.strip():  # empty comment
                return [nodes.comment()], True  # "A tiny but practical wart."
            if first_comment_line.startswith('end of inclusion from "'):
                # cf. parsers.rst.directives.misc.Include
                self.document.include_log.pop()
                return [], True
        (indented, indent, offset, blank_finish
         ) = self.state_machine.get_first_known_indented(match.end())
        while indented and not indented[-1].strip():
            indented.trim_end()
        text = '\n'.join(indented)
        return [nodes.comment(text, text)], blank_finish

    explicit.constructs = [
          (footnote,
           re.compile(r"""
                      \.\.[ ]+          # explicit markup start
                      \[
                      (                 # footnote label:
                          [0-9]+          # manually numbered footnote
                        |               # *OR*
                          \#              # anonymous auto-numbered footnote
                        |               # *OR*
                          \#%s            # auto-number ed?) footnote label
                        |               # *OR*
                          \*              # auto-symbol footnote
                      )
                      \]
                      ([ ]+|$)          # whitespace or end of line
                      """ % Inliner.simplename, re.VERBOSE)),
          (citation,
           re.compile(r"""
                      \.\.[ ]+          # explicit markup start
                      \[(%s)\]          # citation label
                      ([ ]+|$)          # whitespace or end of line
                      """ % Inliner.simplename, re.VERBOSE)),
          (hyperlink_target,
           re.compile(r"""
                      \.\.[ ]+          # explicit markup start
                      _                 # target indicator
                      (?![ ]|$)         # first char. not space or EOL
                      """, re.VERBOSE)),
          (substitution_def,
           re.compile(r"""
                      \.\.[ ]+          # explicit markup start
                      \|                # substitution indicator
                      (?![ ]|$)         # first char. not space or EOL
                      """, re.VERBOSE)),
          (directive,
           re.compile(r"""
                      \.\.[ ]+          # explicit markup start
                      (%s)              # directive name
                      [ ]?              # optional space
                      ::                # directive delimiter
                      ([ ]+|$)          # whitespace or end of line
                      """ % Inliner.simplename, re.VERBOSE))]

    def explicit_markup(self, match, context, next_state):
        """Footnotes, hyperlink targets, directives, comments."""
        nodelist, blank_finish = self.explicit_construct(match)
        self.parent += nodelist
        self.explicit_list(blank_finish)
        return [], next_state, []

    def explicit_construct(self, match):
        """Determine which explicit construct this is, parse & return it."""
        errors = []
        for method, pattern in self.explicit.constructs:
            expmatch = pattern.match(match.string)
            if expmatch:
                try:
                    return method(self, expmatch)
                except MarkupError as error:
                    lineno = self.state_machine.abs_line_number()
                    message = ' '.join(error.args)
                    errors.append(self.reporter.warning(message, line=lineno))
                    break
        nodelist, blank_finish = self.comment(match)
        return nodelist + errors, blank_finish

    def explicit_list(self, blank_finish):
        """
        Create a nested state machine for a series of explicit markup
        constructs (including anonymous hyperlink targets).
        """
        offset = self.state_machine.line_offset + 1   # next line
        newline_offset, blank_finish = self.nested_list_parse(
              self.state_machine.input_lines[offset:],
              input_offset=self.state_machine.abs_line_offset() + 1,
              node=self.parent, initial_state='Explicit',
              blank_finish=blank_finish,
              match_titles=self.state_machine.match_titles)
        self.goto_line(newline_offset)
        if not blank_finish:
            self.parent += self.unindent_warning('Explicit markup')

    def anonymous(self, match, context, next_state):
        """Anonymous hyperlink targets."""
        nodelist, blank_finish = self.anonymous_target(match)
        self.parent += nodelist
        self.explicit_list(blank_finish)
        return [], next_state, []

    def anonymous_target(self, match):
        lineno = self.state_machine.abs_line_number()
        (block, indent, offset, blank_finish
         ) = self.state_machine.get_first_known_indented(match.end(),
                                                         until_blank=True)
        blocktext = match.string[:match.end()] + '\n'.join(block)
        block = [escape2null(line) for line in block]
        target = self.make_target(block, blocktext, lineno, '')
        return [target], blank_finish

    def line(self, match, context, next_state):
        """Section title overline or transition marker."""
        if self.state_machine.match_titles:
            return [match.string], 'Line', []
        elif match.string.strip() == '::':
            raise statemachine.TransitionCorrection('text')
        elif len(match.string.strip()) < 4:
            msg = self.reporter.info(
                'Unexpected possible title overline or transition.\n'
                "Treating it as ordinary text because it's so short.",
                line=self.state_machine.abs_line_number())
            self.parent += msg
            raise statemachine.TransitionCorrection('text')
        else:
            blocktext = self.state_machine.line
            msg = self.reporter.severe(
                  'Unexpected section title or transition.',
                  nodes.literal_block(blocktext, blocktext),
                  line=self.state_machine.abs_line_number())
            self.parent += msg
            return [], next_state, []

    def text(self, match, context, next_state):
        """Titles, definition lists, paragraphs."""
        return [match.string], 'Text', []


class RFC2822Body(Body):

    """
    RFC2822 headers are only valid as the first constructs in documents.  As
    soon as anything else appears, the `Body` state should take over.
    """

    patterns = Body.patterns.copy()     # can't modify the original
    patterns['rfc2822'] = r'[!-9;-~]+:( +|$)'
    initial_transitions = [(name, 'Body')
                           for name in Body.initial_transitions]
    initial_transitions.insert(-1, ('rfc2822', 'Body'))  # just before 'text'

    def rfc2822(self, match, context, next_state):
        """RFC2822-style field list item."""
        fieldlist = nodes.field_list(classes=['rfc2822'])
        self.parent += fieldlist
        field, blank_finish = self.rfc2822_field(match)
        fieldlist += field
        offset = self.state_machine.line_offset + 1  # next line
        newline_offset, blank_finish = self.nested_list_parse(
              self.state_machine.input_lines[offset:],
              input_offset=self.state_machine.abs_line_offset() + 1,
              node=fieldlist, initial_state='RFC2822List',
              blank_finish=blank_finish)
        self.goto_line(newline_offset)
        if not blank_finish:
            self.parent += self.unindent_warning(
                  'RFC2822-style field list')
        return [], next_state, []

    def rfc2822_field(self, match):
        name = match.string[:match.string.find(':')]
        (indented, indent, line_offset, blank_finish
         ) = self.state_machine.get_first_known_indented(match.end(),
                                                         until_blank=True)
        fieldnode = nodes.field()
        fieldnode += nodes.field_name(name, name)
        fieldbody = nodes.field_body('\n'.join(indented))
        fieldnode += fieldbody
        if indented:
            self.nested_parse(indented, input_offset=line_offset,
                              node=fieldbody)
        return fieldnode, blank_finish


class SpecializedBody(Body):

    """
    Superclass for second and subsequent compound element members.  Compound
    elements are lists and list-like constructs.

    All transition methods are disabled (redefined as `invalid_input`).
    Override individual methods in subclasses to re-enable.

    For example, once an initial bullet list item, say, is recognized, the
    `BulletList` subclass takes over, with a "bullet_list" node as its
    container.  Upon encountering the initial bullet list item, `Body.bullet`
    calls its ``self.nested_list_parse`` (`RSTState.nested_list_parse`), which
    starts up a nested parsing session with `BulletList` as the initial state.
    Only the ``bullet`` transition method is enabled in `BulletList`; as long
    as only bullet list items are encountered, they are parsed and inserted
    into the container.  The first construct which is *not* a bullet list item
    triggers the `invalid_input` method, which ends the nested parse and
    closes the container.  `BulletList` needs to recognize input that is
    invalid in the context of a bullet list, which means everything *other
    than* bullet list items, so it inherits the transition list created in
    `Body`.
    """

    def invalid_input(self, match=None, context=None, next_state=None):
        """Not a compound element member. Abort this state machine."""
        self.state_machine.previous_line()  # back up so parent SM can reassess
        raise EOFError

    indent = invalid_input
    bullet = invalid_input
    enumerator = invalid_input
    field_marker = invalid_input
    option_marker = invalid_input
    doctest = invalid_input
    line_block = invalid_input
    grid_table_top = invalid_input
    simple_table_top = invalid_input
    explicit_markup = invalid_input
    anonymous = invalid_input
    line = invalid_input
    text = invalid_input


class BulletList(SpecializedBody):

    """Second and subsequent bullet_list list_items."""

    def bullet(self, match, context, next_state):
        """Bullet list item."""
        if match.string[0] != self.parent['bullet']:
            # different bullet: new list
            self.invalid_input()
        listitem, blank_finish = self.list_item(match.end())
        self.parent += listitem
        self.blank_finish = blank_finish
        return [], next_state, []


class DefinitionList(SpecializedBody):

    """Second and subsequent definition_list_items."""

    def text(self, match, context, next_state):
        """Definition lists."""
        return [match.string], 'Definition', []


class EnumeratedList(SpecializedBody):

    """Second and subsequent enumerated_list list_items."""

    def enumerator(self, match, context, next_state):
        """Enumerated list item."""
        format, sequence, text, ordinal = self.parse_enumerator(
              match, self.parent['enumtype'])
        if (format != self.format
            or (sequence != '#' and (sequence != self.parent['enumtype']
                                     or self.auto
                                     or ordinal != (self.lastordinal + 1)))
            or not self.is_enumerated_list_item(ordinal, sequence, format)):
            # different enumeration: new list
            self.invalid_input()
        if sequence == '#':
            self.auto = 1
        listitem, blank_finish = self.list_item(match.end())
        self.parent += listitem
        self.blank_finish = blank_finish
        self.lastordinal = ordinal
        return [], next_state, []


class FieldList(SpecializedBody):

    """Second and subsequent field_list fields."""

    def field_marker(self, match, context, next_state):
        """Field list field."""
        field, blank_finish = self.field(match)
        self.parent += field
        self.blank_finish = blank_finish
        return [], next_state, []


class OptionList(SpecializedBody):

    """Second and subsequent option_list option_list_items."""

    def option_marker(self, match, context, next_state):
        """Option list item."""
        try:
            option_list_item, blank_finish = self.option_list_item(match)
        except MarkupError:
            self.invalid_input()
        self.parent += option_list_item
        self.blank_finish = blank_finish
        return [], next_state, []


class RFC2822List(SpecializedBody, RFC2822Body):

    """Second and subsequent RFC2822-style field_list fields."""

    patterns = RFC2822Body.patterns
    initial_transitions = RFC2822Body.initial_transitions

    def rfc2822(self, match, context, next_state):
        """RFC2822-style field list item."""
        field, blank_finish = self.rfc2822_field(match)
        self.parent += field
        self.blank_finish = blank_finish
        return [], 'RFC2822List', []

    blank = SpecializedBody.invalid_input


class ExtensionOptions(FieldList):

    """
    Parse field_list fields for extension options.

    No nested parsing is done (including inline markup parsing).
    """

    def parse_field_body(self, indented, offset, node):
        """Override `Body.parse_field_body` for simpler parsing."""
        lines = []
        for line in list(indented) + ['']:
            if line.strip():
                lines.append(line)
            elif lines:
                text = '\n'.join(lines)
                node += nodes.paragraph(text, text)
                lines = []


class LineBlock(SpecializedBody):

    """Second and subsequent lines of a line_block."""

    blank = SpecializedBody.invalid_input

    def line_block(self, match, context, next_state):
        """New line of line block."""
        lineno = self.state_machine.abs_line_number()
        line, messages, blank_finish = self.line_block_line(match, lineno)
        self.parent += line
        self.parent.parent += messages
        self.blank_finish = blank_finish
        return [], next_state, []


class Explicit(SpecializedBody):

    """Second and subsequent explicit markup construct."""

    def explicit_markup(self, match, context, next_state):
        """Footnotes, hyperlink targets, directives, comments."""
        nodelist, blank_finish = self.explicit_construct(match)
        self.parent += nodelist
        self.blank_finish = blank_finish
        return [], next_state, []

    def anonymous(self, match, context, next_state):
        """Anonymous hyperlink targets."""
        nodelist, blank_finish = self.anonymous_target(match)
        self.parent += nodelist
        self.blank_finish = blank_finish
        return [], next_state, []

    blank = SpecializedBody.invalid_input


class SubstitutionDef(Body):

    """
    Parser for the contents of a substitution_definition element.
    """

    patterns = {
          'embedded_directive': re.compile(r'(%s)::( +|$)'
                                           % Inliner.simplename),
          'text': r''}
    initial_transitions = ['embedded_directive', 'text']

    def embedded_directive(self, match, context, next_state):
        nodelist, blank_finish = self.directive(match,
                                                alt=self.parent['names'][0])
        self.parent += nodelist
        if not self.state_machine.at_eof():
            self.blank_finish = blank_finish
        raise EOFError

    def text(self, match, context, next_state):
        if not self.state_machine.at_eof():
            self.blank_finish = self.state_machine.is_next_line_blank()
        raise EOFError


class Text(RSTState):

    """
    Classifier of second line of a text block.

    Could be a paragraph, a definition list item, or a title.
    """

    patterns = {'underline': Body.patterns['line'],
                'text': r''}
    initial_transitions = [('underline', 'Body'), ('text', 'Body')]

    def blank(self, match, context, next_state):
        """End of paragraph."""
        # NOTE: self.paragraph returns [node, system_message(s)], literalnext
        paragraph, literalnext = self.paragraph(
              context, self.state_machine.abs_line_number() - 1)
        self.parent += paragraph
        if literalnext:
            self.parent += self.literal_block()
        return [], 'Body', []

    def eof(self, context):
        if context:
            self.blank(None, context, None)
        return []

    def indent(self, match, context, next_state):
        """Definition list item."""
        definitionlist = nodes.definition_list()
        definitionlistitem, blank_finish = self.definition_list_item(context)
        definitionlist += definitionlistitem
        self.parent += definitionlist
        offset = self.state_machine.line_offset + 1   # next line
        newline_offset, blank_finish = self.nested_list_parse(
              self.state_machine.input_lines[offset:],
              input_offset=self.state_machine.abs_line_offset() + 1,
              node=definitionlist, initial_state='DefinitionList',
              blank_finish=blank_finish, blank_finish_state='Definition')
        self.goto_line(newline_offset)
        if not blank_finish:
            self.parent += self.unindent_warning('Definition list')
        return [], 'Body', []

    def underline(self, match, context, next_state):
        """Section title."""
        lineno = self.state_machine.abs_line_number()
        title = context[0].rstrip()
        underline = match.string.rstrip()
        source = title + '\n' + underline
        messages = []
        if column_width(title) > len(underline):
            if len(underline) < 4:
                if self.state_machine.match_titles:
                    msg = self.reporter.info(
                        'Possible title underline, too short for the title.\n'
                        "Treating it as ordinary text because it's so short.",
                        line=lineno)
                    self.parent += msg
                raise statemachine.TransitionCorrection('text')
            else:
                blocktext = context[0] + '\n' + self.state_machine.line
                msg = self.reporter.warning(
                    'Title underline too short.',
                    nodes.literal_block(blocktext, blocktext),
                    line=lineno)
                messages.append(msg)
        if not self.state_machine.match_titles:
            blocktext = context[0] + '\n' + self.state_machine.line
            # We need get_source_and_line() here to report correctly
            src, srcline = self.state_machine.get_source_and_line()
            # TODO: why is abs_line_number() == srcline+1
            # if the error is in a table (try with test_tables.py)?
            # print("get_source_and_line", srcline)
            # print("abs_line_number", self.state_machine.abs_line_number())
            msg = self.reporter.severe(
                'Unexpected section title.',
                nodes.literal_block(blocktext, blocktext),
                source=src, line=srcline)
            self.parent += messages
            self.parent += msg
            return [], next_state, []
        style = underline[0]
        context[:] = []
        self.section(title, source, style, lineno - 1, messages)
        return [], next_state, []

    def text(self, match, context, next_state):
        """Paragraph."""
        startline = self.state_machine.abs_line_number() - 1
        msg = None
        try:
            block = self.state_machine.get_text_block(flush_left=True)
        except statemachine.UnexpectedIndentationError as err:
            block, src, srcline = err.args
            msg = self.reporter.error('Unexpected indentation.',
                                      source=src, line=srcline)
        lines = context + list(block)
        paragraph, literalnext = self.paragraph(lines, startline)
        self.parent += paragraph
        self.parent += msg
        if literalnext:
            try:
                self.state_machine.next_line()
            except EOFError:
                pass
            self.parent += self.literal_block()
        return [], next_state, []

    def literal_block(self):
        """Return a list of nodes."""
        (indented, indent, offset, blank_finish
         ) = self.state_machine.get_indented()
        while indented and not indented[-1].strip():
            indented.trim_end()
        if not indented:
            return self.quoted_literal_block()
        data = '\n'.join(indented)
        literal_block = nodes.literal_block(data, data)
        (literal_block.source,
         literal_block.line) = self.state_machine.get_source_and_line(offset+1)
        nodelist = [literal_block]
        if not blank_finish:
            nodelist.append(self.unindent_warning('Literal block'))
        return nodelist

    def quoted_literal_block(self):
        abs_line_offset = self.state_machine.abs_line_offset()
        offset = self.state_machine.line_offset
        parent_node = nodes.Element()
        new_abs_offset = self.nested_parse(
            self.state_machine.input_lines[offset:],
            input_offset=abs_line_offset, node=parent_node, match_titles=False,
            state_machine_kwargs={'state_classes': (QuotedLiteralBlock,),
                                  'initial_state': 'QuotedLiteralBlock'})
        self.goto_line(new_abs_offset)
        return parent_node.children

    def definition_list_item(self, termline):
        (indented, indent, line_offset, blank_finish
         ) = self.state_machine.get_indented()
        itemnode = nodes.definition_list_item(
            '\n'.join(termline + list(indented)))
        lineno = self.state_machine.abs_line_number() - 1
        (itemnode.source,
         itemnode.line) = self.state_machine.get_source_and_line(lineno)
        termlist, messages = self.term(termline, lineno)
        itemnode += termlist
        definition = nodes.definition('', *messages)
        itemnode += definition
        if termline[0][-2:] == '::':
            definition += self.reporter.info(
                  'Blank line missing before literal block (after the "::")? '
                  'Interpreted as a definition list item.',
                  line=lineno+1)
        self.nested_parse(indented, input_offset=line_offset, node=definition)
        return itemnode, blank_finish

    classifier_delimiter = re.compile(' +: +')

    def term(self, lines, lineno):
        """Return a definition_list's term and optional classifiers."""
        assert len(lines) == 1
        text_nodes, messages = self.inline_text(lines[0], lineno)
        term_node = nodes.term(lines[0])
        (term_node.source,
         term_node.line) = self.state_machine.get_source_and_line(lineno)
        node_list = [term_node]
        for i in range(len(text_nodes)):
            node = text_nodes[i]
            if isinstance(node, nodes.Text):
                parts = self.classifier_delimiter.split(node)
                if len(parts) == 1:
                    node_list[-1] += node
                else:
                    text = parts[0].rstrip()
                    textnode = nodes.Text(text)
                    node_list[-1] += textnode
                    for part in parts[1:]:
                        node_list.append(
                            nodes.classifier(unescape(part, True), part))
            else:
                node_list[-1] += node
        return node_list, messages


class SpecializedText(Text):

    """
    Superclass for second and subsequent lines of Text-variants.

    All transition methods are disabled. Override individual methods in
    subclasses to re-enable.
    """

    def eof(self, context):
        """Incomplete construct."""
        return []

    def invalid_input(self, match=None, context=None, next_state=None):
        """Not a compound element member. Abort this state machine."""
        raise EOFError

    blank = invalid_input
    indent = invalid_input
    underline = invalid_input
    text = invalid_input


class Definition(SpecializedText):

    """Second line of potential definition_list_item."""

    def eof(self, context):
        """Not a definition."""
        self.state_machine.previous_line(2)  # so parent SM can reassess
        return []

    def indent(self, match, context, next_state):
        """Definition list item."""
        itemnode, blank_finish = self.definition_list_item(context)
        self.parent += itemnode
        self.blank_finish = blank_finish
        return [], 'DefinitionList', []


class Line(SpecializedText):

    """
    Second line of over- & underlined section title or transition marker.
    """

    eofcheck = 1                        # @@@ ???
    """Set to 0 while parsing sections, so that we don't catch the EOF."""

    def eof(self, context):
        """Transition marker at end of section or document."""
        marker = context[0].strip()
        if self.memo.section_bubble_up_kludge:
            self.memo.section_bubble_up_kludge = False
        elif len(marker) < 4:
            self.state_correction(context)
        if self.eofcheck:               # ignore EOFError with sections
            src, srcline = self.state_machine.get_source_and_line()
            # lineno = self.state_machine.abs_line_number() - 1
            transition = nodes.transition(rawsource=context[0])
            transition.source = src
            transition.line = srcline - 1
            # transition.line = lineno
            self.parent += transition
        self.eofcheck = 1
        return []

    def blank(self, match, context, next_state):
        """Transition marker."""
        src, srcline = self.state_machine.get_source_and_line()
        marker = context[0].strip()
        if len(marker) < 4:
            self.state_correction(context)
        transition = nodes.transition(rawsource=marker)
        transition.source = src
        transition.line = srcline - 1
        self.parent += transition
        return [], 'Body', []

    def text(self, match, context, next_state):
        """Potential over- & underlined title."""
        lineno = self.state_machine.abs_line_number() - 1
        overline = context[0]
        title = match.string
        underline = ''
        try:
            underline = self.state_machine.next_line()
        except EOFError:
            blocktext = overline + '\n' + title
            if len(overline.rstrip()) < 4:
                self.short_overline(context, blocktext, lineno, 2)
            else:
                msg = self.reporter.severe(
                    'Incomplete section title.',
                    nodes.literal_block(blocktext, blocktext),
                    line=lineno)
                self.parent += msg
                return [], 'Body', []
        source = '%s\n%s\n%s' % (overline, title, underline)
        overline = overline.rstrip()
        underline = underline.rstrip()
        if not self.transitions['underline'][0].match(underline):
            blocktext = overline + '\n' + title + '\n' + underline
            if len(overline.rstrip()) < 4:
                self.short_overline(context, blocktext, lineno, 2)
            else:
                msg = self.reporter.severe(
                    'Missing matching underline for section title overline.',
                    nodes.literal_block(source, source),
                    line=lineno)
                self.parent += msg
                return [], 'Body', []
        elif overline != underline:
            blocktext = overline + '\n' + title + '\n' + underline
            if len(overline.rstrip()) < 4:
                self.short_overline(context, blocktext, lineno, 2)
            else:
                msg = self.reporter.severe(
                      'Title overline & underline mismatch.',
                      nodes.literal_block(source, source),
                      line=lineno)
                self.parent += msg
                return [], 'Body', []
        title = title.rstrip()
        messages = []
        if column_width(title) > len(overline):
            blocktext = overline + '\n' + title + '\n' + underline
            if len(overline.rstrip()) < 4:
                self.short_overline(context, blocktext, lineno, 2)
            else:
                msg = self.reporter.warning(
                      'Title overline too short.',
                      nodes.literal_block(source, source),
                      line=lineno)
                messages.append(msg)
        style = (overline[0], underline[0])
        self.eofcheck = 0               # @@@ not sure this is correct
        self.section(title.lstrip(), source, style, lineno + 1, messages)
        self.eofcheck = 1
        return [], 'Body', []

    indent = text                       # indented title

    def underline(self, match, context, next_state):
        overline = context[0]
        blocktext = overline + '\n' + self.state_machine.line
        lineno = self.state_machine.abs_line_number() - 1
        if len(overline.rstrip()) < 4:
            self.short_overline(context, blocktext, lineno, 1)
        msg = self.reporter.error(
              'Invalid section title or transition marker.',
              nodes.literal_block(blocktext, blocktext),
              line=lineno)
        self.parent += msg
        return [], 'Body', []

    def short_overline(self, context, blocktext, lineno, lines=1):
        msg = self.reporter.info(
            'Possible incomplete section title.\nTreating the overline as '
            "ordinary text because it's so short.",
            line=lineno)
        self.parent += msg
        self.state_correction(context, lines)

    def state_correction(self, context, lines=1):
        self.state_machine.previous_line(lines)
        context[:] = []
        raise statemachine.StateCorrection('Body', 'text')


class QuotedLiteralBlock(RSTState):

    """
    Nested parse handler for quoted (unindented) literal blocks.

    Special-purpose.  Not for inclusion in `state_classes`.
    """

    patterns = {'initial_quoted': r'(%(nonalphanum7bit)s)' % Body.pats,
                'text': r''}
    initial_transitions = ('initial_quoted', 'text')

    def __init__(self, state_machine, debug=False):
        RSTState.__init__(self, state_machine, debug)
        self.messages = []
        self.initial_lineno = None

    def blank(self, match, context, next_state):
        if context:
            raise EOFError
        else:
            return context, next_state, []

    def eof(self, context):
        if context:
            src, srcline = self.state_machine.get_source_and_line(
                                                        self.initial_lineno)
            text = '\n'.join(context)
            literal_block = nodes.literal_block(text, text)
            literal_block.source = src
            literal_block.line = srcline
            self.parent += literal_block
        else:
            self.parent += self.reporter.warning(
                'Literal block expected; none found.',
                line=self.state_machine.abs_line_number()
                )  # src not available, statemachine.input_lines is empty
            self.state_machine.previous_line()
        self.parent += self.messages
        return []

    def indent(self, match, context, next_state):
        assert context, ('QuotedLiteralBlock.indent: context should not '
                         'be empty!')
        self.messages.append(
            self.reporter.error('Unexpected indentation.',
                                line=self.state_machine.abs_line_number()))
        self.state_machine.previous_line()
        raise EOFError

    def initial_quoted(self, match, context, next_state):
        """Match arbitrary quote character on the first line only."""
        self.remove_transition('initial_quoted')
        quote = match.string[0]
        pattern = re.compile(re.escape(quote))
        # New transition matches consistent quotes only:
        self.add_transition('quoted',
                            (pattern, self.quoted, self.__class__.__name__))
        self.initial_lineno = self.state_machine.abs_line_number()
        return [match.string], next_state, []

    def quoted(self, match, context, next_state):
        """Match consistent quotes on subsequent lines."""
        context.append(match.string)
        return context, next_state, []

    def text(self, match, context, next_state):
        if context:
            self.messages.append(
                self.reporter.error('Inconsistent literal block quoting.',
                                    line=self.state_machine.abs_line_number()))
            self.state_machine.previous_line()
        raise EOFError


state_classes = (Body, BulletList, DefinitionList, EnumeratedList, FieldList,
                 OptionList, LineBlock, ExtensionOptions, Explicit, Text,
                 Definition, Line, SubstitutionDef, RFC2822Body, RFC2822List)
"""Standard set of State classes used to start `RSTStateMachine`."""
