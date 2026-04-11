# $Id: manpage.py 10161 2025-06-10 19:50:50Z grubert $
# Author: Engelbert Gruber <grubert@users.sourceforge.net>
# Copyright: This module is put into the public domain.

"""
Simple man page writer for reStructuredText.

Man pages (short for "manual pages") contain system documentation on unix-like
systems. The pages are grouped in numbered sections:

 1 executable programs and shell commands
 2 system calls
 3 library functions
 4 special files
 5 file formats
 6 games
 7 miscellaneous
 8 system administration

Man pages are written in the *roff* markup language.

See https://www.tldp.org/HOWTO/Man-Page for a start.

Man pages have no subsection only parts.
Standard parts

  Name ,
  Synopsis ,
  Description ,
  Options ,
  Files ,
  See also ,
  Bugs ,

and

  AUthor .

A unix-like system keeps an index of the Descriptions, which is accessible
by the command whatis or apropos.

"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

import re

import docutils
from docutils import frontend, nodes, writers, languages
from docutils.utils._roman_numerals import RomanNumeral

FIELD_LIST_INDENT = 7
DEFINITION_LIST_INDENT = 7
OPTION_LIST_INDENT = 7
BLOCKQOUTE_INDENT = 3.5
LITERAL_BLOCK_INDENT = 3.5

# Define two macros so man/roff can calculate the
# indent/unindent margins by itself
MACRO_DEF = r""".
.nr rst2man-indent-level 0
.
.de1 rstReportMargin
\\$1 \\n[an-margin]
level \\n[rst2man-indent-level]
level margin: \\n[rst2man-indent\\n[rst2man-indent-level]]
-
\\n[rst2man-indent0]
\\n[rst2man-indent1]
\\n[rst2man-indent2]
..
.de1 INDENT
.\" .rstReportMargin pre:
. RS \\$1
. nr rst2man-indent\\n[rst2man-indent-level] \\n[an-margin]
. nr rst2man-indent-level +1
.\" .rstReportMargin post:
..
.de UNINDENT
. RE
.\" indent \\n[an-margin]
.\" old: \\n[rst2man-indent\\n[rst2man-indent-level]]
.nr rst2man-indent-level -1
.\" new: \\n[rst2man-indent\\n[rst2man-indent-level]]
.in \\n[rst2man-indent\\n[rst2man-indent-level]]u
..
"""

# see groff_man_style recommends applying non-printing break points
# in long URIs.
NONPRINTING_BREAKPOINT = r'\:'

# after a slash series of
# after an at sign
# after question marks
# after ampersands
# after number signs
# (?=.) avoids matching the end of string, requires something
# MAYBE require 5 after the break point
NONBREAKING_INSERT_RE = re.compile(r'([/@?&#]+)(?=.{3,})')
# before each dot or a series of
NONBREAKING_INSERT_RE2 = re.compile(r'([^\.]+)(?=\.+)(?=.{3,})')


def insert_URI_breakpoints(s):
    # TODO only for long URIs ?
    return NONBREAKING_INSERT_RE2.sub(
               r'\1' + NONPRINTING_BREAKPOINT,
               NONBREAKING_INSERT_RE.sub(r'\1' + NONPRINTING_BREAKPOINT, s))


class Writer(writers.Writer):
    """
    manpage writer class
    """

    supported = ('manpage',)
    """Formats this writer supports."""

    settings_spec = (
        'Manpage Writer Options',
        None,
        (('Write references in plain text form. (default)',
          ['--text-references'],
          {'action': 'store_true',
           'default': True,  # remove in Docutils 1.0
           'validator': frontend.validate_boolean}),
         ('Use man macros UR and MT for references.',
          ['--macro-references'],
          {'dest': 'text_references',
           'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ),
        )

    config_section_dependencies = ('writers',)

    output = None
    """Final translated form of `document`."""

    def __init__(self) -> None:
        writers.Writer.__init__(self)
        self.translator_class = Translator

    def translate(self) -> None:
        visitor = self.translator_class(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.astext()


class Table:
    """
    man package table handling.
    """
    def __init__(self) -> None:
        self._rows = []
        self._options = ['box', 'center']
        self._tab_char = '\t'
        self._coldefs = []

    def new_row(self) -> None:
        self._rows.append([])

    def append_separator(self, separator) -> None:
        """Append the separator for table head."""
        self._rows.append([separator])

    def append_cell(self, cell_lines) -> None:
        """cell_lines is an array of lines"""
        start = 0
        if len(cell_lines) > 0 and cell_lines[0] == '.sp\n':
            start = 1
        self._rows[-1].append(cell_lines[start:])
        if len(self._coldefs) < len(self._rows[-1]):
            self._coldefs.append('l')

    def _minimize_cell(self, cell_lines) -> None:
        """Remove leading and trailing blank and ``.sp`` lines"""
        while cell_lines and cell_lines[0] in ('\n', '.sp\n'):
            del cell_lines[0]
        while cell_lines and cell_lines[-1] in ('\n', '.sp\n'):
            del cell_lines[-1]

    def as_list(self):
        text = ['.TS\n',
                ' '.join(self._options) + ';\n',
                '%s.\n' % '|'.join(self._coldefs),
                ]
        for row in self._rows:
            # row = array of cells. cell = array of lines.
            text.append('T{\n')
            for i in range(len(row)):
                cell = row[i]
                self._minimize_cell(cell)
                text.extend(cell)
                if not text[-1].endswith('\n'):
                    text[-1] += '\n'
                if i < len(row)-1:
                    text.append('T}'+self._tab_char+'T{\n')
                else:
                    text.append('T}\n')
            text.append('_\n')       # line between rows
        text.pop()     # pop last "line between"
        text.append('.TE\n')
        return text


class Translator(nodes.NodeVisitor):
    """
    Docutils to man page translator.

    Generate unix-like manual pages using the "man macro package"
    from a Docutils document tree.
    """

    words_and_spaces = re.compile(r'\S+| +|\n')
    possibly_a_roff_command = re.compile(r'\.\w')
    document_start = (
        'Man page generated from reStructuredText\n'
        f'by the Docutils {docutils.__version__} manpage writer.'
    )

    def __init__(self, document) -> None:
        nodes.NodeVisitor.__init__(self, document)
        self.settings = settings = document.settings
        if settings.text_references:
            self.visit_reference = self._visit_reference_no_macro
            self.depart_reference = self._depart_reference_no_macro
        else:
            self.visit_reference = self._visit_reference_with_macro
            self.depart_reference = self._depart_reference_with_macro
        lcode = settings.language_code
        self.language = languages.get_language(lcode, document.reporter)
        self.head = []
        self.body = []
        self.foot = []
        self.section_level = 0
        self.context = []
        self.topic_class = ''
        self.colspecs = []
        self.compact_p = 1
        self.compact_simple = None
        # the list style "*" bullet or "#" numbered
        self._list_char = []
        # writing the header .TH and .SH Name is postponed after docinfo.
        self._docinfo = {
                "title": "",
                "subtitle": "",
                "manual_section": "", "manual_group": "",
                "author": [],
                "date": "",
                "copyright": "",
                "version": "",
                    }
        self._docinfo_keys = []     # a list to keep the sequence as in source.
        self._docinfo_names = {}    # to get name from text not normalized.
        self._in_docinfo = None
        self._field_name = None
        self._active_table = None
        self._has_a_table = False   # is there a table in this document
        self._in_literal = False
        self.header_written = 0
        self._line_block = 0
        self.authors = []
        self.section_level = 0
        self._indent = [0]
        # Do not use paragraph requests ``.PP`` because these set indentation.
        # use ``.sp``. Remove superfluous ``.sp`` in ``astext``.

        # Fonts are put on a stack, the top one is used.
        # ``.ft P`` or ``\\fP`` pop from stack.
        # But ``.BI`` seams to fill stack with BIBIBIBIB...
        # ``B`` bold, ``I`` italic, ``R`` roman should be available.

        # from groff_man_style(7)
        #
        # \c   End a text line without inserting space or attempting a
        #      break. ...
        #      The next line is interpreted as usual and can include a
        #      macro call (contrast with \newline). ...
        #      useful when three font styles are needed in a single
        #      word, as in a command synopsis.
        #
        #             .RB [ \-\-stylesheet=\c
        #             .IR name ]

        # Requests start wit a dot ``.`` or the no-break control character,
        # a neutral apostrophe ``'`` suppresses the break implied by some
        # requests.

        # central definition of simple processing rules
        # what to output on : visit, depart
        self.defs = {
                'indent': ('.INDENT %.1f\n', '.UNINDENT\n'),
                'definition_list_item': ('.TP', ''),  # par. with hanging tag
                'field_name': ('.TP\n.B ', '\n'),
                'literal': ('\\fB', '\\fP'),
                'literal_block': ('.sp\n.EX\n', '\n.EE\n'),

                'option_list_item': ('.TP\n', ''),

                'emphasis': ('\\fI', '\\fP'),
                'strong': ('\\fB', '\\fP'),
                'title_reference': ('\\fI', '\\fP'),

                'topic-title': ('.SS ',),
                'sidebar-title': ('.SS ',),

                'problematic': ('\n.nf\n', '\n.fi\n'),
                    }
        # NOTE do not specify the newline before a dot-command, but ensure
        # it is there.

    def comment_begin(self, text):
        """Return commented version of the passed text WITHOUT end of
        line/comment."""
        prefix = '.\\" '
        out_text = ''.join([(prefix + in_line + '\n')
                            for in_line in text.split('\n')])
        return out_text

    def comment(self, text):
        """Return commented version of the passed text."""
        return self.comment_begin(text)+'.\n'

    def ensure_eol(self) -> None:
        """Ensure the last line in body is terminated by new line."""
        if len(self.body) > 0 and self.body[-1][-1] != '\n':
            self.body.append('\n')

    def ensure_c_eol(self) -> None:
        """Ensure the last line in body is terminated by new line."""
        if len(self.body) > 0 and self.body[-1][-1] != '\n':
            self.body.append('\\c\n')

    def astext(self):
        """Return the final formatted document as a string."""
        if not self.header_written:
            # ensure we get a ".TH" as viewers require it.
            self.append_header()
        # filter body
        for i in range(len(self.body)-1, 0, -1):
            # remove superfluous vertical gaps.
            if self.body[i] == '.sp\n':
                if self.body[i - 1][:4] in ('.BI ', '.IP '):
                    self.body[i] = '.\n'
                elif (self.body[i - 1][:3] == '.B '
                      and self.body[i - 2][:4] == '.TP\n'):
                    self.body[i] = '.\n'
                elif (self.body[i - 1] == '\n'
                      and not self.possibly_a_roff_command.match(
                                  self.body[i - 2])
                      and (self.body[i - 3][:7] == '.TP\n.B '
                           or self.body[i - 3][:4] == '\n.B ')
                      ):
                    self.body[i] = '.\n'
            elif self.body[i][:4] in ('.UE\n', '.ME\n'):
                # if next item starts with
                # a) a line end, disable it
                if self.body[i+1][0] in ('\n', '\r'):
                    self.body[i+1] = '.' + self.body[i+1]
                    # b) with a separator: moving the 1st char to current item
                    #    would require to check the second, use \c instead.
                else:
                    # append \c to end the text line, .ME or .UE without
                    # inserting space or attempting a break.
                    self.body[i] = "%s \\c\n" % (self.body[i][:3])
        return ''.join(self.head + self.body + self.foot)

    def deunicode(self, text):
        text = text.replace('\xa0', '\\ ')
        text = text.replace('\u2020', '\\(dg')
        return text

    def encode_special_chars(self, text):
        replace_pairs = [
            ('-', '\\-'),
            ('\'', '\\(aq'),
            ('´', "\\'"),
            ('`', '\\(ga'),
            ('"', '\\(dq'),  # double quotes are a problem on macro lines
            ]
        for (in_char, out_markup) in replace_pairs:
            text = text.replace(in_char, out_markup)
        return text

    def visit_Text(self, node) -> None:
        text = node.astext()
        text = text.replace('\\', '\\e')
        text = self.encode_special_chars(text)
        # unicode
        text = self.deunicode(text)
        # prevent interpretation of "." at line start
        if text.startswith('.'):
            text = '\\&' + text
        if self._in_literal:
            text = text.replace('\n.', '\n\\&.')
        self.body.append(text)

    def depart_Text(self, node) -> None:
        pass

    def list_start(self, node) -> None:
        class EnumChar:
            """list item numbering/markup handling"""
            enum_style = {
                    'bullet': '\\(bu',
                     }

            def __init__(self, style) -> None:
                self._style = style
                if 'start' in node:
                    self._cnt = node['start'] - 1
                else:
                    self._cnt = 0
                self._indent = 2
                if style == 'arabic':
                    # indentation depends on number of children
                    # and start value.
                    self._indent = len(str(len(node.children)))
                    self._indent += len(str(self._cnt)) + 1
                elif style == 'loweralpha':
                    self._cnt += ord('a') - 1
                    self._indent = 3
                elif style == 'upperalpha':
                    self._cnt += ord('A') - 1
                    self._indent = 3
                elif style.endswith('roman'):
                    self._indent = 5

            def __next__(self):
                if self._style == 'bullet':
                    return self.enum_style[self._style]
                self._cnt += 1
                # TODO add prefix postfix
                if self._style in ('loweralpha', 'upperalpha'):
                    return "%c." % self._cnt
                if self._style.endswith('roman'):
                    res = RomanNumeral(self._cnt)
                    if self._style.startswith('upper'):
                        return res.to_uppercase() + '.'
                    else:
                        return res.to_lowercase() + '.'
                # else 'arabic', ...
                return "%d." % self._cnt

            def get_width(self):
                return self._indent

            def __repr__(self) -> str:
                return 'enum_style-%s' % list(self._style)

        if 'enumtype' in node:
            self._list_char.append(EnumChar(node['enumtype']))
        else:
            # INFO node['bullet'] contains the bullet style "*+-"
            # BUT man pages only use "*".
            self._list_char.append(EnumChar('bullet'))
        if len(self._list_char) > 1:
            # indent nested lists
            self.indent(self._list_char[-2].get_width())
        else:
            self.indent(self._list_char[-1].get_width())

    def list_end(self) -> None:
        self.dedent()
        self._list_char.pop()

    def header(self):
        th = (".TH \"%(title)s\" \"%(manual_section)s\""
              " \"%(date)s\" \"%(version)s\"") % self._docinfo
        if self._docinfo["manual_group"]:
            th += " \"%(manual_group)s\"" % self._docinfo
        th += "\n"
        sh_tmpl = (".SH Name\n"
                   "%(title)s \\- %(subtitle)s\n")
        return th + sh_tmpl % self._docinfo

    def append_header(self) -> None:
        """append header with .TH and .SH Name"""
        # NOTE before everything
        # .TH title section date source manual
        # BUT macros before .TH for whatis database generators.
        if self.header_written:
            return
        self.head.append(MACRO_DEF)
        self.head.append(self.header())
        self.header_written = 1

    def visit_address(self, node) -> None:
        self.visit_docinfo_item(node, 'address')

    def depart_address(self, node) -> None:
        pass

    def visit_admonition(self, node, name=None) -> None:
        #
        # Make admonitions a simple block quote
        # with a strong heading
        #
        # Using .IP/.RE doesn't preserve indentation
        # when admonitions contain bullets, literal,
        # and/or block quotes.
        #
        if name:
            # .. admonition:: has no name
            self.body.append('.sp\n')
            name = '%s%s:%s\n' % (
                self.defs['strong'][0],
                self.language.labels.get(name, name),
                self.defs['strong'][1],
                )
            self.body.append(name)
        self.visit_block_quote(node)

    def depart_admonition(self, node) -> None:
        self.depart_block_quote(node)

    def visit_attention(self, node) -> None:
        self.visit_admonition(node, 'attention')

    depart_attention = depart_admonition

    def visit_docinfo_item(self, node, name):
        if name == 'author':
            self._docinfo[name].append(node.astext())
        else:
            self._docinfo[name] = node.astext()
        self._docinfo_keys.append(name)
        raise nodes.SkipNode

    def depart_docinfo_item(self, node) -> None:
        pass

    def visit_author(self, node) -> None:
        self.visit_docinfo_item(node, 'author')

    depart_author = depart_docinfo_item

    def visit_authors(self, node) -> None:
        # _author is called anyway.
        pass

    def depart_authors(self, node) -> None:
        pass

    def visit_block_quote(self, node) -> None:
        # BUG/HACK: indent always uses the _last_ indentation,
        # thus we need two of them.
        self.indent(BLOCKQOUTE_INDENT)
        self.indent(0)

    def depart_block_quote(self, node) -> None:
        self.dedent()
        self.dedent()

    def visit_bullet_list(self, node) -> None:
        self.list_start(node)

    def depart_bullet_list(self, node) -> None:
        self.list_end()

    def visit_caption(self, node) -> None:
        pass

    def depart_caption(self, node) -> None:
        pass

    def visit_caution(self, node) -> None:
        self.visit_admonition(node, 'caution')

    depart_caution = depart_admonition

    def visit_citation(self, node) -> None:
        num = node.astext().split(None, 1)[0]
        num = num.strip()
        self.body.append('.IP [%s] 5\n' % num)

    def depart_citation(self, node) -> None:
        pass

    def visit_citation_reference(self, node):
        self.body.append('['+node.astext()+']')
        raise nodes.SkipNode

    def visit_classifier(self, node) -> None:
        self.body.append('(')

    def depart_classifier(self, node) -> None:
        self.body.append(')')
        self.depart_term(node)  # close the term element after last classifier

    def visit_colspec(self, node) -> None:
        self.colspecs.append(node)

    def depart_colspec(self, node) -> None:
        pass

    def write_colspecs(self) -> None:
        self.body.append("%s.\n" % ('L '*len(self.colspecs)))

    def visit_comment(self, node,
                      sub=re.compile('-(?=-)').sub):
        self.body.append(self.comment(node.astext()))
        raise nodes.SkipNode

    def visit_contact(self, node) -> None:
        self.visit_docinfo_item(node, 'contact')

    depart_contact = depart_docinfo_item

    def visit_container(self, node) -> None:
        pass

    def depart_container(self, node) -> None:
        pass

    def visit_compound(self, node) -> None:
        pass

    def depart_compound(self, node) -> None:
        pass

    def visit_copyright(self, node) -> None:
        self.visit_docinfo_item(node, 'copyright')

    def visit_danger(self, node) -> None:
        self.visit_admonition(node, 'danger')

    depart_danger = depart_admonition

    def visit_date(self, node) -> None:
        self.visit_docinfo_item(node, 'date')

    def visit_decoration(self, node) -> None:
        pass

    def depart_decoration(self, node) -> None:
        pass

    def visit_definition(self, node) -> None:
        pass

    def depart_definition(self, node) -> None:
        pass

    def visit_definition_list(self, node) -> None:
        self.indent(DEFINITION_LIST_INDENT)

    def depart_definition_list(self, node) -> None:
        self.dedent()

    def visit_definition_list_item(self, node) -> None:
        self.body.append(self.defs['definition_list_item'][0])

    def depart_definition_list_item(self, node) -> None:
        self.body.append(self.defs['definition_list_item'][1])

    def visit_description(self, node) -> None:
        pass

    def depart_description(self, node) -> None:
        pass

    def visit_docinfo(self, node) -> None:
        self._in_docinfo = 1

    def depart_docinfo(self, node) -> None:
        self._in_docinfo = None
        # NOTE nothing should be written before this
        self.append_header()

    def visit_doctest_block(self, node) -> None:
        self.body.append(self.defs['literal_block'][0])
        self._in_literal = True

    def depart_doctest_block(self, node) -> None:
        self._in_literal = False
        self.body.append(self.defs['literal_block'][1])

    def visit_document(self, node) -> None:
        # no blank line between comment and header.
        self.head.append(self.comment(self.document_start).rstrip()+'\n')
        # writing header is postponed
        self.header_written = 0

    def depart_document(self, node) -> None:
        if self._docinfo['author']:
            self.body.append('.SH Author\n%s\n'
                             % ', '.join(self._docinfo['author']))
        skip = ('author', 'copyright', 'date',
                'manual_group', 'manual_section',
                'subtitle',
                'title', 'version')
        for name in self._docinfo_keys:
            if name == 'address':
                self.body.append("\n%s:\n%s%s.nf\n%s\n.fi\n%s%s" % (
                                    self.language.labels.get(name, name),
                                    self.defs['indent'][0] % 0,
                                    self.defs['indent'][0] % BLOCKQOUTE_INDENT,
                                    self._docinfo[name],
                                    self.defs['indent'][1],
                                    self.defs['indent'][1]))
            elif name not in skip:
                if name in self._docinfo_names:
                    label = self._docinfo_names[name]
                else:
                    label = self.language.labels.get(name, name)
                self.body.append("\n%s: %s\n" % (label, self._docinfo[name]))
        if self._docinfo['copyright']:
            self.body.append('.SH Copyright\n%s\n'
                             % self._docinfo['copyright'])
        self.body.append(self.comment_begin('End of generated man page.'))

    def visit_emphasis(self, node) -> None:
        self.body.append(self.defs['emphasis'][0])

    def depart_emphasis(self, node) -> None:
        self.body.append(self.defs['emphasis'][1])

    def visit_entry(self, node) -> None:
        # a cell in a table row
        if 'morerows' in node:
            self.document.reporter.warning(
                '"table row spanning" not supported', base_node=node)
        if 'morecols' in node:
            self.document.reporter.warning(
                '"table cell spanning" not supported', base_node=node)
        self.context.append(len(self.body))

    def depart_entry(self, node) -> None:
        start = self.context.pop()
        self._active_table.append_cell(self.body[start:])
        del self.body[start:]

    def visit_enumerated_list(self, node) -> None:
        self.list_start(node)

    def depart_enumerated_list(self, node) -> None:
        self.list_end()

    def visit_error(self, node) -> None:
        self.visit_admonition(node, 'error')

    depart_error = depart_admonition

    def visit_field(self, node) -> None:
        pass

    def depart_field(self, node) -> None:
        pass

    def visit_field_body(self, node):
        if self._in_docinfo:
            name_normalized = self._field_name.lower().replace(" ", "_")
            self._docinfo_names[name_normalized] = self._field_name
            self.visit_docinfo_item(node, name_normalized)
            raise nodes.SkipNode

    def depart_field_body(self, node) -> None:
        pass

    def visit_field_list(self, node) -> None:
        self.indent(FIELD_LIST_INDENT)

    def depart_field_list(self, node) -> None:
        self.dedent()

    def visit_field_name(self, node):
        if self._in_docinfo:
            self._field_name = node.astext()
            raise nodes.SkipNode
        self.body.append(self.defs['field_name'][0])

    def depart_field_name(self, node) -> None:
        self.body.append(self.defs['field_name'][1])

    def visit_figure(self, node) -> None:
        self.indent(2.5)
        self.indent(0)

    def depart_figure(self, node) -> None:
        self.dedent()
        self.dedent()

    def visit_footer(self, node):
        self.document.reporter.warning('"footer" not supported',
                                       base_node=node)
        # avoid output the link to document source
        raise nodes.SkipNode

    def depart_footer(self, node) -> None:
        pass

    def visit_footnote(self, node) -> None:
        num, _text = node.astext().split(maxsplit=1)
        num = num.strip()
        self.body.append('.IP [%s] 5\n' % self.deunicode(num))

    def depart_footnote(self, node) -> None:
        pass

    def footnote_backrefs(self, node) -> None:
        self.document.reporter.warning('"footnote_backrefs" not supported',
                                       base_node=node)

    def visit_footnote_reference(self, node):
        self.body.append('['+self.deunicode(node.astext())+']')
        raise nodes.SkipNode

    def depart_footnote_reference(self, node) -> None:
        pass

    def visit_generated(self, node) -> None:
        pass

    def depart_generated(self, node) -> None:
        pass

    def visit_header(self, node):
        raise NotImplementedError(node.astext())

    def depart_header(self, node) -> None:
        pass

    def visit_hint(self, node) -> None:
        self.visit_admonition(node, 'hint')

    depart_hint = depart_admonition

    def visit_subscript(self, node) -> None:
        self.body.append('\\s-2\\d')

    def depart_subscript(self, node) -> None:
        self.body.append('\\u\\s0')

    def visit_superscript(self, node) -> None:
        self.body.append('\\s-2\\u')

    def depart_superscript(self, node) -> None:
        self.body.append('\\d\\s0')

    def visit_attribution(self, node) -> None:
        self.body.append('\\(em ')

    def depart_attribution(self, node) -> None:
        self.body.append('\n')

    def visit_image(self, node):
        msg = '"image" not supported by "manpage" writer.'
        if 'alt' in node.attributes:
            self.document.reporter.info(msg,
                                        base_node=node)
            self.body.append('.sp\n    %s\n' % (
                    node.attributes['alt']))
        elif 'uri' in node.attributes:
            self.body.append('.sp\n    image: %s\n' % (
                    node.attributes['uri']))
            self.document.reporter.warning(
                    f'{msg}\nPlease provide an "alt" attribute with textual'
                    ' replacement.', base_node=node)
        # else 0 arguments to image not allowed
        raise nodes.SkipNode

    def visit_important(self, node) -> None:
        self.visit_admonition(node, 'important')

    depart_important = depart_admonition

    def visit_inline(self, node) -> None:
        pass

    def depart_inline(self, node) -> None:
        pass

    def visit_label(self, node):
        # footnote and citation labels are written in their visit_ functions.
        if isinstance(node.parent, (nodes.footnote, nodes.citation)):
            raise nodes.SkipNode
        self.document.reporter.warning('"unsupported "label"',
                                       base_node=node)
        self.body.append('[')

    def depart_label(self, node) -> None:
        self.body.append(']\n')

    def visit_legend(self, node) -> None:
        pass

    def depart_legend(self, node) -> None:
        pass

    # WHAT should we use .INDENT, .UNINDENT ?
    def visit_line_block(self, node) -> None:
        self._line_block += 1
        if self._line_block == 1:
            # TODO: separate inline blocks from previous paragraphs
            # see http://hg.intevation.org/mercurial/crew/rev/9c142ed9c405
            # self.body.append('.sp\n')
            # but it does not work for me.
            self.body.append('.nf\n')
        else:
            self.body.append('.in +2\n')

    def depart_line_block(self, node) -> None:
        self._line_block -= 1
        if self._line_block == 0:
            self.body.append('.fi\n')
            self.body.append('.sp\n')
        else:
            self.body.append('.in -2\n')

    def visit_line(self, node) -> None:
        pass

    def depart_line(self, node) -> None:
        self.body.append('\n')

    def visit_list_item(self, node) -> None:
        # man 7 man argues to use ".IP" instead of ".TP"
        self.body.append('.IP %s %d\n' % (
                next(self._list_char[-1]),
                self._list_char[-1].get_width(),))

    def depart_list_item(self, node) -> None:
        pass

    def visit_literal(self, node) -> None:
        self.body.append(self.defs['literal'][0])

    def depart_literal(self, node) -> None:
        self.body.append(self.defs['literal'][1])

    def visit_literal_block(self, node) -> None:
        # BUG/HACK: indent always uses the _last_ indentation,
        # thus we need two of them.
        self.indent(LITERAL_BLOCK_INDENT)
        self.indent(0)
        self.body.append(self.defs['literal_block'][0])
        self._in_literal = True

    def depart_literal_block(self, node) -> None:
        self._in_literal = False
        self.body.append(self.defs['literal_block'][1])
        self.dedent()
        self.dedent()

    def visit_math(self, node) -> None:
        self.document.reporter.warning('"math" role not supported',
                                       base_node=node)
        self.visit_literal(node)

    def depart_math(self, node) -> None:
        self.depart_literal(node)

    def visit_math_block(self, node) -> None:
        self.document.reporter.warning('"math" directive not supported',
                                       base_node=node)
        self.visit_literal_block(node)

    def depart_math_block(self, node) -> None:
        self.depart_literal_block(node)

    # <meta> shall become an optional standard node:
    # def visit_meta(self, node):
    #     raise NotImplementedError(node.astext())

    # def depart_meta(self, node):
    #     pass

    def visit_note(self, node) -> None:
        self.visit_admonition(node, 'note')

    depart_note = depart_admonition

    def indent(self, by=0.5) -> None:
        # if we are in a section ".SH" there already is a .RS
        step = self._indent[-1]
        self._indent.append(by)
        self.body.append(self.defs['indent'][0] % step)

    def dedent(self) -> None:
        self._indent.pop()
        self.body.append(self.defs['indent'][1])

    def visit_option_list(self, node) -> None:
        self.indent(OPTION_LIST_INDENT)

    def depart_option_list(self, node) -> None:
        self.dedent()

    def visit_option_list_item(self, node) -> None:
        # one item of the list
        self.body.append(self.defs['option_list_item'][0])

    def depart_option_list_item(self, node) -> None:
        self.body.append(self.defs['option_list_item'][1])

    def visit_option_group(self, node) -> None:
        # as one option could have several forms it is a group
        # options without parameter bold only, .B, -v
        # options with parameter bold italic, .BI, -f file
        #
        # we do not know if .B or .BI, blind guess:
        self.context.append('.B ')  # Add blank for sphinx (docutils/bugs/380)
        self.context.append(len(self.body))  # to be able to insert later
        self.context.append(0)               # option counter

    def depart_option_group(self, node) -> None:
        self.context.pop()  # the counter
        start_position = self.context.pop()
        text = self.body[start_position:]
        del self.body[start_position:]
        self.body.append('%s%s\n' % (self.context.pop(), ''.join(text)))

    def visit_option(self, node) -> None:
        # each form of the option will be presented separately
        if self.context[-1] > 0:
            if self.context[-3] == '.BI':
                self.body.append('\\fR,\\fB ')
            else:
                self.body.append('\\fP,\\fB ')
        if self.context[-3] == '.BI':
            self.body.append('\\')
        self.body.append(' ')

    def depart_option(self, node) -> None:
        self.context[-1] += 1

    def visit_option_string(self, node) -> None:
        # do not know if .B or .BI
        pass

    def depart_option_string(self, node) -> None:
        pass

    def visit_option_argument(self, node) -> None:
        self.context[-3] = '.BI'  # bold/italic alternate
        if node['delimiter'] != ' ':
            self.body.append('\\fB%s ' % node['delimiter'])
        elif self.body[len(self.body)-1].endswith('='):
            # a blank only means no blank in output, just changing font
            self.body.append(' ')
        else:
            # blank backslash blank, switch font then a blank
            self.body.append(' \\ ')

    def depart_option_argument(self, node) -> None:
        pass

    def visit_organization(self, node) -> None:
        self.visit_docinfo_item(node, 'organization')

    def depart_organization(self, node) -> None:
        pass

    def first_child(self, node) -> int:
        first = isinstance(node.parent[0], nodes.label)  # skip label
        for child in node.parent.children[first:]:
            if isinstance(child, nodes.Invisible):
                continue
            if child is node:
                return 1
            break
        return 0

    def visit_paragraph(self, node) -> None:
        # ``.PP`` : Start standard indented paragraph.
        # ``.LP`` : Start block paragraph, all except the first.
        # ``.P [type]``  : Start paragraph type.
        # NOTE do not use paragraph starts because they reset indentation.
        # ``.sp`` is only vertical space
        self.ensure_eol()
        if not self.first_child(node):
            self.body.append('.sp\n')
        # set in literal to escape dots after a new-line-character
        self._in_literal = True

    def depart_paragraph(self, node) -> None:
        self._in_literal = False
        self.body.append('\n')

    def visit_problematic(self, node) -> None:
        self.body.append(self.defs['problematic'][0])

    def depart_problematic(self, node) -> None:
        self.body.append(self.defs['problematic'][1])

    def visit_raw(self, node):
        if 'manpage' in node.get('format', '').split():
            self.body.append(node.astext() + "\n")
        # Keep non-manpage raw text out of output:
        raise nodes.SkipNode

    # references ----

    def _visit_reference_no_macro(self, node) -> None:
        """E.g. link or email address."""
        # For .UR/.UE and .MT/.ME macros groff might use OSC8 escape sequences
        # which are not supported everywhere yet
        # therefore make the markup ourself

        # precede with backslash-% to disable standard hyphenation
        if 'refuri' in node:
            # check if content is the uri and only output reference.
            # MAYBE if only content is ouput hyphens "-" get a backslash.
            if (node['refuri'] == node.astext()
                or node['refuri'] == "mailto:"+node.astext()):
                # without mailto:
                self.body.append(r"\%%<%s>"
                                 % insert_URI_breakpoints(node.astext()))
                raise nodes.SkipNode
        # TODO markup the target
        # elif 'refid' in node:
        #     internal cross references are ignored (just print the text)

    def _depart_reference_no_macro(self, node) -> None:
        if 'refuri' in node:
            self.body.append(r" \%%<%s>"
                             % insert_URI_breakpoints(node['refuri']))
        # elif 'refid' in node:

    def _visit_reference_with_macro(self, node) -> None:
        # use UR/UE or MT/ME
        if 'refuri' in node:
            self.ensure_c_eol()  # c_eol avoids space before the refuri
            _uri = node['refuri']
            if _uri.startswith('mailto:'):
                _uri = _uri[7:]  # remove "mailto:"
                # groff macro in an.tmac adds "mailto:"
                # mandoc does not.
                self.body.append(".MT ")
                self.context.append('.ME\n')
            else:
                self.body.append(".UR ")
                self.context.append('.UE\n')
            self.body.append("\\%%%s\n" % insert_URI_breakpoints(_uri))
            if (node['refuri'] == node.astext()
                or node['refuri'] == "mailto:"+node.astext()):
                self.body.append(self.context.pop())
                # if content is uri skip content
                raise nodes.SkipNode
        else:
            # TODO markup the target
            self.context.append('')

    def _depart_reference_with_macro(self, node) -> None:
        macro_end = self.context.pop()
        if macro_end:
            self.ensure_eol()
            self.body.append(macro_end)
        # problems to handle in astext looking ahead.
        # * if the ref is at end of line
        #   we get a blank line following which we dont want.
        # * if ref is followed by )., there will be a space separating
    # ----

    def visit_revision(self, node) -> None:
        self.visit_docinfo_item(node, 'revision')

    depart_revision = depart_docinfo_item

    def visit_row(self, node) -> None:
        self._active_table.new_row()

    def depart_row(self, node) -> None:
        pass

    def visit_section(self, node) -> None:
        self.section_level += 1

    def depart_section(self, node) -> None:
        self.section_level -= 1

    def visit_status(self, node) -> None:
        self.visit_docinfo_item(node, 'status')

    depart_status = depart_docinfo_item

    def visit_strong(self, node) -> None:
        self.body.append(self.defs['strong'][0])

    def depart_strong(self, node) -> None:
        self.body.append(self.defs['strong'][1])

    def visit_substitution_definition(self, node):
        """Internal only."""
        raise nodes.SkipNode

    def visit_substitution_reference(self, node) -> None:
        self.document.reporter.warning(
            '"substitution_reference" not supported', base_node=node)

    def visit_subtitle(self, node) -> None:
        if isinstance(node.parent, nodes.sidebar):
            self.body.append(self.defs['strong'][0])
        elif isinstance(node.parent, nodes.document):
            self.visit_docinfo_item(node, 'subtitle')
        elif isinstance(node.parent, nodes.section):
            self.body.append(self.defs['strong'][0])

    def depart_subtitle(self, node) -> None:
        # document subtitle calls SkipNode
        self.body.append(self.defs['strong'][1]+'\n.PP\n')

    def visit_system_message(self, node) -> None:
        # TODO add report_level
        # if node['level'] < self.document.reporter['writer'].report_level:
        #    Level is too low to display:
        #    raise nodes.SkipNode
        attr = {}
        if node.hasattr('id'):
            attr['name'] = node['id']
        if node.hasattr('line'):
            line = ', line %s' % node['line']
        else:
            line = ''
        self.body.append('.IP "System Message: %s/%s (%s:%s)"\n'
                         % (node['type'], node['level'], node['source'], line))

    def depart_system_message(self, node) -> None:
        pass

    def visit_table(self, node) -> None:
        self._active_table = Table()
        if not self._has_a_table:
            self._has_a_table = True
            # the comment to hint that preprocessor tbl should be called
            self.head.insert(0, "'\\\" t\n")  # ``'\" t`` + newline

    def depart_table(self, node) -> None:
        self.ensure_eol()
        self.body.extend(self._active_table.as_list())
        self._active_table = None

    def visit_target(self, node):
        # <target> elements are anchors of internal hyperlinks (not used
        # in man-pages). Just print content (inline targets may contain text):
        pass

    def depart_target(self, node):
        pass

    def visit_tbody(self, node) -> None:
        pass

    def depart_tbody(self, node) -> None:
        pass

    def visit_term(self, node) -> None:
        self.body.append('\n.B ')

    def depart_term(self, node) -> None:
        _next = node.next_node(None, descend=False, siblings=True)
        # Nest (optional) classifier(s) in the <term> element
        if isinstance(_next, nodes.classifier):
            self.body.append(' ')
            return  # skip (depart_classifier() calls this function again)
        if isinstance(_next, nodes.term):
            # .TQ  Additional paragraph tag
            self.body.append('\n.TQ')
        else:
            self.body.append('\n')

    def visit_tgroup(self, node) -> None:
        pass

    def depart_tgroup(self, node) -> None:
        pass

    def visit_thead(self, node) -> None:
        # MAYBE double line '='
        pass

    def depart_thead(self, node) -> None:
        # MAYBE double line '='
        pass

    def visit_tip(self, node) -> None:
        self.visit_admonition(node, 'tip')

    depart_tip = depart_admonition

    def visit_title(self, node):
        if isinstance(node.parent, nodes.topic):
            self.body.append(self.defs['topic-title'][0])
        elif isinstance(node.parent, nodes.sidebar):
            self.body.append(self.defs['sidebar-title'][0])
        elif isinstance(node.parent, nodes.admonition):
            self.body.append('.IP "')
        elif self.section_level == 0:
            self._docinfo['title'] = node.astext()
            raise nodes.SkipNode
        elif self.section_level == 1:
            self.body.append('.SH %s\n'%self.deunicode(node.astext()))
            raise nodes.SkipNode
        else:
            self.body.append('.SS ')

    def depart_title(self, node) -> None:
        if isinstance(node.parent, nodes.admonition):
            self.body.append('"')
        self.body.append('\n')

    def visit_title_reference(self, node) -> None:
        """inline citation reference"""
        self.body.append(self.defs['title_reference'][0])

    def depart_title_reference(self, node) -> None:
        self.body.append(self.defs['title_reference'][1])

    def visit_topic(self, node) -> None:
        pass

    def depart_topic(self, node) -> None:
        pass

    def visit_sidebar(self, node) -> None:
        pass

    def depart_sidebar(self, node) -> None:
        pass

    def visit_rubric(self, node) -> None:
        pass

    def depart_rubric(self, node) -> None:
        self.body.append('\n')

    def visit_transition(self, node) -> None:
        # .PP      Begin a new paragraph and reset prevailing indent.
        # .sp N    leaves N lines of blank space.
        # .ce      centers the next line
        self.body.append('\n.sp\n.ce\n----\n')

    def depart_transition(self, node) -> None:
        self.body.append('\n.ce 0\n.sp\n')

    def visit_version(self, node) -> None:
        self.visit_docinfo_item(node, 'version')

    def visit_warning(self, node) -> None:
        self.visit_admonition(node, 'warning')

    depart_warning = depart_admonition

    def unimplemented_visit(self, node):
        raise NotImplementedError('visiting unimplemented node type: %s'
                                  % node.__class__.__name__)

# vim: set fileencoding=utf-8 et ts=4 ai :
