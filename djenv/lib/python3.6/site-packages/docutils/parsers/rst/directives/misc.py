# $Id: misc.py 7961 2016-07-28 22:02:47Z milde $
# Authors: David Goodger <goodger@python.org>; Dethe Elza
# Copyright: This module has been placed in the public domain.

"""Miscellaneous directives."""

__docformat__ = 'reStructuredText'

import sys
import os.path
import re
import time
from docutils import io, nodes, statemachine, utils
from docutils.utils.error_reporting import SafeString, ErrorString
from docutils.utils.error_reporting import locale_encoding
from docutils.parsers.rst import Directive, convert_directive_function
from docutils.parsers.rst import directives, roles, states
from docutils.parsers.rst.directives.body import CodeBlock, NumberLines
from docutils.parsers.rst.roles import set_classes
from docutils.transforms import misc

class Include(Directive):

    """
    Include content read from a separate source file.

    Content may be parsed by the parser, or included as a literal
    block.  The encoding of the included file can be specified.  Only
    a part of the given file argument may be included by specifying
    start and end line or text to match before and/or after the text
    to be used.
    """

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'literal': directives.flag,
                   'code': directives.unchanged,
                   'encoding': directives.encoding,
                   'tab-width': int,
                   'start-line': int,
                   'end-line': int,
                   'start-after': directives.unchanged_required,
                   'end-before': directives.unchanged_required,
                   # ignored except for 'literal' or 'code':
                   'number-lines': directives.unchanged, # integer or None
                   'class': directives.class_option,
                   'name': directives.unchanged}

    standard_include_path = os.path.join(os.path.dirname(states.__file__),
                                         'include')

    def run(self):
        """Include a file as part of the content of this reST file."""
        if not self.state.document.settings.file_insertion_enabled:
            raise self.warning('"%s" directive disabled.' % self.name)
        source = self.state_machine.input_lines.source(
            self.lineno - self.state_machine.input_offset - 1)
        source_dir = os.path.dirname(os.path.abspath(source))
        path = directives.path(self.arguments[0])
        if path.startswith('<') and path.endswith('>'):
            path = os.path.join(self.standard_include_path, path[1:-1])
        path = os.path.normpath(os.path.join(source_dir, path))
        path = utils.relative_path(None, path)
        path = nodes.reprunicode(path)
        encoding = self.options.get(
            'encoding', self.state.document.settings.input_encoding)
        e_handler=self.state.document.settings.input_encoding_error_handler
        tab_width = self.options.get(
            'tab-width', self.state.document.settings.tab_width)
        try:
            self.state.document.settings.record_dependencies.add(path)
            include_file = io.FileInput(source_path=path,
                                        encoding=encoding,
                                        error_handler=e_handler)
        except UnicodeEncodeError as error:
            raise self.severe('Problems with "%s" directive path:\n'
                              'Cannot encode input file path "%s" '
                              '(wrong locale?).' %
                              (self.name, SafeString(path)))
        except IOError as error:
            raise self.severe('Problems with "%s" directive path:\n%s.' %
                      (self.name, ErrorString(error)))
        startline = self.options.get('start-line', None)
        endline = self.options.get('end-line', None)
        try:
            if startline or (endline is not None):
                lines = include_file.readlines()
                rawtext = ''.join(lines[startline:endline])
            else:
                rawtext = include_file.read()
        except UnicodeError as error:
            raise self.severe('Problem with "%s" directive:\n%s' %
                              (self.name, ErrorString(error)))
        # start-after/end-before: no restrictions on newlines in match-text,
        # and no restrictions on matching inside lines vs. line boundaries
        after_text = self.options.get('start-after', None)
        if after_text:
            # skip content in rawtext before *and incl.* a matching text
            after_index = rawtext.find(after_text)
            if after_index < 0:
                raise self.severe('Problem with "start-after" option of "%s" '
                                  'directive:\nText not found.' % self.name)
            rawtext = rawtext[after_index + len(after_text):]
        before_text = self.options.get('end-before', None)
        if before_text:
            # skip content in rawtext after *and incl.* a matching text
            before_index = rawtext.find(before_text)
            if before_index < 0:
                raise self.severe('Problem with "end-before" option of "%s" '
                                  'directive:\nText not found.' % self.name)
            rawtext = rawtext[:before_index]

        include_lines = statemachine.string2lines(rawtext, tab_width,
                                                  convert_whitespace=True)
        if 'literal' in self.options:
            # Convert tabs to spaces, if `tab_width` is positive.
            if tab_width >= 0:
                text = rawtext.expandtabs(tab_width)
            else:
                text = rawtext
            literal_block = nodes.literal_block(rawtext, source=path,
                                    classes=self.options.get('class', []))
            literal_block.line = 1
            self.add_name(literal_block)
            if 'number-lines' in self.options:
                try:
                    startline = int(self.options['number-lines'] or 1)
                except ValueError:
                    raise self.error(':number-lines: with non-integer '
                                     'start value')
                endline = startline + len(include_lines)
                if text.endswith('\n'):
                    text = text[:-1]
                tokens = NumberLines([([], text)], startline, endline)
                for classes, value in tokens:
                    if classes:
                        literal_block += nodes.inline(value, value,
                                                      classes=classes)
                    else:
                        literal_block += nodes.Text(value, value)
            else:
                literal_block += nodes.Text(text, text)
            return [literal_block]
        if 'code' in self.options:
            self.options['source'] = path
            codeblock = CodeBlock(self.name,
                                  [self.options.pop('code')], # arguments
                                  self.options,
                                  include_lines, # content
                                  self.lineno,
                                  self.content_offset,
                                  self.block_text,
                                  self.state,
                                  self.state_machine)
            return codeblock.run()
        self.state_machine.insert_input(include_lines, path)
        return []


class Raw(Directive):

    """
    Pass through content unchanged

    Content is included in output based on type argument

    Content may be included inline (content section of directive) or
    imported from a file or url.
    """

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'file': directives.path,
                   'url': directives.uri,
                   'encoding': directives.encoding}
    has_content = True

    def run(self):
        if (not self.state.document.settings.raw_enabled
            or (not self.state.document.settings.file_insertion_enabled
                and ('file' in self.options
                     or 'url' in self.options))):
            raise self.warning('"%s" directive disabled.' % self.name)
        attributes = {'format': ' '.join(self.arguments[0].lower().split())}
        encoding = self.options.get(
            'encoding', self.state.document.settings.input_encoding)
        e_handler=self.state.document.settings.input_encoding_error_handler
        if self.content:
            if 'file' in self.options or 'url' in self.options:
                raise self.error(
                    '"%s" directive may not both specify an external file '
                    'and have content.' % self.name)
            text = '\n'.join(self.content)
        elif 'file' in self.options:
            if 'url' in self.options:
                raise self.error(
                    'The "file" and "url" options may not be simultaneously '
                    'specified for the "%s" directive.' % self.name)
            source_dir = os.path.dirname(
                os.path.abspath(self.state.document.current_source))
            path = os.path.normpath(os.path.join(source_dir,
                                                 self.options['file']))
            path = utils.relative_path(None, path)
            try:
                raw_file = io.FileInput(source_path=path,
                                        encoding=encoding,
                                        error_handler=e_handler)
                # TODO: currently, raw input files are recorded as
                # dependencies even if not used for the chosen output format.
                self.state.document.settings.record_dependencies.add(path)
            except IOError as error:
                raise self.severe('Problems with "%s" directive path:\n%s.'
                                  % (self.name, ErrorString(error)))
            try:
                text = raw_file.read()
            except UnicodeError as error:
                raise self.severe('Problem with "%s" directive:\n%s'
                    % (self.name, ErrorString(error)))
            attributes['source'] = path
        elif 'url' in self.options:
            source = self.options['url']
            # Do not import urllib2 at the top of the module because
            # it may fail due to broken SSL dependencies, and it takes
            # about 0.15 seconds to load.
            import urllib.request, urllib.error, urllib.parse
            try:
                raw_text = urllib.request.urlopen(source).read()
            except (urllib.error.URLError, IOError, OSError) as error:
                raise self.severe('Problems with "%s" directive URL "%s":\n%s.'
                    % (self.name, self.options['url'], ErrorString(error)))
            raw_file = io.StringInput(source=raw_text, source_path=source,
                                      encoding=encoding,
                                      error_handler=e_handler)
            try:
                text = raw_file.read()
            except UnicodeError as error:
                raise self.severe('Problem with "%s" directive:\n%s'
                                  % (self.name, ErrorString(error)))
            attributes['source'] = source
        else:
            # This will always fail because there is no content.
            self.assert_has_content()
        raw_node = nodes.raw('', text, **attributes)
        (raw_node.source,
        raw_node.line) = self.state_machine.get_source_and_line(self.lineno)
        return [raw_node]


class Replace(Directive):

    has_content = True

    def run(self):
        if not isinstance(self.state, states.SubstitutionDef):
            raise self.error(
                'Invalid context: the "%s" directive can only be used within '
                'a substitution definition.' % self.name)
        self.assert_has_content()
        text = '\n'.join(self.content)
        element = nodes.Element(text)
        self.state.nested_parse(self.content, self.content_offset,
                                element)
        # element might contain [paragraph] + system_message(s)
        node = None
        messages = []
        for elem in element:
            if not node and isinstance(elem, nodes.paragraph):
                node = elem
            elif isinstance(elem, nodes.system_message):
                elem['backrefs'] = []
                messages.append(elem)
            else:
                return [
                    self.state_machine.reporter.error(
                        'Error in "%s" directive: may contain a single paragraph '
                        'only.' % (self.name), line=self.lineno) ]
        if node:
            return messages + node.children
        return messages

class Unicode(Directive):

    r"""
    Convert Unicode character codes (numbers) to characters.  Codes may be
    decimal numbers, hexadecimal numbers (prefixed by ``0x``, ``x``, ``\x``,
    ``U+``, ``u``, or ``\u``; e.g. ``U+262E``), or XML-style numeric character
    entities (e.g. ``&#x262E;``).  Text following ".." is a comment and is
    ignored.  Spaces are ignored, and any other text remains as-is.
    """

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {'trim': directives.flag,
                   'ltrim': directives.flag,
                   'rtrim': directives.flag}

    comment_pattern = re.compile(r'( |\n|^)\.\. ')

    def run(self):
        if not isinstance(self.state, states.SubstitutionDef):
            raise self.error(
                'Invalid context: the "%s" directive can only be used within '
                'a substitution definition.' % self.name)
        substitution_definition = self.state_machine.node
        if 'trim' in self.options:
            substitution_definition.attributes['ltrim'] = 1
            substitution_definition.attributes['rtrim'] = 1
        if 'ltrim' in self.options:
            substitution_definition.attributes['ltrim'] = 1
        if 'rtrim' in self.options:
            substitution_definition.attributes['rtrim'] = 1
        codes = self.comment_pattern.split(self.arguments[0])[0].split()
        element = nodes.Element()
        for code in codes:
            try:
                decoded = directives.unicode_code(code)
            except ValueError as error:
                raise self.error('Invalid character code: %s\n%s'
                    % (code, ErrorString(error)))
            element += nodes.Text(decoded)
        return element.children


class Class(Directive):

    """
    Set a "class" attribute on the directive content or the next element.
    When applied to the next element, a "pending" element is inserted, and a
    transform does the work later.
    """

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = True

    def run(self):
        try:
            class_value = directives.class_option(self.arguments[0])
        except ValueError:
            raise self.error(
                'Invalid class attribute value for "%s" directive: "%s".'
                % (self.name, self.arguments[0]))
        node_list = []
        if self.content:
            container = nodes.Element()
            self.state.nested_parse(self.content, self.content_offset,
                                    container)
            for node in container:
                node['classes'].extend(class_value)
            node_list.extend(container.children)
        else:
            pending = nodes.pending(
                misc.ClassAttribute,
                {'class': class_value, 'directive': self.name},
                self.block_text)
            self.state_machine.document.note_pending(pending)
            node_list.append(pending)
        return node_list


class Role(Directive):

    has_content = True

    argument_pattern = re.compile(r'(%s)\s*(\(\s*(%s)\s*\)\s*)?$'
                                  % ((states.Inliner.simplename,) * 2))

    def run(self):
        """Dynamically create and register a custom interpreted text role."""
        if self.content_offset > self.lineno or not self.content:
            raise self.error('"%s" directive requires arguments on the first '
                             'line.' % self.name)
        args = self.content[0]
        match = self.argument_pattern.match(args)
        if not match:
            raise self.error('"%s" directive arguments not valid role names: '
                             '"%s".' % (self.name, args))
        new_role_name = match.group(1)
        base_role_name = match.group(3)
        messages = []
        if base_role_name:
            base_role, messages = roles.role(
                base_role_name, self.state_machine.language, self.lineno,
                self.state.reporter)
            if base_role is None:
                error = self.state.reporter.error(
                    'Unknown interpreted text role "%s".' % base_role_name,
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)
                return messages + [error]
        else:
            base_role = roles.generic_custom_role
        assert not hasattr(base_role, 'arguments'), (
            'Supplemental directive arguments for "%s" directive not '
            'supported (specified by "%r" role).' % (self.name, base_role))
        try:
            converted_role = convert_directive_function(base_role)
            (arguments, options, content, content_offset) = (
                self.state.parse_directive_block(
                self.content[1:], self.content_offset, converted_role,
                option_presets={}))
        except states.MarkupError as detail:
            error = self.state_machine.reporter.error(
                'Error in "%s" directive:\n%s.' % (self.name, detail),
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)
            return messages + [error]
        if 'class' not in options:
            try:
                options['class'] = directives.class_option(new_role_name)
            except ValueError as detail:
                error = self.state_machine.reporter.error(
                    'Invalid argument for "%s" directive:\n%s.'
                    % (self.name, SafeString(detail)), nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
                return messages + [error]
        role = roles.CustomRole(new_role_name, base_role, options, content)
        roles.register_local_role(new_role_name, role)
        return messages


class DefaultRole(Directive):

    """Set the default interpreted text role."""

    optional_arguments = 1
    final_argument_whitespace = False

    def run(self):
        if not self.arguments:
            if '' in roles._roles:
                # restore the "default" default role
                del roles._roles['']
            return []
        role_name = self.arguments[0]
        role, messages = roles.role(role_name, self.state_machine.language,
                                    self.lineno, self.state.reporter)
        if role is None:
            error = self.state.reporter.error(
                'Unknown interpreted text role "%s".' % role_name,
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)
            return messages + [error]
        roles._roles[''] = role
        # @@@ should this be local to the document, not the parser?
        return messages


class Title(Directive):

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    def run(self):
        self.state_machine.document['title'] = self.arguments[0]
        return []


class Date(Directive):

    has_content = True

    def run(self):
        if not isinstance(self.state, states.SubstitutionDef):
            raise self.error(
                'Invalid context: the "%s" directive can only be used within '
                'a substitution definition.' % self.name)
        format_str = '\n'.join(self.content) or '%Y-%m-%d'
        if sys.version_info< (3, 0):
            try:
                format_str = format_str.encode(locale_encoding or 'utf-8')
            except UnicodeEncodeError:
                raise self.warning('Cannot encode date format string '
                    'with locale encoding "%s".' % locale_encoding)
        # @@@
        # Use timestamp from the `SOURCE_DATE_EPOCH`_ environment variable?
        # Pro: Docutils-generated documentation
        #      can easily be part of `reproducible software builds`__
        #
        #      __ https://reproducible-builds.org/
        #
        # Con: Changes the specs, hard to predict behaviour,
        #      no actual use case!
        #
        # See also the discussion about \date \time \year in TeX
        # http://tug.org/pipermail/tex-k/2016-May/002704.html
        # source_date_epoch = os.environ.get('SOURCE_DATE_EPOCH')
        # if (source_date_epoch
        #     and self.state.document.settings.use_source_date_epoch):
        #     text = time.strftime(format_str,
        #                          time.gmtime(int(source_date_epoch)))
        # else:
        text = time.strftime(format_str)
        if sys.version_info< (3, 0):
            # `text` is a byte string that may contain non-ASCII characters:
            try:
                text = text.decode(locale_encoding or 'utf-8')
            except UnicodeDecodeError:
                text = text.decode(locale_encoding or 'utf-8', 'replace')
                raise self.warning('Error decoding "%s"'
                    'with locale encoding "%s".' % (text, locale_encoding))
        return [nodes.Text(text)]


class TestDirective(Directive):

    """This directive is useful only for testing purposes."""

    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {'option': directives.unchanged_required}
    has_content = True

    def run(self):
        if self.content:
            text = '\n'.join(self.content)
            info = self.state_machine.reporter.info(
                'Directive processed. Type="%s", arguments=%r, options=%r, '
                'content:' % (self.name, self.arguments, self.options),
                nodes.literal_block(text, text), line=self.lineno)
        else:
            info = self.state_machine.reporter.info(
                'Directive processed. Type="%s", arguments=%r, options=%r, '
                'content: None' % (self.name, self.arguments, self.options),
                line=self.lineno)
        return [info]

# Old-style, functional definition:
#
# def directive_test_function(name, arguments, options, content, lineno,
#                             content_offset, block_text, state, state_machine):
#     """This directive is useful only for testing purposes."""
#     if content:
#         text = '\n'.join(content)
#         info = state_machine.reporter.info(
#             'Directive processed. Type="%s", arguments=%r, options=%r, '
#             'content:' % (name, arguments, options),
#             nodes.literal_block(text, text), line=lineno)
#     else:
#         info = state_machine.reporter.info(
#             'Directive processed. Type="%s", arguments=%r, options=%r, '
#             'content: None' % (name, arguments, options), line=lineno)
#     return [info]
#
# directive_test_function.arguments = (0, 1, 1)
# directive_test_function.options = {'option': directives.unchanged_required}
# directive_test_function.content = 1
