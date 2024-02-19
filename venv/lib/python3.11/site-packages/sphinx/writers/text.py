"""Custom docutils writer for plain text."""
from __future__ import annotations

import math
import os
import re
import textwrap
from collections.abc import Generator, Iterable, Sequence
from itertools import chain, groupby
from typing import TYPE_CHECKING, Any, cast

from docutils import nodes, writers
from docutils.utils import column_width

from sphinx import addnodes
from sphinx.locale import _, admonitionlabels
from sphinx.util.docutils import SphinxTranslator

if TYPE_CHECKING:
    from docutils.nodes import Element, Text

    from sphinx.builders.text import TextBuilder


class Cell:
    """Represents a cell in a table.
    It can span multiple columns or multiple lines.
    """
    def __init__(self, text: str = "", rowspan: int = 1, colspan: int = 1) -> None:
        self.text = text
        self.wrapped: list[str] = []
        self.rowspan = rowspan
        self.colspan = colspan
        self.col: int | None = None
        self.row: int | None = None

    def __repr__(self) -> str:
        return f"<Cell {self.text!r} {self.row}v{self.rowspan}/{self.col}>{self.colspan}>"

    def __hash__(self) -> int:
        return hash((self.col, self.row))

    def __bool__(self) -> bool:
        return self.text != '' and self.col is not None and self.row is not None

    def wrap(self, width: int) -> None:
        self.wrapped = my_wrap(self.text, width)


class Table:
    """Represents a table, handling cells that can span multiple lines
    or rows, like::

       +-----------+-----+
       | AAA       | BBB |
       +-----+-----+     |
       |     | XXX |     |
       |     +-----+-----+
       | DDD | CCC       |
       +-----+-----------+

    This class can be used in two ways, either:

    - With absolute positions: call ``table[line, col] = Cell(...)``,
      this overwrites any existing cell(s) at these positions.

    - With relative positions: call the ``add_row()`` and
      ``add_cell(Cell(...))`` as needed.

    Cells spanning multiple rows or multiple columns (having a
    colspan or rowspan greater than one) are automatically referenced
    by all the table cells they cover. This is a useful
    representation as we can simply check
    ``if self[x, y] is self[x, y+1]`` to recognize a rowspan.

    Colwidth is not automatically computed, it has to be given, either
    at construction time, or during the table construction.

    Example usage::

       table = Table([6, 6])
       table.add_cell(Cell("foo"))
       table.add_cell(Cell("bar"))
       table.set_separator()
       table.add_row()
       table.add_cell(Cell("FOO"))
       table.add_cell(Cell("BAR"))
       print(table)
       +--------+--------+
       | foo    | bar    |
       |========|========|
       | FOO    | BAR    |
       +--------+--------+

    """
    def __init__(self, colwidth: list[int] | None = None) -> None:
        self.lines: list[list[Cell]] = []
        self.separator = 0
        self.colwidth: list[int] = (colwidth if colwidth is not None else [])
        self.current_line = 0
        self.current_col = 0

    def add_row(self) -> None:
        """Add a row to the table, to use with ``add_cell()``.  It is not needed
        to call ``add_row()`` before the first ``add_cell()``.
        """
        self.current_line += 1
        self.current_col = 0

    def set_separator(self) -> None:
        """Sets the separator below the current line."""
        self.separator = len(self.lines)

    def add_cell(self, cell: Cell) -> None:
        """Add a cell to the current line, to use with ``add_row()``.  To add
        a cell spanning multiple lines or rows, simply set the
        ``cell.colspan`` or ``cell.rowspan`` BEFORE inserting it into
        the table.
        """
        while self[self.current_line, self.current_col]:
            self.current_col += 1
        self[self.current_line, self.current_col] = cell
        self.current_col += cell.colspan

    def __getitem__(self, pos: tuple[int, int]) -> Cell:
        line, col = pos
        self._ensure_has_line(line + 1)
        self._ensure_has_column(col + 1)
        return self.lines[line][col]

    def __setitem__(self, pos: tuple[int, int], cell: Cell) -> None:
        line, col = pos
        self._ensure_has_line(line + cell.rowspan)
        self._ensure_has_column(col + cell.colspan)
        for dline in range(cell.rowspan):
            for dcol in range(cell.colspan):
                self.lines[line + dline][col + dcol] = cell
                cell.row = line
                cell.col = col

    def _ensure_has_line(self, line: int) -> None:
        while len(self.lines) < line:
            self.lines.append([])

    def _ensure_has_column(self, col: int) -> None:
        for line in self.lines:
            while len(line) < col:
                line.append(Cell())

    def __repr__(self) -> str:
        return "\n".join(repr(line) for line in self.lines)

    def cell_width(self, cell: Cell, source: list[int]) -> int:
        """Give the cell width, according to the given source (either
        ``self.colwidth`` or ``self.measured_widths``).
        This takes into account cells spanning multiple columns.
        """
        if cell.row is None or cell.col is None:
            msg = 'Cell co-ordinates have not been set'
            raise ValueError(msg)
        width = 0
        for i in range(self[cell.row, cell.col].colspan):
            width += source[cell.col + i]
        return width + (cell.colspan - 1) * 3

    @property
    def cells(self) -> Generator[Cell, None, None]:
        seen: set[Cell] = set()
        for line in self.lines:
            for cell in line:
                if cell and cell not in seen:
                    yield cell
                    seen.add(cell)

    def rewrap(self) -> None:
        """Call ``cell.wrap()`` on all cells, and measure each column width
        after wrapping (result written in ``self.measured_widths``).
        """
        self.measured_widths = self.colwidth[:]
        for cell in self.cells:
            cell.wrap(width=self.cell_width(cell, self.colwidth))
            if not cell.wrapped:
                continue
            if cell.row is None or cell.col is None:
                msg = 'Cell co-ordinates have not been set'
                raise ValueError(msg)
            width = math.ceil(max(column_width(x) for x in cell.wrapped) / cell.colspan)
            for col in range(cell.col, cell.col + cell.colspan):
                self.measured_widths[col] = max(self.measured_widths[col], width)

    def physical_lines_for_line(self, line: list[Cell]) -> int:
        """For a given line, compute the number of physical lines it spans
        due to text wrapping.
        """
        physical_lines = 1
        for cell in line:
            physical_lines = max(physical_lines, len(cell.wrapped))
        return physical_lines

    def __str__(self) -> str:
        out = []
        self.rewrap()

        def writesep(char: str = "-", lineno: int | None = None) -> str:
            """Called on the line *before* lineno.
            Called with no *lineno* for the last sep.
            """
            out: list[str] = []
            for colno, width in enumerate(self.measured_widths):
                if (
                    lineno is not None and
                    lineno > 0 and
                    self[lineno, colno] is self[lineno - 1, colno]
                ):
                    out.append(" " * (width + 2))
                else:
                    out.append(char * (width + 2))
            head = "+" if out[0][0] == "-" else "|"
            tail = "+" if out[-1][0] == "-" else "|"
            glue = [
                "+" if left[0] == "-" or right[0] == "-" else "|"
                for left, right in zip(out, out[1:])
            ]
            glue.append(tail)
            return head + "".join(chain.from_iterable(zip(out, glue)))

        for lineno, line in enumerate(self.lines):
            if self.separator and lineno == self.separator:
                out.append(writesep("=", lineno))
            else:
                out.append(writesep("-", lineno))
            for physical_line in range(self.physical_lines_for_line(line)):
                linestr = ["|"]
                for colno, cell in enumerate(line):
                    if cell.col != colno:
                        continue
                    if lineno != cell.row:  # NoQA: SIM114
                        physical_text = ""
                    elif physical_line >= len(cell.wrapped):
                        physical_text = ""
                    else:
                        physical_text = cell.wrapped[physical_line]
                    adjust_len = len(physical_text) - column_width(physical_text)
                    linestr.append(
                        " " +
                        physical_text.ljust(
                            self.cell_width(cell, self.measured_widths) + 1 + adjust_len,
                        ) + "|",
                    )
                out.append("".join(linestr))
        out.append(writesep("-"))
        return "\n".join(out)


class TextWrapper(textwrap.TextWrapper):
    """Custom subclass that uses a different word separator regex."""

    wordsep_re = re.compile(
        r'(\s+|'                                  # any whitespace
        r'(?<=\s)(?::[a-z-]+:)?`\S+|'             # interpreted text start
        r'[^\s\w]*\w+[a-zA-Z]-(?=\w+[a-zA-Z])|'   # hyphenated words
        r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w))')   # em-dash

    def _wrap_chunks(self, chunks: list[str]) -> list[str]:
        """_wrap_chunks(chunks : [string]) -> [string]

        The original _wrap_chunks uses len() to calculate width.
        This method respects wide/fullwidth characters for width adjustment.
        """
        lines: list[str] = []
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

            if self.drop_whitespace and chunks[-1].strip() == '' and lines:
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

            if self.drop_whitespace and cur_line and cur_line[-1].strip() == '':
                del cur_line[-1]

            if cur_line:
                lines.append(indent + ''.join(cur_line))

        return lines

    def _break_word(self, word: str, space_left: int) -> tuple[str, str]:
        """_break_word(word : string, space_left : int) -> (string, string)

        Break line by unicode width instead of len(word).
        """
        total = 0
        for i, c in enumerate(word):
            total += column_width(c)
            if total > space_left:
                return word[:i - 1], word[i - 1:]
        return word, ''

    def _split(self, text: str) -> list[str]:
        """_split(text : string) -> [string]

        Override original method that only split by 'wordsep_re'.
        This '_split' splits wide-characters into chunks by one character.
        """
        def split(t: str) -> list[str]:
            return super(TextWrapper, self)._split(t)
        chunks: list[str] = []
        for chunk in split(text):
            for w, g in groupby(chunk, column_width):
                if w == 1:
                    chunks.extend(split(''.join(g)))
                else:
                    chunks.extend(list(g))
        return chunks

    def _handle_long_word(self, reversed_chunks: list[str], cur_line: list[str],
                          cur_len: int, width: int) -> None:
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


def my_wrap(text: str, width: int = MAXWIDTH, **kwargs: Any) -> list[str]:
    w = TextWrapper(width=width, **kwargs)
    return w.wrap(text)


class TextWriter(writers.Writer):
    supported = ('text',)
    settings_spec = ('No options here.', '', ())
    settings_defaults: dict[str, Any] = {}

    output: str

    def __init__(self, builder: TextBuilder) -> None:
        super().__init__()
        self.builder = builder

    def translate(self) -> None:
        visitor = self.builder.create_translator(self.document, self.builder)
        self.document.walkabout(visitor)
        self.output = cast(TextTranslator, visitor).body


class TextTranslator(SphinxTranslator):
    builder: TextBuilder

    def __init__(self, document: nodes.document, builder: TextBuilder) -> None:
        super().__init__(document, builder)

        newlines = self.config.text_newlines
        if newlines == 'windows':
            self.nl = '\r\n'
        elif newlines == 'native':
            self.nl = os.linesep
        else:
            self.nl = '\n'
        self.sectionchars = self.config.text_sectionchars
        self.add_secnumbers = self.config.text_add_secnumbers
        self.secnumber_suffix = self.config.text_secnumber_suffix
        self.states: list[list[tuple[int, str | list[str]]]] = [[]]
        self.stateindent = [0]
        self.list_counter: list[int] = []
        self.sectionlevel = 0
        self.lineblocklevel = 0
        self.table: Table

        self.context: list[str] = []
        """Heterogeneous stack.

        Used by visit_* and depart_* functions in conjunction with the tree
        traversal. Make sure that the pops correspond to the pushes.
        """

    def add_text(self, text: str) -> None:
        self.states[-1].append((-1, text))

    def new_state(self, indent: int = STDINDENT) -> None:
        self.states.append([])
        self.stateindent.append(indent)

    def end_state(
        self, wrap: bool = True, end: Sequence[str] | None = ('',), first: str | None = None,
    ) -> None:
        content = self.states.pop()
        maxindent = sum(self.stateindent)
        indent = self.stateindent.pop()
        result: list[tuple[int, list[str]]] = []
        toformat: list[str] = []

        def do_format() -> None:
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
                toformat.append(item)  # type: ignore[arg-type]
            else:
                do_format()
                result.append((indent + itemindent, item))  # type: ignore[arg-type]
                toformat = []
        do_format()
        if first is not None and result:
            # insert prefix into first line (ex. *, [1], See also, etc.)
            newindent = result[0][0] - indent
            if result[0][1] == ['']:
                result.insert(0, (newindent, [first]))
            else:
                text = first + result[0][1].pop(0)
                result.insert(0, (newindent, [text]))

        self.states[-1].extend(result)

    def visit_document(self, node: Element) -> None:
        self.new_state(0)

    def depart_document(self, node: Element) -> None:
        self.end_state()
        self.body = self.nl.join(line and (' ' * indent + line)
                                 for indent, lines in self.states[0]
                                 for line in lines)
        # XXX header/footer?

    def visit_section(self, node: Element) -> None:
        self._title_char = self.sectionchars[self.sectionlevel]
        self.sectionlevel += 1

    def depart_section(self, node: Element) -> None:
        self.sectionlevel -= 1

    def visit_topic(self, node: Element) -> None:
        self.new_state(0)

    def depart_topic(self, node: Element) -> None:
        self.end_state()

    visit_sidebar = visit_topic
    depart_sidebar = depart_topic

    def visit_rubric(self, node: Element) -> None:
        self.new_state(0)
        self.add_text('-[ ')

    def depart_rubric(self, node: Element) -> None:
        self.add_text(' ]-')
        self.end_state()

    def visit_compound(self, node: Element) -> None:
        pass

    def depart_compound(self, node: Element) -> None:
        pass

    def visit_glossary(self, node: Element) -> None:
        pass

    def depart_glossary(self, node: Element) -> None:
        pass

    def visit_title(self, node: Element) -> None:
        if isinstance(node.parent, nodes.Admonition):
            self.add_text(node.astext() + ': ')
            raise nodes.SkipNode
        self.new_state(0)

    def get_section_number_string(self, node: Element) -> str:
        if isinstance(node.parent, nodes.section):
            anchorname = '#' + node.parent['ids'][0]
            numbers = self.builder.secnumbers.get(anchorname)
            if numbers is None:
                numbers = self.builder.secnumbers.get('')
            if numbers is not None:
                return '.'.join(map(str, numbers)) + self.secnumber_suffix
        return ''

    def depart_title(self, node: Element) -> None:
        if isinstance(node.parent, nodes.section):
            char = self._title_char
        else:
            char = '^'
        text = ''
        text = ''.join(x[1] for x in self.states.pop() if x[0] == -1)  # type: ignore[misc]
        if self.add_secnumbers:
            text = self.get_section_number_string(node) + text
        self.stateindent.pop()
        title = ['', text, '%s' % (char * column_width(text)), '']
        if len(self.states) == 2 and len(self.states[-1]) == 0:
            # remove an empty line before title if it is first section title in the document
            title.pop(0)
        self.states[-1].append((0, title))

    def visit_subtitle(self, node: Element) -> None:
        pass

    def depart_subtitle(self, node: Element) -> None:
        pass

    def visit_attribution(self, node: Element) -> None:
        self.add_text('-- ')

    def depart_attribution(self, node: Element) -> None:
        pass

    #############################################################
    # Domain-specific object descriptions
    #############################################################

    # Top-level nodes
    #################

    def visit_desc(self, node: Element) -> None:
        pass

    def depart_desc(self, node: Element) -> None:
        pass

    def visit_desc_signature(self, node: Element) -> None:
        self.new_state(0)

    def depart_desc_signature(self, node: Element) -> None:
        # XXX: wrap signatures in a way that makes sense
        self.end_state(wrap=False, end=None)

    def visit_desc_signature_line(self, node: Element) -> None:
        pass

    def depart_desc_signature_line(self, node: Element) -> None:
        self.add_text('\n')

    def visit_desc_content(self, node: Element) -> None:
        self.new_state()
        self.add_text(self.nl)

    def depart_desc_content(self, node: Element) -> None:
        self.end_state()

    def visit_desc_inline(self, node: Element) -> None:
        pass

    def depart_desc_inline(self, node: Element) -> None:
        pass

    # Nodes for high-level structure in signatures
    ##############################################

    def visit_desc_name(self, node: Element) -> None:
        pass

    def depart_desc_name(self, node: Element) -> None:
        pass

    def visit_desc_addname(self, node: Element) -> None:
        pass

    def depart_desc_addname(self, node: Element) -> None:
        pass

    def visit_desc_type(self, node: Element) -> None:
        pass

    def depart_desc_type(self, node: Element) -> None:
        pass

    def visit_desc_returns(self, node: Element) -> None:
        self.add_text(' -> ')

    def depart_desc_returns(self, node: Element) -> None:
        pass

    def _visit_sig_parameter_list(
        self,
        node: Element,
        parameter_group: type[Element],
        sig_open_paren: str,
        sig_close_paren: str,
    ) -> None:
        """Visit a signature parameters or type parameters list.

        The *parameter_group* value is the type of a child node acting as a required parameter
        or as a set of contiguous optional parameters.
        """
        self.add_text(sig_open_paren)
        self.is_first_param = True
        self.optional_param_level = 0
        self.params_left_at_level = 0
        self.param_group_index = 0
        # Counts as what we call a parameter group are either a required parameter, or a
        # set of contiguous optional ones.
        self.list_is_required_param = [isinstance(c, parameter_group) for c in node.children]
        self.required_params_left = sum(self.list_is_required_param)
        self.param_separator = ', '
        self.multi_line_parameter_list = node.get('multi_line_parameter_list', False)
        if self.multi_line_parameter_list:
            self.param_separator = self.param_separator.rstrip()
        self.context.append(sig_close_paren)

    def _depart_sig_parameter_list(self, node: Element) -> None:
        sig_close_paren = self.context.pop()
        self.add_text(sig_close_paren)

    def visit_desc_parameterlist(self, node: Element) -> None:
        self._visit_sig_parameter_list(node, addnodes.desc_parameter, '(', ')')

    def depart_desc_parameterlist(self, node: Element) -> None:
        self._depart_sig_parameter_list(node)

    def visit_desc_type_parameter_list(self, node: Element) -> None:
        self._visit_sig_parameter_list(node, addnodes.desc_type_parameter, '[', ']')

    def depart_desc_type_parameter_list(self, node: Element) -> None:
        self._depart_sig_parameter_list(node)

    def visit_desc_parameter(self, node: Element) -> None:
        on_separate_line = self.multi_line_parameter_list
        if on_separate_line and not (self.is_first_param and self.optional_param_level > 0):
            self.new_state()
        if self.is_first_param:
            self.is_first_param = False
        elif not on_separate_line and not self.required_params_left:
            self.add_text(self.param_separator)
        if self.optional_param_level == 0:
            self.required_params_left -= 1
        else:
            self.params_left_at_level -= 1

        self.add_text(node.astext())

        is_required = self.list_is_required_param[self.param_group_index]
        if on_separate_line:
            is_last_group = self.param_group_index + 1 == len(self.list_is_required_param)
            next_is_required = (
                not is_last_group
                and self.list_is_required_param[self.param_group_index + 1]
            )
            opt_param_left_at_level = self.params_left_at_level > 0
            if opt_param_left_at_level or is_required and (is_last_group or next_is_required):
                self.add_text(self.param_separator)
                self.end_state(wrap=False, end=None)

        elif self.required_params_left:
            self.add_text(self.param_separator)

        if is_required:
            self.param_group_index += 1
        raise nodes.SkipNode

    def visit_desc_type_parameter(self, node: Element) -> None:
        self.visit_desc_parameter(node)

    def visit_desc_optional(self, node: Element) -> None:
        self.params_left_at_level = sum([isinstance(c, addnodes.desc_parameter)
                                         for c in node.children])
        self.optional_param_level += 1
        self.max_optional_param_level = self.optional_param_level
        if self.multi_line_parameter_list:
            # If the first parameter is optional, start a new line and open the bracket.
            if self.is_first_param:
                self.new_state()
                self.add_text('[')
            # Else, if there remains at least one required parameter, append the
            # parameter separator, open a new bracket, and end the line.
            elif self.required_params_left:
                self.add_text(self.param_separator)
                self.add_text('[')
                self.end_state(wrap=False, end=None)
            # Else, open a new bracket, append the parameter separator, and end the
            # line.
            else:
                self.add_text('[')
                self.add_text(self.param_separator)
                self.end_state(wrap=False, end=None)
        else:
            self.add_text('[')

    def depart_desc_optional(self, node: Element) -> None:
        self.optional_param_level -= 1
        if self.multi_line_parameter_list:
            # If it's the first time we go down one level, add the separator before the
            # bracket.
            if self.optional_param_level == self.max_optional_param_level - 1:
                self.add_text(self.param_separator)
            self.add_text(']')
            # End the line if we have just closed the last bracket of this group of
            # optional parameters.
            if self.optional_param_level == 0:
                self.end_state(wrap=False, end=None)

        else:
            self.add_text(']')
        if self.optional_param_level == 0:
            self.param_group_index += 1

    def visit_desc_annotation(self, node: Element) -> None:
        pass

    def depart_desc_annotation(self, node: Element) -> None:
        pass

    ##############################################

    def visit_figure(self, node: Element) -> None:
        self.new_state()

    def depart_figure(self, node: Element) -> None:
        self.end_state()

    def visit_caption(self, node: Element) -> None:
        pass

    def depart_caption(self, node: Element) -> None:
        pass

    def visit_productionlist(self, node: Element) -> None:
        self.new_state()
        names = []
        productionlist = cast(Iterable[addnodes.production], node)
        for production in productionlist:
            names.append(production['tokenname'])
        maxlen = max(len(name) for name in names)
        lastname = None
        for production in productionlist:
            if production['tokenname']:
                self.add_text(production['tokenname'].ljust(maxlen) + ' ::=')
                lastname = production['tokenname']
            elif lastname is not None:
                self.add_text('%s    ' % (' ' * len(lastname)))
            self.add_text(production.astext() + self.nl)
        self.end_state(wrap=False)
        raise nodes.SkipNode

    def visit_footnote(self, node: Element) -> None:
        label = cast(nodes.label, node[0])
        self._footnote = label.astext().strip()
        self.new_state(len(self._footnote) + 3)

    def depart_footnote(self, node: Element) -> None:
        self.end_state(first='[%s] ' % self._footnote)

    def visit_citation(self, node: Element) -> None:
        if len(node) and isinstance(node[0], nodes.label):
            self._citlabel = node[0].astext()
        else:
            self._citlabel = ''
        self.new_state(len(self._citlabel) + 3)

    def depart_citation(self, node: Element) -> None:
        self.end_state(first='[%s] ' % self._citlabel)

    def visit_label(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_legend(self, node: Element) -> None:
        pass

    def depart_legend(self, node: Element) -> None:
        pass

    # XXX: option list could use some better styling

    def visit_option_list(self, node: Element) -> None:
        pass

    def depart_option_list(self, node: Element) -> None:
        pass

    def visit_option_list_item(self, node: Element) -> None:
        self.new_state(0)

    def depart_option_list_item(self, node: Element) -> None:
        self.end_state()

    def visit_option_group(self, node: Element) -> None:
        self._firstoption = True

    def depart_option_group(self, node: Element) -> None:
        self.add_text('     ')

    def visit_option(self, node: Element) -> None:
        if self._firstoption:
            self._firstoption = False
        else:
            self.add_text(', ')

    def depart_option(self, node: Element) -> None:
        pass

    def visit_option_string(self, node: Element) -> None:
        pass

    def depart_option_string(self, node: Element) -> None:
        pass

    def visit_option_argument(self, node: Element) -> None:
        self.add_text(node['delimiter'])

    def depart_option_argument(self, node: Element) -> None:
        pass

    def visit_description(self, node: Element) -> None:
        pass

    def depart_description(self, node: Element) -> None:
        pass

    def visit_tabular_col_spec(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_colspec(self, node: Element) -> None:
        self.table.colwidth.append(node["colwidth"])
        raise nodes.SkipNode

    def visit_tgroup(self, node: Element) -> None:
        pass

    def depart_tgroup(self, node: Element) -> None:
        pass

    def visit_thead(self, node: Element) -> None:
        pass

    def depart_thead(self, node: Element) -> None:
        pass

    def visit_tbody(self, node: Element) -> None:
        self.table.set_separator()

    def depart_tbody(self, node: Element) -> None:
        pass

    def visit_row(self, node: Element) -> None:
        if self.table.lines:
            self.table.add_row()

    def depart_row(self, node: Element) -> None:
        pass

    def visit_entry(self, node: Element) -> None:
        self.entry = Cell(
            rowspan=node.get("morerows", 0) + 1, colspan=node.get("morecols", 0) + 1,
        )
        self.new_state(0)

    def depart_entry(self, node: Element) -> None:
        text = self.nl.join(self.nl.join(x[1]) for x in self.states.pop())
        self.stateindent.pop()
        self.entry.text = text
        self.table.add_cell(self.entry)
        del self.entry

    def visit_table(self, node: Element) -> None:
        if hasattr(self, 'table'):
            msg = 'Nested tables are not supported.'
            raise NotImplementedError(msg)
        self.new_state(0)
        self.table = Table()

    def depart_table(self, node: Element) -> None:
        self.add_text(str(self.table))
        del self.table
        self.end_state(wrap=False)

    def visit_acks(self, node: Element) -> None:
        bullet_list = cast(nodes.bullet_list, node[0])
        list_items = cast(Iterable[nodes.list_item], bullet_list)
        self.new_state(0)
        self.add_text(', '.join(n.astext() for n in list_items) + '.')
        self.end_state()
        raise nodes.SkipNode

    def visit_image(self, node: Element) -> None:
        if 'alt' in node.attributes:
            self.add_text(_('[image: %s]') % node['alt'])
        self.add_text(_('[image]'))
        raise nodes.SkipNode

    def visit_transition(self, node: Element) -> None:
        indent = sum(self.stateindent)
        self.new_state(0)
        self.add_text('=' * (MAXWIDTH - indent))
        self.end_state()
        raise nodes.SkipNode

    def visit_bullet_list(self, node: Element) -> None:
        self.list_counter.append(-1)

    def depart_bullet_list(self, node: Element) -> None:
        self.list_counter.pop()

    def visit_enumerated_list(self, node: Element) -> None:
        self.list_counter.append(node.get('start', 1) - 1)

    def depart_enumerated_list(self, node: Element) -> None:
        self.list_counter.pop()

    def visit_definition_list(self, node: Element) -> None:
        self.list_counter.append(-2)

    def depart_definition_list(self, node: Element) -> None:
        self.list_counter.pop()

    def visit_list_item(self, node: Element) -> None:
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

    def depart_list_item(self, node: Element) -> None:
        if self.list_counter[-1] == -1:
            self.end_state(first='* ')
        elif self.list_counter[-1] == -2:
            pass
        else:
            self.end_state(first='%s. ' % self.list_counter[-1])

    def visit_definition_list_item(self, node: Element) -> None:
        self._classifier_count_in_li = len(list(node.findall(nodes.classifier)))

    def depart_definition_list_item(self, node: Element) -> None:
        pass

    def visit_term(self, node: Element) -> None:
        self.new_state(0)

    def depart_term(self, node: Element) -> None:
        if not self._classifier_count_in_li:
            self.end_state(end=None)

    def visit_classifier(self, node: Element) -> None:
        self.add_text(' : ')

    def depart_classifier(self, node: Element) -> None:
        self._classifier_count_in_li -= 1
        if not self._classifier_count_in_li:
            self.end_state(end=None)

    def visit_definition(self, node: Element) -> None:
        self.new_state()

    def depart_definition(self, node: Element) -> None:
        self.end_state()

    def visit_field_list(self, node: Element) -> None:
        pass

    def depart_field_list(self, node: Element) -> None:
        pass

    def visit_field(self, node: Element) -> None:
        pass

    def depart_field(self, node: Element) -> None:
        pass

    def visit_field_name(self, node: Element) -> None:
        self.new_state(0)

    def depart_field_name(self, node: Element) -> None:
        self.add_text(':')
        self.end_state(end=None)

    def visit_field_body(self, node: Element) -> None:
        self.new_state()

    def depart_field_body(self, node: Element) -> None:
        self.end_state()

    def visit_centered(self, node: Element) -> None:
        pass

    def depart_centered(self, node: Element) -> None:
        pass

    def visit_hlist(self, node: Element) -> None:
        pass

    def depart_hlist(self, node: Element) -> None:
        pass

    def visit_hlistcol(self, node: Element) -> None:
        pass

    def depart_hlistcol(self, node: Element) -> None:
        pass

    def visit_admonition(self, node: Element) -> None:
        self.new_state(0)

    def depart_admonition(self, node: Element) -> None:
        self.end_state()

    def _visit_admonition(self, node: Element) -> None:
        self.new_state(2)

    def _depart_admonition(self, node: Element) -> None:
        label = admonitionlabels[node.tagname]
        indent = sum(self.stateindent) + len(label)
        if (len(self.states[-1]) == 1 and
                self.states[-1][0][0] == 0 and
                MAXWIDTH - indent >= sum(len(s) for s in self.states[-1][0][1])):
            # short text: append text after admonition label
            self.stateindent[-1] += len(label)
            self.end_state(first=label + ': ')
        else:
            # long text: append label before the block
            self.states[-1].insert(0, (0, [self.nl]))
            self.end_state(first=label + ':')

    visit_attention = _visit_admonition
    depart_attention = _depart_admonition
    visit_caution = _visit_admonition
    depart_caution = _depart_admonition
    visit_danger = _visit_admonition
    depart_danger = _depart_admonition
    visit_error = _visit_admonition
    depart_error = _depart_admonition
    visit_hint = _visit_admonition
    depart_hint = _depart_admonition
    visit_important = _visit_admonition
    depart_important = _depart_admonition
    visit_note = _visit_admonition
    depart_note = _depart_admonition
    visit_tip = _visit_admonition
    depart_tip = _depart_admonition
    visit_warning = _visit_admonition
    depart_warning = _depart_admonition
    visit_seealso = _visit_admonition
    depart_seealso = _depart_admonition

    def visit_versionmodified(self, node: Element) -> None:
        self.new_state(0)

    def depart_versionmodified(self, node: Element) -> None:
        self.end_state()

    def visit_literal_block(self, node: Element) -> None:
        self.new_state()

    def depart_literal_block(self, node: Element) -> None:
        self.end_state(wrap=False)

    def visit_doctest_block(self, node: Element) -> None:
        self.new_state(0)

    def depart_doctest_block(self, node: Element) -> None:
        self.end_state(wrap=False)

    def visit_line_block(self, node: Element) -> None:
        self.new_state()
        self.lineblocklevel += 1

    def depart_line_block(self, node: Element) -> None:
        self.lineblocklevel -= 1
        self.end_state(wrap=False, end=None)
        if not self.lineblocklevel:
            self.add_text('\n')

    def visit_line(self, node: Element) -> None:
        pass

    def depart_line(self, node: Element) -> None:
        self.add_text('\n')

    def visit_block_quote(self, node: Element) -> None:
        self.new_state()

    def depart_block_quote(self, node: Element) -> None:
        self.end_state()

    def visit_compact_paragraph(self, node: Element) -> None:
        pass

    def depart_compact_paragraph(self, node: Element) -> None:
        pass

    def visit_paragraph(self, node: Element) -> None:
        if not isinstance(node.parent, nodes.Admonition) or \
           isinstance(node.parent, addnodes.seealso):
            self.new_state(0)

    def depart_paragraph(self, node: Element) -> None:
        if not isinstance(node.parent, nodes.Admonition) or \
           isinstance(node.parent, addnodes.seealso):
            self.end_state()

    def visit_target(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_index(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_toctree(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_substitution_definition(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_pending_xref(self, node: Element) -> None:
        pass

    def depart_pending_xref(self, node: Element) -> None:
        pass

    def visit_reference(self, node: Element) -> None:
        if self.add_secnumbers:
            numbers = node.get("secnumber")
            if numbers is not None:
                self.add_text('.'.join(map(str, numbers)) + self.secnumber_suffix)

    def depart_reference(self, node: Element) -> None:
        pass

    def visit_number_reference(self, node: Element) -> None:
        text = nodes.Text(node.get('title', '#'))
        self.visit_Text(text)
        raise nodes.SkipNode

    def visit_download_reference(self, node: Element) -> None:
        pass

    def depart_download_reference(self, node: Element) -> None:
        pass

    def visit_emphasis(self, node: Element) -> None:
        self.add_text('*')

    def depart_emphasis(self, node: Element) -> None:
        self.add_text('*')

    def visit_literal_emphasis(self, node: Element) -> None:
        self.add_text('*')

    def depart_literal_emphasis(self, node: Element) -> None:
        self.add_text('*')

    def visit_strong(self, node: Element) -> None:
        self.add_text('**')

    def depart_strong(self, node: Element) -> None:
        self.add_text('**')

    def visit_literal_strong(self, node: Element) -> None:
        self.add_text('**')

    def depart_literal_strong(self, node: Element) -> None:
        self.add_text('**')

    def visit_abbreviation(self, node: Element) -> None:
        self.add_text('')

    def depart_abbreviation(self, node: Element) -> None:
        if node.hasattr('explanation'):
            self.add_text(' (%s)' % node['explanation'])

    def visit_manpage(self, node: Element) -> None:
        return self.visit_literal_emphasis(node)

    def depart_manpage(self, node: Element) -> None:
        return self.depart_literal_emphasis(node)

    def visit_title_reference(self, node: Element) -> None:
        self.add_text('*')

    def depart_title_reference(self, node: Element) -> None:
        self.add_text('*')

    def visit_literal(self, node: Element) -> None:
        self.add_text('"')

    def depart_literal(self, node: Element) -> None:
        self.add_text('"')

    def visit_subscript(self, node: Element) -> None:
        self.add_text('_')

    def depart_subscript(self, node: Element) -> None:
        pass

    def visit_superscript(self, node: Element) -> None:
        self.add_text('^')

    def depart_superscript(self, node: Element) -> None:
        pass

    def visit_footnote_reference(self, node: Element) -> None:
        self.add_text('[%s]' % node.astext())
        raise nodes.SkipNode

    def visit_citation_reference(self, node: Element) -> None:
        self.add_text('[%s]' % node.astext())
        raise nodes.SkipNode

    def visit_Text(self, node: Text) -> None:
        self.add_text(node.astext())

    def depart_Text(self, node: Text) -> None:
        pass

    def visit_generated(self, node: Element) -> None:
        pass

    def depart_generated(self, node: Element) -> None:
        pass

    def visit_inline(self, node: Element) -> None:
        if 'xref' in node['classes'] or 'term' in node['classes']:
            self.add_text('*')

    def depart_inline(self, node: Element) -> None:
        if 'xref' in node['classes'] or 'term' in node['classes']:
            self.add_text('*')

    def visit_container(self, node: Element) -> None:
        pass

    def depart_container(self, node: Element) -> None:
        pass

    def visit_problematic(self, node: Element) -> None:
        self.add_text('>>')

    def depart_problematic(self, node: Element) -> None:
        self.add_text('<<')

    def visit_system_message(self, node: Element) -> None:
        self.new_state(0)
        self.add_text('<SYSTEM MESSAGE: %s>' % node.astext())
        self.end_state()
        raise nodes.SkipNode

    def visit_comment(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_meta(self, node: Element) -> None:
        # only valid for HTML
        raise nodes.SkipNode

    def visit_raw(self, node: Element) -> None:
        if 'text' in node.get('format', '').split():
            self.new_state(0)
            self.add_text(node.astext())
            self.end_state(wrap = False)
        raise nodes.SkipNode

    def visit_math(self, node: Element) -> None:
        pass

    def depart_math(self, node: Element) -> None:
        pass

    def visit_math_block(self, node: Element) -> None:
        self.new_state()

    def depart_math_block(self, node: Element) -> None:
        self.end_state()
