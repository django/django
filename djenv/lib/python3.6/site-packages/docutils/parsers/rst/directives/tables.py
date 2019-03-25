# $Id: tables.py 8039 2017-02-28 12:19:20Z milde $
# Authors: David Goodger <goodger@python.org>; David Priest
# Copyright: This module has been placed in the public domain.

"""
Directives for table elements.
"""

__docformat__ = 'reStructuredText'


import sys
import os.path
import csv

from docutils import io, nodes, statemachine, utils
from docutils.utils.error_reporting import SafeString
from docutils.utils import SystemMessagePropagation
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives


def align(argument):
    return directives.choice(argument, ('left', 'center', 'right'))


class Table(Directive):

    """
    Generic table base class.
    """

    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {'class': directives.class_option,
                   'name': directives.unchanged,
                   'align': align,
                   'widths': directives.value_or(('auto', 'grid'),
                                                 directives.positive_int_list)}
    has_content = True

    def make_title(self):
        if self.arguments:
            title_text = self.arguments[0]
            text_nodes, messages = self.state.inline_text(title_text,
                                                          self.lineno)
            title = nodes.title(title_text, '', *text_nodes)
            (title.source,
             title.line) = self.state_machine.get_source_and_line(self.lineno)
        else:
            title = None
            messages = []
        return title, messages

    def process_header_option(self):
        source = self.state_machine.get_source(self.lineno - 1)
        table_head = []
        max_header_cols = 0
        if 'header' in self.options:   # separate table header in option
            rows, max_header_cols = self.parse_csv_data_into_rows(
                self.options['header'].split('\n'), self.HeaderDialect(),
                source)
            table_head.extend(rows)
        return table_head, max_header_cols

    def check_table_dimensions(self, rows, header_rows, stub_columns):
        if len(rows) < header_rows:
            error = self.state_machine.reporter.error(
                '%s header row(s) specified but only %s row(s) of data '
                'supplied ("%s" directive).'
                % (header_rows, len(rows), self.name), nodes.literal_block(
                self.block_text, self.block_text), line=self.lineno)
            raise SystemMessagePropagation(error)
        if len(rows) == header_rows > 0:
            error = self.state_machine.reporter.error(
                'Insufficient data supplied (%s row(s)); no data remaining '
                'for table body, required by "%s" directive.'
                % (len(rows), self.name), nodes.literal_block(
                self.block_text, self.block_text), line=self.lineno)
            raise SystemMessagePropagation(error)
        for row in rows:
            if len(row) < stub_columns:
                error = self.state_machine.reporter.error(
                    '%s stub column(s) specified but only %s columns(s) of '
                    'data supplied ("%s" directive).' %
                    (stub_columns, len(row), self.name), nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
                raise SystemMessagePropagation(error)
            if len(row) == stub_columns > 0:
                error = self.state_machine.reporter.error(
                    'Insufficient data supplied (%s columns(s)); no data remaining '
                    'for table body, required by "%s" directive.'
                    % (len(row), self.name), nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
                raise SystemMessagePropagation(error)

    @property
    def widths(self):
        return self.options.get('widths', '')

    def get_column_widths(self, max_cols):
        if type(self.widths) == list:
            if len(self.widths) != max_cols:
                error = self.state_machine.reporter.error(
                    '"%s" widths do not match the number of columns in table '
                    '(%s).' % (self.name, max_cols), nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
                raise SystemMessagePropagation(error)
            col_widths = self.widths
        elif max_cols:
            col_widths = [100 // max_cols] * max_cols
        else:
            error = self.state_machine.reporter.error(
                'No table data detected in CSV file.', nodes.literal_block(
                self.block_text, self.block_text), line=self.lineno)
            raise SystemMessagePropagation(error)
        return col_widths

    def extend_short_rows_with_empty_cells(self, columns, parts):
        for part in parts:
            for row in part:
                if len(row) < columns:
                    row.extend([(0, 0, 0, [])] * (columns - len(row)))


class RSTTable(Table):

    def run(self):
        if not self.content:
            warning = self.state_machine.reporter.warning(
                'Content block expected for the "%s" directive; none found.'
                % self.name, nodes.literal_block(
                self.block_text, self.block_text), line=self.lineno)
            return [warning]
        title, messages = self.make_title()
        node = nodes.Element()          # anonymous container for parsing
        self.state.nested_parse(self.content, self.content_offset, node)
        if len(node) != 1 or not isinstance(node[0], nodes.table):
            error = self.state_machine.reporter.error(
                'Error parsing content block for the "%s" directive: exactly '
                'one table expected.' % self.name, nodes.literal_block(
                self.block_text, self.block_text), line=self.lineno)
            return [error]
        table_node = node[0]
        table_node['classes'] += self.options.get('class', [])
        if 'align' in self.options:
            table_node['align'] = self.options.get('align')
        tgroup = table_node[0]
        if type(self.widths) == list:
            colspecs = [child for child in tgroup.children
                        if child.tagname == 'colspec']
            for colspec, col_width in zip(colspecs, self.widths):
                colspec['colwidth'] = col_width
        # @@@ the colwidths argument for <tgroup> is not part of the
        # XML Exchange Table spec (https://www.oasis-open.org/specs/tm9901.htm)
        # and hence violates the docutils.dtd.
        if self.widths == 'auto':
            table_node['classes'] += ['colwidths-auto']
        elif self.widths: # "grid" or list of integers
            table_node['classes'] += ['colwidths-given']
        self.add_name(table_node)
        if title:
            table_node.insert(0, title)
        return [table_node] + messages


class CSVTable(Table):

    option_spec = {'header-rows': directives.nonnegative_int,
                   'stub-columns': directives.nonnegative_int,
                   'header': directives.unchanged,
                   'widths': directives.value_or(('auto', ),
                                                 directives.positive_int_list),
                   'file': directives.path,
                   'url': directives.uri,
                   'encoding': directives.encoding,
                   'class': directives.class_option,
                   'name': directives.unchanged,
                   'align': align,
                   # field delimiter char
                   'delim': directives.single_char_or_whitespace_or_unicode,
                   # treat whitespace after delimiter as significant
                   'keepspace': directives.flag,
                   # text field quote/unquote char:
                   'quote': directives.single_char_or_unicode,
                   # char used to escape delim & quote as-needed:
                   'escape': directives.single_char_or_unicode,}

    class DocutilsDialect(csv.Dialect):

        """CSV dialect for `csv_table` directive."""

        delimiter = ','
        quotechar = '"'
        doublequote = True
        skipinitialspace = True
        strict = True
        lineterminator = '\n'
        quoting = csv.QUOTE_MINIMAL

        def __init__(self, options):
            if 'delim' in options:
                self.delimiter = CSVTable.encode_for_csv(options['delim'])
            if 'keepspace' in options:
                self.skipinitialspace = False
            if 'quote' in options:
                self.quotechar = CSVTable.encode_for_csv(options['quote'])
            if 'escape' in options:
                self.doublequote = False
                self.escapechar = CSVTable.encode_for_csv(options['escape'])
            csv.Dialect.__init__(self)


    class HeaderDialect(csv.Dialect):

        """CSV dialect to use for the "header" option data."""

        delimiter = ','
        quotechar = '"'
        escapechar = '\\'
        doublequote = False
        skipinitialspace = True
        strict = True
        lineterminator = '\n'
        quoting = csv.QUOTE_MINIMAL

    def check_requirements(self):
        pass

    def run(self):
        try:
            if (not self.state.document.settings.file_insertion_enabled
                and ('file' in self.options
                     or 'url' in self.options)):
                warning = self.state_machine.reporter.warning(
                    'File and URL access deactivated; ignoring "%s" '
                    'directive.' % self.name, nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
                return [warning]
            self.check_requirements()
            title, messages = self.make_title()
            csv_data, source = self.get_csv_data()
            table_head, max_header_cols = self.process_header_option()
            rows, max_cols = self.parse_csv_data_into_rows(
                csv_data, self.DocutilsDialect(self.options), source)
            max_cols = max(max_cols, max_header_cols)
            header_rows = self.options.get('header-rows', 0)
            stub_columns = self.options.get('stub-columns', 0)
            self.check_table_dimensions(rows, header_rows, stub_columns)
            table_head.extend(rows[:header_rows])
            table_body = rows[header_rows:]
            col_widths = self.get_column_widths(max_cols)
            self.extend_short_rows_with_empty_cells(max_cols,
                                                    (table_head, table_body))
        except SystemMessagePropagation as detail:
            return [detail.args[0]]
        except csv.Error as detail:
            message = str(detail)
            if sys.version_info < (3,) and '1-character string' in message:
                message += '\nwith Python 2.x this must be an ASCII character.'
            error = self.state_machine.reporter.error(
                'Error with CSV data in "%s" directive:\n%s'
                % (self.name, message), nodes.literal_block(
                self.block_text, self.block_text), line=self.lineno)
            return [error]
        table = (col_widths, table_head, table_body)
        table_node = self.state.build_table(table, self.content_offset,
                                            stub_columns, widths=self.widths)
        table_node['classes'] += self.options.get('class', [])
        if 'align' in self.options:
            table_node['align'] = self.options.get('align')
        self.add_name(table_node)
        if title:
            table_node.insert(0, title)
        return [table_node] + messages

    def get_csv_data(self):
        """
        Get CSV data from the directive content, from an external
        file, or from a URL reference.
        """
        encoding = self.options.get(
            'encoding', self.state.document.settings.input_encoding)
        error_handler = self.state.document.settings.input_encoding_error_handler
        if self.content:
            # CSV data is from directive content.
            if 'file' in self.options or 'url' in self.options:
                error = self.state_machine.reporter.error(
                    '"%s" directive may not both specify an external file and'
                    ' have content.' % self.name, nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
                raise SystemMessagePropagation(error)
            source = self.content.source(0)
            csv_data = self.content
        elif 'file' in self.options:
            # CSV data is from an external file.
            if 'url' in self.options:
                error = self.state_machine.reporter.error(
                      'The "file" and "url" options may not be simultaneously'
                      ' specified for the "%s" directive.' % self.name,
                      nodes.literal_block(self.block_text, self.block_text),
                      line=self.lineno)
                raise SystemMessagePropagation(error)
            source_dir = os.path.dirname(
                os.path.abspath(self.state.document.current_source))
            source = os.path.normpath(os.path.join(source_dir,
                                                   self.options['file']))
            source = utils.relative_path(None, source)
            try:
                self.state.document.settings.record_dependencies.add(source)
                csv_file = io.FileInput(source_path=source,
                                        encoding=encoding,
                                        error_handler=error_handler)
                csv_data = csv_file.read().splitlines()
            except IOError as error:
                severe = self.state_machine.reporter.severe(
                    'Problems with "%s" directive path:\n%s.'
                    % (self.name, SafeString(error)),
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)
                raise SystemMessagePropagation(severe)
        elif 'url' in self.options:
            # CSV data is from a URL.
            # Do not import urllib2 at the top of the module because
            # it may fail due to broken SSL dependencies, and it takes
            # about 0.15 seconds to load.
            import urllib.request, urllib.error, urllib.parse
            source = self.options['url']
            try:
                csv_text = urllib.request.urlopen(source).read()
            except (urllib.error.URLError, IOError, OSError, ValueError) as error:
                severe = self.state_machine.reporter.severe(
                      'Problems with "%s" directive URL "%s":\n%s.'
                      % (self.name, self.options['url'], SafeString(error)),
                      nodes.literal_block(self.block_text, self.block_text),
                      line=self.lineno)
                raise SystemMessagePropagation(severe)
            csv_file = io.StringInput(
                source=csv_text, source_path=source, encoding=encoding,
                error_handler=(self.state.document.settings.\
                               input_encoding_error_handler))
            csv_data = csv_file.read().splitlines()
        else:
            error = self.state_machine.reporter.warning(
                'The "%s" directive requires content; none supplied.'
                % self.name, nodes.literal_block(
                self.block_text, self.block_text), line=self.lineno)
            raise SystemMessagePropagation(error)
        return csv_data, source

    if sys.version_info < (3,):
        # 2.x csv module doesn't do Unicode
        def decode_from_csv(s):
            return s.decode('utf-8')
        def encode_for_csv(s):
            return s.encode('utf-8')
    else:
        def decode_from_csv(s):
            return s
        def encode_for_csv(s):
            return s
    decode_from_csv = staticmethod(decode_from_csv)
    encode_for_csv = staticmethod(encode_for_csv)

    def parse_csv_data_into_rows(self, csv_data, dialect, source):
        # csv.py doesn't do Unicode; encode temporarily as UTF-8
        csv_reader = csv.reader([self.encode_for_csv(line + '\n')
                                 for line in csv_data],
                                dialect=dialect)
        rows = []
        max_cols = 0
        for row in csv_reader:
            row_data = []
            for cell in row:
                # decode UTF-8 back to Unicode
                cell_text = self.decode_from_csv(cell)
                cell_data = (0, 0, 0, statemachine.StringList(
                    cell_text.splitlines(), source=source))
                row_data.append(cell_data)
            rows.append(row_data)
            max_cols = max(max_cols, len(row))
        return rows, max_cols


class ListTable(Table):

    """
    Implement tables whose data is encoded as a uniform two-level bullet list.
    For further ideas, see
    http://docutils.sf.net/docs/dev/rst/alternatives.html#list-driven-tables
    """

    option_spec = {'header-rows': directives.nonnegative_int,
                   'stub-columns': directives.nonnegative_int,
                   'widths': directives.value_or(('auto', ),
                                                 directives.positive_int_list),
                   'class': directives.class_option,
                   'name': directives.unchanged,
                   'align': align}

    def run(self):
        if not self.content:
            error = self.state_machine.reporter.error(
                'The "%s" directive is empty; content required.' % self.name,
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)
            return [error]
        title, messages = self.make_title()
        node = nodes.Element()          # anonymous container for parsing
        self.state.nested_parse(self.content, self.content_offset, node)
        try:
            num_cols, col_widths = self.check_list_content(node)
            table_data = [[item.children for item in row_list[0]]
                          for row_list in node[0]]
            header_rows = self.options.get('header-rows', 0)
            stub_columns = self.options.get('stub-columns', 0)
            self.check_table_dimensions(table_data, header_rows, stub_columns)
        except SystemMessagePropagation as detail:
            return [detail.args[0]]
        table_node = self.build_table_from_list(table_data, col_widths,
                                                header_rows, stub_columns)
        if 'align' in self.options:
            table_node['align'] = self.options.get('align')
        table_node['classes'] += self.options.get('class', [])
        self.add_name(table_node)
        if title:
            table_node.insert(0, title)
        return [table_node] + messages

    def check_list_content(self, node):
        if len(node) != 1 or not isinstance(node[0], nodes.bullet_list):
            error = self.state_machine.reporter.error(
                'Error parsing content block for the "%s" directive: '
                'exactly one bullet list expected.' % self.name,
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)
            raise SystemMessagePropagation(error)
        list_node = node[0]
        # Check for a uniform two-level bullet list:
        for item_index in range(len(list_node)):
            item = list_node[item_index]
            if len(item) != 1 or not isinstance(item[0], nodes.bullet_list):
                error = self.state_machine.reporter.error(
                    'Error parsing content block for the "%s" directive: '
                    'two-level bullet list expected, but row %s does not '
                    'contain a second-level bullet list.'
                    % (self.name, item_index + 1), nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
                raise SystemMessagePropagation(error)
            elif item_index:
                # ATTN pychecker users: num_cols is guaranteed to be set in the
                # "else" clause below for item_index==0, before this branch is
                # triggered.
                if len(item[0]) != num_cols:
                    error = self.state_machine.reporter.error(
                        'Error parsing content block for the "%s" directive: '
                        'uniform two-level bullet list expected, but row %s '
                        'does not contain the same number of items as row 1 '
                        '(%s vs %s).'
                        % (self.name, item_index + 1, len(item[0]), num_cols),
                        nodes.literal_block(self.block_text, self.block_text),
                        line=self.lineno)
                    raise SystemMessagePropagation(error)
            else:
                num_cols = len(item[0])
        col_widths = self.get_column_widths(num_cols)
        return num_cols, col_widths

    def build_table_from_list(self, table_data, col_widths, header_rows, stub_columns):
        table = nodes.table()
        if self.widths == 'auto':
            table['classes'] += ['colwidths-auto']
        elif self.widths: # "grid" or list of integers
            table['classes'] += ['colwidths-given']
        tgroup = nodes.tgroup(cols=len(col_widths))
        table += tgroup
        for col_width in col_widths:
            colspec = nodes.colspec()
            if col_width is not None:
                colspec.attributes['colwidth'] = col_width
            if stub_columns:
                colspec.attributes['stub'] = 1
                stub_columns -= 1
            tgroup += colspec
        rows = []
        for row in table_data:
            row_node = nodes.row()
            for cell in row:
                entry = nodes.entry()
                entry += cell
                row_node += entry
            rows.append(row_node)
        if header_rows:
            thead = nodes.thead()
            thead.extend(rows[:header_rows])
            tgroup += thead
        tbody = nodes.tbody()
        tbody.extend(rows[header_rows:])
        tgroup += tbody
        return table
