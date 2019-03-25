# -*- coding: utf-8 -*-
"""
    sphinx.writers.text
    ~~~~~~~~~~~~~~~~~~~

    Custom docutils writer for plain text.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import os
import re
import textwrap
from itertools import groupby

from docutils import nodes, writers
from docutils.utils import column_width
from six.moves import zip_longest

from sphinx import addnodes
from sphinx.locale import admonitionlabels, _
from sphinx.util import logging

if False:
    # For type annotation
    from typing import Any, Callable, Dict, List, Tuple, Union  # NOQA
    from sphinx.builders.text import TextBuilder  # NOQA

logger = logging.getLogger(__name__)


class TextWrapper(textwrap.TextWrapper):
    """Custom subclass that uses a different word separator regex."""

    wordsep_re = re.compile(
        r'(\s+|'                                  # any whitespace
        r'(?<=\s)(?::[a-z-]+:)?`\S+|'             # interpreted text start
        r'[^\s\w]*\w+[a-zA-Z]-(?=\w+[a-zA-Z])|'   # hyphenated words
        r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w))')   # em-dash

    def _wrap_chunks(self, chunks):
        # type: (List[unicode]) -> List[unicode]
        """_wrap_chunks(chunks : [string]) -> [string]

        The original _wrap_chunks uses len() to calculate width.
        This method respects wide/fullwidth characters for width adjustment.
        """
        drop_whitespace = getattr(self, 'drop_whitespace', True)  # py25 compat
        lines = []  # type: List[unicode]
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)

        chunks.reverse()

        while chunks:
            cur_line = []
            cur_len = 0

            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent

            width = self.width - column_width(indent)

            if drop_whitespace and chunks[-1].strip() == '' and lines:
                del chunks[-1]

            while chunks:
                l = column_width(chunks[-1])

                if cur_len + l <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l

                else:
                    break

            if chunks and column_width(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)

            if drop_whitespace and cur_line and cur_line[-1].strip() == '':
                del cur_line[-1]

            if cur_line:
                lines.append(indent + ''.join(cur_line))

        return lines

    def _break_word(self, word, space_left):
        # type: (unicode, int) -> Tuple[unicode, unicode]
        """_break_word(word : string, space_left : int) -> (string, string)

        Break line by unicode width instead of len(word).
        """
        total = 0
        for i, c in enumerate(word):
            total += column_width(c)
            if total > space_left:
                return word[:i - 1], word[i - 1:]
        return word, ''

    def _split(self, text):
        # type: (unicode) -> List[unicode]
        """_split(text : string) -> [string]

        Override original method that only split by 'wordsep_re'.
        This '_split' split wide-characters into chunk by one character.
        """
        def split(t):
            # type: (unicode) -> List[unicode]
            return textwrap.TextWrapper._split(self, t)  # type: ignore
        chunks = []  # type: List[unicode]
        for chunk in split(text):
            for w, g in groupby(chunk, column_width):
                if w == 1:
                    chunks.extend(split(''.join(g)))
                else:
                    chunks.extend(list(g))
        return chunks

    def _handle_long_word(self, reversed_chunks, cur_line, cur_len, width):
        # type: (List[unicode], List[unicode], int, int) -> None
        """_handle_long_word(chunks : [string],
                             cur_line : [string],
                             cur_len : int, width : int)

        Override original method for using self._break_word() instead of slice.
        """
        space_left = max(width - cur_len, 1)
        if self.break_long_words:
            l, r = self._break_word(reversed_chunks[-1], space_left)
            cur_line.append(l)
            reversed_chunks[-1] = r

        elif not cur_line:
            cur_line.append(reversed_chunks.pop())


MAXWIDTH = 70
STDINDENT = 3


def my_wrap(text, width=MAXWIDTH, **kwargs):
    # type: (unicode, int, Any) -> List[unicode]
    w = TextWrapper(width=width, **kwargs)
    return w.wrap(text)


class TextWriter(writers.Writer):
    supported = ('text',)
    settings_spec = ('No options here.', '', ())
    settings_defaults = {}  # type: Dict

    output = None

    def __init__(self, builder):
        # type: (TextBuilder) -> None
        writers.Writer.__init__(self)
        self.builder = builder

    def translate(self):
        # type: () -> None
        visitor = self.builder.create_translator(self.document, self.builder)
        self.document.walkabout(visitor)
        self.output = visitor.body


class TextTranslator(nodes.NodeVisitor):
    sectionchars = '*=-~"+`'

    def __init__(self, document, builder):
        # type: (nodes.Node, TextBuilder) -> None
        nodes.NodeVisitor.__init__(self, document)
        self.builder = builder

        newlines = builder.config.text_newlines
        if newlines == 'windows':
            self.nl = '\r\n'
        elif newlines == 'native':
            self.nl = os.linesep
        else:
            self.nl = '\n'
        self.sectionchars = builder.config.text_sectionchars
        self.add_secnumbers = builder.config.text_add_secnumbers
        self.secnumber_suffix = builder.config.text_secnumber_suffix
        self.states = [[]]      # type: List[List[Tuple[int, Union[unicode, List[unicode]]]]]
        self.stateindent = [0]
        self.list_counter = []  # type: List[int]
        self.sectionlevel = 0
        self.lineblocklevel = 0
        self.table = None       # type: List[Union[unicode, List[int]]]

    def add_text(self, text):
        # type: (unicode) -> None
        self.states[-1].append((-1, text))

    def new_state(self, indent=STDINDENT):
        # type: (int) -> None
        self.states.append([])
        self.stateindent.append(indent)

    def end_state(self, wrap=True, end=[''], first=None):
        # type: (bool, List[unicode], unicode) -> None
        content = self.states.pop()
        maxindent = sum(self.stateindent)
        indent = self.stateindent.pop()
        result = []     # type: List[Tuple[int, List[unicode]]]
        toformat = []   # type: List[unicode]

        def do_format():
            # type: () -> None
            if not toformat:
                return
            if wrap:
                res = my_wrap(''.join(toformat), width=MAXWIDTH - maxindent)
            else:
                res = ''.join(toformat).splitlines()
            if end:
                res += end
            result.append((indent, res))
        for itemindent, item in content:
            if itemindent == -1:
                toformat.append(item)  # type: ignore
            else:
                do_format()
                result.append((indent + itemindent, item))  # type: ignore
                toformat = []
        do_format()
        if first is not None and result:
            itemindent, item = result[0]
            result_rest, result = result[1:], []
            if item:
                toformat = [first + ' '.join(item)]
                do_format()  # re-create `result` from `toformat`
                _dummy, new_item = result[0]
                result.insert(0, (itemindent - indent, [new_item[0]]))
                result[1] = (itemindent, new_item[1:])
                result.extend(result_rest)
        self.states[-1].extend(result)

    def visit_document(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)

    def depart_document(self, node):
        # type: (nodes.Node) -> None
        self.end_state()
        self.body = self.nl.join(line and (' ' * indent + line)
                                 for indent, lines in self.states[0]
                                 for line in lines)
        # XXX header/footer?

    def visit_section(self, node):
        # type: (nodes.Node) -> None
        self._title_char = self.sectionchars[self.sectionlevel]
        self.sectionlevel += 1

    def depart_section(self, node):
        # type: (nodes.Node) -> None
        self.sectionlevel -= 1

    def visit_topic(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)

    def depart_topic(self, node):
        # type: (nodes.Node) -> None
        self.end_state()

    visit_sidebar = visit_topic
    depart_sidebar = depart_topic

    def visit_rubric(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)
        self.add_text('-[ ')

    def depart_rubric(self, node):
        # type: (nodes.Node) -> None
        self.add_text(' ]-')
        self.end_state()

    def visit_compound(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_compound(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_glossary(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_glossary(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_title(self, node):
        # type: (nodes.Node) -> None
        if isinstance(node.parent, nodes.Admonition):
            self.add_text(node.astext() + ': ')
            raise nodes.SkipNode
        self.new_state(0)

    def get_section_number_string(self, node):
        # type: (nodes.Node) -> unicode
        if isinstance(node.parent, nodes.section):
            anchorname = '#' + node.parent['ids'][0]
            numbers = self.builder.secnumbers.get(anchorname)
            if numbers is None:
                numbers = self.builder.secnumbers.get('')
            if numbers is not None:
                return '.'.join(map(str, numbers)) + self.secnumber_suffix
        return ''

    def depart_title(self, node):
        # type: (nodes.Node) -> None
        if isinstance(node.parent, nodes.section):
            char = self._title_char
        else:
            char = '^'
        text = None  # type: unicode
        text = ''.join(x[1] for x in self.states.pop() if x[0] == -1)  # type: ignore
        if self.add_secnumbers:
            text = self.get_section_number_string(node) + text
        self.stateindent.pop()
        title = ['', text, '%s' % (char * column_width(text)), '']  # type: List[unicode]
        if len(self.states) == 2 and len(self.states[-1]) == 0:
            # remove an empty line before title if it is first section title in the document
            title.pop(0)
        self.states[-1].append((0, title))

    def visit_subtitle(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_subtitle(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_attribution(self, node):
        # type: (nodes.Node) -> None
        self.add_text('-- ')

    def depart_attribution(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_signature(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)

    def depart_desc_signature(self, node):
        # type: (nodes.Node) -> None
        # XXX: wrap signatures in a way that makes sense
        self.end_state(wrap=False, end=None)

    def visit_desc_signature_line(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_signature_line(self, node):
        # type: (nodes.Node) -> None
        self.add_text('\n')

    def visit_desc_name(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_name(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_addname(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_addname(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_type(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_type(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_returns(self, node):
        # type: (nodes.Node) -> None
        self.add_text(' -> ')

    def depart_desc_returns(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_parameterlist(self, node):
        # type: (nodes.Node) -> None
        self.add_text('(')
        self.first_param = 1

    def depart_desc_parameterlist(self, node):
        # type: (nodes.Node) -> None
        self.add_text(')')

    def visit_desc_parameter(self, node):
        # type: (nodes.Node) -> None
        if not self.first_param:
            self.add_text(', ')
        else:
            self.first_param = 0
        self.add_text(node.astext())
        raise nodes.SkipNode

    def visit_desc_optional(self, node):
        # type: (nodes.Node) -> None
        self.add_text('[')

    def depart_desc_optional(self, node):
        # type: (nodes.Node) -> None
        self.add_text(']')

    def visit_desc_annotation(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_annotation(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_content(self, node):
        # type: (nodes.Node) -> None
        self.new_state()
        self.add_text(self.nl)

    def depart_desc_content(self, node):
        # type: (nodes.Node) -> None
        self.end_state()

    def visit_figure(self, node):
        # type: (nodes.Node) -> None
        self.new_state()

    def depart_figure(self, node):
        # type: (nodes.Node) -> None
        self.end_state()

    def visit_caption(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_caption(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_productionlist(self, node):
        # type: (nodes.Node) -> None
        self.new_state()
        names = []
        for production in node:
            names.append(production['tokenname'])
        maxlen = max(len(name) for name in names)
        lastname = None
        for production in node:
            if production['tokenname']:
                self.add_text(production['tokenname'].ljust(maxlen) + ' ::=')
                lastname = production['tokenname']
            elif lastname is not None:
                self.add_text('%s    ' % (' ' * len(lastname)))
            self.add_text(production.astext() + self.nl)
        self.end_state(wrap=False)
        raise nodes.SkipNode

    def visit_footnote(self, node):
        # type: (nodes.Node) -> None
        self._footnote = node.children[0].astext().strip()
        self.new_state(len(self._footnote) + 3)

    def depart_footnote(self, node):
        # type: (nodes.Node) -> None
        self.end_state(first='[%s] ' % self._footnote)

    def visit_citation(self, node):
        # type: (nodes.Node) -> None
        if len(node) and isinstance(node[0], nodes.label):
            self._citlabel = node[0].astext()
        else:
            self._citlabel = ''
        self.new_state(len(self._citlabel) + 3)

    def depart_citation(self, node):
        # type: (nodes.Node) -> None
        self.end_state(first='[%s] ' % self._citlabel)

    def visit_label(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_legend(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_legend(self, node):
        # type: (nodes.Node) -> None
        pass

    # XXX: option list could use some better styling

    def visit_option_list(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_option_list(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_option_list_item(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)

    def depart_option_list_item(self, node):
        # type: (nodes.Node) -> None
        self.end_state()

    def visit_option_group(self, node):
        # type: (nodes.Node) -> None
        self._firstoption = True

    def depart_option_group(self, node):
        # type: (nodes.Node) -> None
        self.add_text('     ')

    def visit_option(self, node):
        # type: (nodes.Node) -> None
        if self._firstoption:
            self._firstoption = False
        else:
            self.add_text(', ')

    def depart_option(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_option_string(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_option_string(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_option_argument(self, node):
        # type: (nodes.Node) -> None
        self.add_text(node['delimiter'])

    def depart_option_argument(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_description(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_description(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_tabular_col_spec(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_colspec(self, node):
        # type: (nodes.Node) -> None
        self.table[0].append(node['colwidth'])  # type: ignore
        raise nodes.SkipNode

    def visit_tgroup(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_tgroup(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_thead(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_thead(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_tbody(self, node):
        # type: (nodes.Node) -> None
        self.table.append('sep')

    def depart_tbody(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_row(self, node):
        # type: (nodes.Node) -> None
        self.table.append([])

    def depart_row(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_entry(self, node):
        # type: (nodes.Node) -> None
        if 'morerows' in node or 'morecols' in node:
            raise NotImplementedError('Column or row spanning cells are '
                                      'not implemented.')
        self.new_state(0)

    def depart_entry(self, node):
        # type: (nodes.Node) -> None
        text = self.nl.join(self.nl.join(x[1]) for x in self.states.pop())
        self.stateindent.pop()
        self.table[-1].append(text)  # type: ignore

    def visit_table(self, node):
        # type: (nodes.Node) -> None
        if self.table:
            raise NotImplementedError('Nested tables are not supported.')
        self.new_state(0)
        self.table = [[]]

    def depart_table(self, node):
        # type: (nodes.Node) -> None
        lines = None                # type: List[unicode]
        lines = self.table[1:]      # type: ignore
        fmted_rows = []             # type: List[List[List[unicode]]]
        colwidths = None            # type: List[int]
        colwidths = self.table[0]   # type: ignore
        realwidths = colwidths[:]
        separator = 0
        # don't allow paragraphs in table cells for now
        for line in lines:
            if line == 'sep':
                separator = len(fmted_rows)
            else:
                cells = []  # type: List[List[unicode]]
                for i, cell in enumerate(line):
                    par = my_wrap(cell, width=colwidths[i])
                    if par:
                        maxwidth = max(column_width(x) for x in par)
                    else:
                        maxwidth = 0
                    realwidths[i] = max(realwidths[i], maxwidth)
                    cells.append(par)
                fmted_rows.append(cells)

        def writesep(char='-'):
            # type: (unicode) -> None
            out = ['+']  # type: List[unicode]
            for width in realwidths:
                out.append(char * (width + 2))
                out.append('+')
            self.add_text(''.join(out) + self.nl)

        def writerow(row):
            # type: (List[List[unicode]]) -> None
            lines = zip_longest(*row)
            for line in lines:
                out = ['|']
                for i, cell in enumerate(line):
                    if cell:
                        adjust_len = len(cell) - column_width(cell)
                        out.append(' ' + cell.ljust(
                            realwidths[i] + 1 + adjust_len))
                    else:
                        out.append(' ' * (realwidths[i] + 2))
                    out.append('|')
                self.add_text(''.join(out) + self.nl)

        for i, row in enumerate(fmted_rows):
            if separator and i == separator:
                writesep('=')
            else:
                writesep('-')
            writerow(row)
        writesep('-')
        self.table = None
        self.end_state(wrap=False)

    def visit_acks(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)
        self.add_text(', '.join(n.astext() for n in node.children[0].children) +
                      '.')
        self.end_state()
        raise nodes.SkipNode

    def visit_image(self, node):
        # type: (nodes.Node) -> None
        if 'alt' in node.attributes:
            self.add_text(_('[image: %s]') % node['alt'])
        self.add_text(_('[image]'))
        raise nodes.SkipNode

    def visit_transition(self, node):
        # type: (nodes.Node) -> None
        indent = sum(self.stateindent)
        self.new_state(0)
        self.add_text('=' * (MAXWIDTH - indent))
        self.end_state()
        raise nodes.SkipNode

    def visit_bullet_list(self, node):
        # type: (nodes.Node) -> None
        self.list_counter.append(-1)

    def depart_bullet_list(self, node):
        # type: (nodes.Node) -> None
        self.list_counter.pop()

    def visit_enumerated_list(self, node):
        # type: (nodes.Node) -> None
        self.list_counter.append(node.get('start', 1) - 1)

    def depart_enumerated_list(self, node):
        # type: (nodes.Node) -> None
        self.list_counter.pop()

    def visit_definition_list(self, node):
        # type: (nodes.Node) -> None
        self.list_counter.append(-2)

    def depart_definition_list(self, node):
        # type: (nodes.Node) -> None
        self.list_counter.pop()

    def visit_list_item(self, node):
        # type: (nodes.Node) -> None
        if self.list_counter[-1] == -1:
            # bullet list
            self.new_state(2)
        elif self.list_counter[-1] == -2:
            # definition list
            pass
        else:
            # enumerated list
            self.list_counter[-1] += 1
            self.new_state(len(str(self.list_counter[-1])) + 2)

    def depart_list_item(self, node):
        # type: (nodes.Node) -> None
        if self.list_counter[-1] == -1:
            self.end_state(first='* ')
        elif self.list_counter[-1] == -2:
            pass
        else:
            self.end_state(first='%s. ' % self.list_counter[-1])

    def visit_definition_list_item(self, node):
        # type: (nodes.Node) -> None
        self._classifier_count_in_li = len(node.traverse(nodes.classifier))

    def depart_definition_list_item(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_term(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)

    def depart_term(self, node):
        # type: (nodes.Node) -> None
        if not self._classifier_count_in_li:
            self.end_state(end=None)

    def visit_classifier(self, node):
        # type: (nodes.Node) -> None
        self.add_text(' : ')

    def depart_classifier(self, node):
        # type: (nodes.Node) -> None
        self._classifier_count_in_li -= 1
        if not self._classifier_count_in_li:
            self.end_state(end=None)

    def visit_definition(self, node):
        # type: (nodes.Node) -> None
        self.new_state()

    def depart_definition(self, node):
        # type: (nodes.Node) -> None
        self.end_state()

    def visit_field_list(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_field_list(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_field(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_field(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_field_name(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)

    def depart_field_name(self, node):
        # type: (nodes.Node) -> None
        self.add_text(':')
        self.end_state(end=None)

    def visit_field_body(self, node):
        # type: (nodes.Node) -> None
        self.new_state()

    def depart_field_body(self, node):
        # type: (nodes.Node) -> None
        self.end_state()

    def visit_centered(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_centered(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_hlist(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_hlist(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_hlistcol(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_hlistcol(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_admonition(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)

    def depart_admonition(self, node):
        # type: (nodes.Node) -> None
        self.end_state()

    def _visit_admonition(self, node):
        # type: (nodes.Node) -> None
        self.new_state(2)

        if isinstance(node.children[0], nodes.Sequential):
            self.add_text(self.nl)

    def _make_depart_admonition(name):
        # type: (unicode) -> Callable[[TextTranslator, nodes.Node], None]
        def depart_admonition(self, node):
            # type: (nodes.NodeVisitor, nodes.Node) -> None
            self.end_state(first=admonitionlabels[name] + ': ')
        return depart_admonition

    visit_attention = _visit_admonition
    depart_attention = _make_depart_admonition('attention')
    visit_caution = _visit_admonition
    depart_caution = _make_depart_admonition('caution')
    visit_danger = _visit_admonition
    depart_danger = _make_depart_admonition('danger')
    visit_error = _visit_admonition
    depart_error = _make_depart_admonition('error')
    visit_hint = _visit_admonition
    depart_hint = _make_depart_admonition('hint')
    visit_important = _visit_admonition
    depart_important = _make_depart_admonition('important')
    visit_note = _visit_admonition
    depart_note = _make_depart_admonition('note')
    visit_tip = _visit_admonition
    depart_tip = _make_depart_admonition('tip')
    visit_warning = _visit_admonition
    depart_warning = _make_depart_admonition('warning')
    visit_seealso = _visit_admonition
    depart_seealso = _make_depart_admonition('seealso')

    def visit_versionmodified(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)

    def depart_versionmodified(self, node):
        # type: (nodes.Node) -> None
        self.end_state()

    def visit_literal_block(self, node):
        # type: (nodes.Node) -> None
        self.new_state()

    def depart_literal_block(self, node):
        # type: (nodes.Node) -> None
        self.end_state(wrap=False)

    def visit_doctest_block(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)

    def depart_doctest_block(self, node):
        # type: (nodes.Node) -> None
        self.end_state(wrap=False)

    def visit_line_block(self, node):
        # type: (nodes.Node) -> None
        self.new_state()
        self.lineblocklevel += 1

    def depart_line_block(self, node):
        # type: (nodes.Node) -> None
        self.lineblocklevel -= 1
        self.end_state(wrap=False, end=None)
        if not self.lineblocklevel:
            self.add_text('\n')

    def visit_line(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_line(self, node):
        # type: (nodes.Node) -> None
        self.add_text('\n')

    def visit_block_quote(self, node):
        # type: (nodes.Node) -> None
        self.new_state()

    def depart_block_quote(self, node):
        # type: (nodes.Node) -> None
        self.end_state()

    def visit_compact_paragraph(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_compact_paragraph(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_paragraph(self, node):
        # type: (nodes.Node) -> None
        if not isinstance(node.parent, nodes.Admonition) or \
           isinstance(node.parent, addnodes.seealso):
            self.new_state(0)

    def depart_paragraph(self, node):
        # type: (nodes.Node) -> None
        if not isinstance(node.parent, nodes.Admonition) or \
           isinstance(node.parent, addnodes.seealso):
            self.end_state()

    def visit_target(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_index(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_toctree(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_pending_xref(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_pending_xref(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_reference(self, node):
        # type: (nodes.Node) -> None
        if self.add_secnumbers:
            numbers = node.get("secnumber")
            if numbers is not None:
                self.add_text('.'.join(map(str, numbers)) + self.secnumber_suffix)

    def depart_reference(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_number_reference(self, node):
        # type: (nodes.Node) -> None
        text = nodes.Text(node.get('title', '#'))
        self.visit_Text(text)
        raise nodes.SkipNode

    def visit_download_reference(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_download_reference(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_emphasis(self, node):
        # type: (nodes.Node) -> None
        self.add_text('*')

    def depart_emphasis(self, node):
        # type: (nodes.Node) -> None
        self.add_text('*')

    def visit_literal_emphasis(self, node):
        # type: (nodes.Node) -> None
        self.add_text('*')

    def depart_literal_emphasis(self, node):
        # type: (nodes.Node) -> None
        self.add_text('*')

    def visit_strong(self, node):
        # type: (nodes.Node) -> None
        self.add_text('**')

    def depart_strong(self, node):
        # type: (nodes.Node) -> None
        self.add_text('**')

    def visit_literal_strong(self, node):
        # type: (nodes.Node) -> None
        self.add_text('**')

    def depart_literal_strong(self, node):
        # type: (nodes.Node) -> None
        self.add_text('**')

    def visit_abbreviation(self, node):
        # type: (nodes.Node) -> None
        self.add_text('')

    def depart_abbreviation(self, node):
        # type: (nodes.Node) -> None
        if node.hasattr('explanation'):
            self.add_text(' (%s)' % node['explanation'])

    def visit_manpage(self, node):
        # type: (nodes.Node) -> Any
        return self.visit_literal_emphasis(node)

    def depart_manpage(self, node):
        # type: (nodes.Node) -> Any
        return self.depart_literal_emphasis(node)

    def visit_title_reference(self, node):
        # type: (nodes.Node) -> None
        self.add_text('*')

    def depart_title_reference(self, node):
        # type: (nodes.Node) -> None
        self.add_text('*')

    def visit_literal(self, node):
        # type: (nodes.Node) -> None
        self.add_text('"')

    def depart_literal(self, node):
        # type: (nodes.Node) -> None
        self.add_text('"')

    def visit_subscript(self, node):
        # type: (nodes.Node) -> None
        self.add_text('_')

    def depart_subscript(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_superscript(self, node):
        # type: (nodes.Node) -> None
        self.add_text('^')

    def depart_superscript(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_footnote_reference(self, node):
        # type: (nodes.Node) -> None
        self.add_text('[%s]' % node.astext())
        raise nodes.SkipNode

    def visit_citation_reference(self, node):
        # type: (nodes.Node) -> None
        self.add_text('[%s]' % node.astext())
        raise nodes.SkipNode

    def visit_Text(self, node):
        # type: (nodes.Node) -> None
        self.add_text(node.astext())

    def depart_Text(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_generated(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_generated(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_inline(self, node):
        # type: (nodes.Node) -> None
        if 'xref' in node['classes'] or 'term' in node['classes']:
            self.add_text('*')

    def depart_inline(self, node):
        # type: (nodes.Node) -> None
        if 'xref' in node['classes'] or 'term' in node['classes']:
            self.add_text('*')

    def visit_container(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_container(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_problematic(self, node):
        # type: (nodes.Node) -> None
        self.add_text('>>')

    def depart_problematic(self, node):
        # type: (nodes.Node) -> None
        self.add_text('<<')

    def visit_system_message(self, node):
        # type: (nodes.Node) -> None
        self.new_state(0)
        self.add_text('<SYSTEM MESSAGE: %s>' % node.astext())
        self.end_state()
        raise nodes.SkipNode

    def visit_comment(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_meta(self, node):
        # type: (nodes.Node) -> None
        # only valid for HTML
        raise nodes.SkipNode

    def visit_raw(self, node):
        # type: (nodes.Node) -> None
        if 'text' in node.get('format', '').split():
            self.new_state(0)
            self.add_text(node.astext())
            self.end_state(wrap = False)
        raise nodes.SkipNode

    def visit_math(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_math(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_math_block(self, node):
        # type: (nodes.Node) -> None
        self.new_state()

    def depart_math_block(self, node):
        # type: (nodes.Node) -> None
        self.end_state()

    def unknown_visit(self, node):
        # type: (nodes.Node) -> None
        raise NotImplementedError('Unknown node: ' + node.__class__.__name__)
