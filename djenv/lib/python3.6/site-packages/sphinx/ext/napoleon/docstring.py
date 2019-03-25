# -*- coding: utf-8 -*-
"""
    sphinx.ext.napoleon.docstring
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Classes for docstring parsing and formatting.


    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import collections
import inspect
import re
from functools import partial

from six import string_types, u
from six.moves import range

from sphinx.ext.napoleon.iterators import modify_iter
from sphinx.locale import _
from sphinx.util.pycompat import UnicodeMixin

if False:
    # For type annotation
    from typing import Any, Callable, Dict, List, Tuple, Union  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.config import Config as SphinxConfig  # NOQA


_directive_regex = re.compile(r'\.\. \S+::')
_google_section_regex = re.compile(r'^(\s|\w)+:\s*$')
_google_typed_arg_regex = re.compile(r'\s*(.+?)\s*\(\s*(.*[^\s]+)\s*\)')
_numpy_section_regex = re.compile(r'^[=\-`:\'"~^_*+#<>]{2,}\s*$')
_single_colon_regex = re.compile(r'(?<!:):(?!:)')
_xref_regex = re.compile(r'(:(?:[a-zA-Z0-9]+[\-_+:.])*[a-zA-Z0-9]+:`.+?`)')
_bullet_list_regex = re.compile(r'^(\*|\+|\-)(\s+\S|\s*$)')
_enumerated_list_regex = re.compile(
    r'^(?P<paren>\()?'
    r'(\d+|#|[ivxlcdm]+|[IVXLCDM]+|[a-zA-Z])'
    r'(?(paren)\)|\.)(\s+\S|\s*$)')


class GoogleDocstring(UnicodeMixin):
    """Convert Google style docstrings to reStructuredText.

    Parameters
    ----------
    docstring : :obj:`str` or :obj:`list` of :obj:`str`
        The docstring to parse, given either as a string or split into
        individual lines.
    config: :obj:`sphinx.ext.napoleon.Config` or :obj:`sphinx.config.Config`
        The configuration settings to use. If not given, defaults to the
        config object on `app`; or if `app` is not given defaults to the
        a new :class:`sphinx.ext.napoleon.Config` object.


    Other Parameters
    ----------------
    app : :class:`sphinx.application.Sphinx`, optional
        Application object representing the Sphinx process.
    what : :obj:`str`, optional
        A string specifying the type of the object to which the docstring
        belongs. Valid values: "module", "class", "exception", "function",
        "method", "attribute".
    name : :obj:`str`, optional
        The fully qualified name of the object.
    obj : module, class, exception, function, method, or attribute
        The object to which the docstring belongs.
    options : :class:`sphinx.ext.autodoc.Options`, optional
        The options given to the directive: an object with attributes
        inherited_members, undoc_members, show_inheritance and noindex that
        are True if the flag option of same name was given to the auto
        directive.


    Example
    -------
    >>> from sphinx.ext.napoleon import Config
    >>> config = Config(napoleon_use_param=True, napoleon_use_rtype=True)
    >>> docstring = '''One line summary.
    ...
    ... Extended description.
    ...
    ... Args:
    ...   arg1(int): Description of `arg1`
    ...   arg2(str): Description of `arg2`
    ... Returns:
    ...   str: Description of return value.
    ... '''
    >>> print(GoogleDocstring(docstring, config))
    One line summary.
    <BLANKLINE>
    Extended description.
    <BLANKLINE>
    :param arg1: Description of `arg1`
    :type arg1: int
    :param arg2: Description of `arg2`
    :type arg2: str
    <BLANKLINE>
    :returns: Description of return value.
    :rtype: str
    <BLANKLINE>

    """
    def __init__(self, docstring, config=None, app=None, what='', name='',
                 obj=None, options=None):
        # type: (Union[unicode, List[unicode]], SphinxConfig, Sphinx, unicode, unicode, Any, Any) -> None  # NOQA
        self._config = config
        self._app = app

        if not self._config:
            from sphinx.ext.napoleon import Config
            self._config = self._app and self._app.config or Config()  # type: ignore

        if not what:
            if inspect.isclass(obj):
                what = 'class'
            elif inspect.ismodule(obj):
                what = 'module'
            elif isinstance(obj, collections.Callable):  # type: ignore
                what = 'function'
            else:
                what = 'object'

        self._what = what
        self._name = name
        self._obj = obj
        self._opt = options
        if isinstance(docstring, string_types):
            docstring = docstring.splitlines()
        self._lines = docstring
        self._line_iter = modify_iter(docstring, modifier=lambda s: s.rstrip())
        self._parsed_lines = []  # type: List[unicode]
        self._is_in_section = False
        self._section_indent = 0
        if not hasattr(self, '_directive_sections'):
            self._directive_sections = []  # type: List[unicode]
        if not hasattr(self, '_sections'):
            self._sections = {
                'args': self._parse_parameters_section,
                'arguments': self._parse_parameters_section,
                'attention': partial(self._parse_admonition, 'attention'),
                'attributes': self._parse_attributes_section,
                'caution': partial(self._parse_admonition, 'caution'),
                'danger': partial(self._parse_admonition, 'danger'),
                'error': partial(self._parse_admonition, 'error'),
                'example': self._parse_examples_section,
                'examples': self._parse_examples_section,
                'hint': partial(self._parse_admonition, 'hint'),
                'important': partial(self._parse_admonition, 'important'),
                'keyword args': self._parse_keyword_arguments_section,
                'keyword arguments': self._parse_keyword_arguments_section,
                'methods': self._parse_methods_section,
                'note': partial(self._parse_admonition, 'note'),
                'notes': self._parse_notes_section,
                'other parameters': self._parse_other_parameters_section,
                'parameters': self._parse_parameters_section,
                'return': self._parse_returns_section,
                'returns': self._parse_returns_section,
                'raises': self._parse_raises_section,
                'references': self._parse_references_section,
                'see also': self._parse_see_also_section,
                'tip': partial(self._parse_admonition, 'tip'),
                'todo': partial(self._parse_admonition, 'todo'),
                'warning': partial(self._parse_admonition, 'warning'),
                'warnings': partial(self._parse_admonition, 'warning'),
                'warns': self._parse_warns_section,
                'yield': self._parse_yields_section,
                'yields': self._parse_yields_section,
            }  # type: Dict[unicode, Callable]

        self._load_custom_sections()

        self._parse()

    def __unicode__(self):
        # type: () -> unicode
        """Return the parsed docstring in reStructuredText format.

        Returns
        -------
        unicode
            Unicode version of the docstring.

        """
        return u('\n').join(self.lines())

    def lines(self):
        # type: () -> List[unicode]
        """Return the parsed lines of the docstring in reStructuredText format.

        Returns
        -------
        list(str)
            The lines of the docstring in a list.

        """
        return self._parsed_lines

    def _consume_indented_block(self, indent=1):
        # type: (int) -> List[unicode]
        lines = []
        line = self._line_iter.peek()
        while(not self._is_section_break() and
              (not line or self._is_indented(line, indent))):
            lines.append(next(self._line_iter))
            line = self._line_iter.peek()
        return lines

    def _consume_contiguous(self):
        # type: () -> List[unicode]
        lines = []
        while (self._line_iter.has_next() and
               self._line_iter.peek() and
               not self._is_section_header()):
            lines.append(next(self._line_iter))
        return lines

    def _consume_empty(self):
        # type: () -> List[unicode]
        lines = []
        line = self._line_iter.peek()
        while self._line_iter.has_next() and not line:
            lines.append(next(self._line_iter))
            line = self._line_iter.peek()
        return lines

    def _consume_field(self, parse_type=True, prefer_type=False):
        # type: (bool, bool) -> Tuple[unicode, unicode, List[unicode]]
        line = next(self._line_iter)

        before, colon, after = self._partition_field_on_colon(line)
        _name, _type, _desc = before, '', after  # type: unicode, unicode, unicode

        if parse_type:
            match = _google_typed_arg_regex.match(before)
            if match:
                _name = match.group(1)
                _type = match.group(2)

        _name = self._escape_args_and_kwargs(_name)

        if prefer_type and not _type:
            _type, _name = _name, _type
        indent = self._get_indent(line) + 1
        _descs = [_desc] + self._dedent(self._consume_indented_block(indent))
        _descs = self.__class__(_descs, self._config).lines()
        return _name, _type, _descs

    def _consume_fields(self, parse_type=True, prefer_type=False):
        # type: (bool, bool) -> List[Tuple[unicode, unicode, List[unicode]]]
        self._consume_empty()
        fields = []
        while not self._is_section_break():
            _name, _type, _desc = self._consume_field(parse_type, prefer_type)
            if _name or _type or _desc:
                fields.append((_name, _type, _desc,))
        return fields

    def _consume_inline_attribute(self):
        # type: () -> Tuple[unicode, List[unicode]]
        line = next(self._line_iter)
        _type, colon, _desc = self._partition_field_on_colon(line)
        if not colon:
            _type, _desc = _desc, _type
        _descs = [_desc] + self._dedent(self._consume_to_end())
        _descs = self.__class__(_descs, self._config).lines()
        return _type, _descs

    def _consume_returns_section(self):
        # type: () -> List[Tuple[unicode, unicode, List[unicode]]]
        lines = self._dedent(self._consume_to_next_section())
        if lines:
            before, colon, after = self._partition_field_on_colon(lines[0])
            _name, _type, _desc = '', '', lines  # type: unicode, unicode, List[unicode]

            if colon:
                if after:
                    _desc = [after] + lines[1:]
                else:
                    _desc = lines[1:]

                _type = before

            _desc = self.__class__(_desc, self._config).lines()
            return [(_name, _type, _desc,)]
        else:
            return []

    def _consume_usage_section(self):
        # type: () -> List[unicode]
        lines = self._dedent(self._consume_to_next_section())
        return lines

    def _consume_section_header(self):
        # type: () -> unicode
        section = next(self._line_iter)
        stripped_section = section.strip(':')
        if stripped_section.lower() in self._sections:
            section = stripped_section
        return section

    def _consume_to_end(self):
        # type: () -> List[unicode]
        lines = []
        while self._line_iter.has_next():
            lines.append(next(self._line_iter))
        return lines

    def _consume_to_next_section(self):
        # type: () -> List[unicode]
        self._consume_empty()
        lines = []
        while not self._is_section_break():
            lines.append(next(self._line_iter))
        return lines + self._consume_empty()

    def _dedent(self, lines, full=False):
        # type: (List[unicode], bool) -> List[unicode]
        if full:
            return [line.lstrip() for line in lines]
        else:
            min_indent = self._get_min_indent(lines)
            return [line[min_indent:] for line in lines]

    def _escape_args_and_kwargs(self, name):
        # type: (unicode) -> unicode
        if name[:2] == '**':
            return r'\*\*' + name[2:]
        elif name[:1] == '*':
            return r'\*' + name[1:]
        else:
            return name

    def _fix_field_desc(self, desc):
        # type: (List[unicode]) -> List[unicode]
        if self._is_list(desc):
            desc = [u''] + desc
        elif desc[0].endswith('::'):
            desc_block = desc[1:]
            indent = self._get_indent(desc[0])
            block_indent = self._get_initial_indent(desc_block)
            if block_indent > indent:
                desc = [u''] + desc
            else:
                desc = ['', desc[0]] + self._indent(desc_block, 4)
        return desc

    def _format_admonition(self, admonition, lines):
        # type: (unicode, List[unicode]) -> List[unicode]
        lines = self._strip_empty(lines)
        if len(lines) == 1:
            return ['.. %s:: %s' % (admonition, lines[0].strip()), '']
        elif lines:
            lines = self._indent(self._dedent(lines), 3)
            return [u'.. %s::' % admonition, u''] + lines + [u'']
        else:
            return [u'.. %s::' % admonition, u'']

    def _format_block(self, prefix, lines, padding=None):
        # type: (unicode, List[unicode], unicode) -> List[unicode]
        if lines:
            if padding is None:
                padding = ' ' * len(prefix)
            result_lines = []
            for i, line in enumerate(lines):
                if i == 0:
                    result_lines.append((prefix + line).rstrip())
                elif line:
                    result_lines.append(padding + line)
                else:
                    result_lines.append('')
            return result_lines
        else:
            return [prefix]

    def _format_docutils_params(self, fields, field_role='param',
                                type_role='type'):
        # type: (List[Tuple[unicode, unicode, List[unicode]]], unicode, unicode) -> List[unicode]  # NOQA
        lines = []
        for _name, _type, _desc in fields:
            _desc = self._strip_empty(_desc)
            if any(_desc):
                _desc = self._fix_field_desc(_desc)
                field = ':%s %s: ' % (field_role, _name)
                lines.extend(self._format_block(field, _desc))
            else:
                lines.append(':%s %s:' % (field_role, _name))

            if _type:
                lines.append(':%s %s: %s' % (type_role, _name, _type))
        return lines + ['']

    def _format_field(self, _name, _type, _desc):
        # type: (unicode, unicode, List[unicode]) -> List[unicode]
        _desc = self._strip_empty(_desc)
        has_desc = any(_desc)
        separator = has_desc and ' -- ' or ''
        if _name:
            if _type:
                if '`' in _type:
                    field = '**%s** (%s)%s' % (_name, _type, separator)  # type: unicode
                else:
                    field = '**%s** (*%s*)%s' % (_name, _type, separator)
            else:
                field = '**%s**%s' % (_name, separator)
        elif _type:
            if '`' in _type:
                field = '%s%s' % (_type, separator)
            else:
                field = '*%s*%s' % (_type, separator)
        else:
            field = ''

        if has_desc:
            _desc = self._fix_field_desc(_desc)
            if _desc[0]:
                return [field + _desc[0]] + _desc[1:]
            else:
                return [field] + _desc
        else:
            return [field]

    def _format_fields(self, field_type, fields):
        # type: (unicode, List[Tuple[unicode, unicode, List[unicode]]]) -> List[unicode]
        field_type = ':%s:' % field_type.strip()
        padding = ' ' * len(field_type)
        multi = len(fields) > 1
        lines = []  # type: List[unicode]
        for _name, _type, _desc in fields:
            field = self._format_field(_name, _type, _desc)
            if multi:
                if lines:
                    lines.extend(self._format_block(padding + ' * ', field))
                else:
                    lines.extend(self._format_block(field_type + ' * ', field))
            else:
                lines.extend(self._format_block(field_type + ' ', field))
        if lines and lines[-1]:
            lines.append('')
        return lines

    def _get_current_indent(self, peek_ahead=0):
        # type: (int) -> int
        line = self._line_iter.peek(peek_ahead + 1)[peek_ahead]
        while line != self._line_iter.sentinel:
            if line:
                return self._get_indent(line)
            peek_ahead += 1
            line = self._line_iter.peek(peek_ahead + 1)[peek_ahead]
        return 0

    def _get_indent(self, line):
        # type: (unicode) -> int
        for i, s in enumerate(line):
            if not s.isspace():
                return i
        return len(line)

    def _get_initial_indent(self, lines):
        # type: (List[unicode]) -> int
        for line in lines:
            if line:
                return self._get_indent(line)
        return 0

    def _get_min_indent(self, lines):
        # type: (List[unicode]) -> int
        min_indent = None
        for line in lines:
            if line:
                indent = self._get_indent(line)
                if min_indent is None:
                    min_indent = indent
                elif indent < min_indent:
                    min_indent = indent
        return min_indent or 0

    def _indent(self, lines, n=4):
        # type: (List[unicode], int) -> List[unicode]
        return [(' ' * n) + line for line in lines]

    def _is_indented(self, line, indent=1):
        # type: (unicode, int) -> bool
        for i, s in enumerate(line):
            if i >= indent:
                return True
            elif not s.isspace():
                return False
        return False

    def _is_list(self, lines):
        # type: (List[unicode]) -> bool
        if not lines:
            return False
        if _bullet_list_regex.match(lines[0]):
            return True
        if _enumerated_list_regex.match(lines[0]):
            return True
        if len(lines) < 2 or lines[0].endswith('::'):
            return False
        indent = self._get_indent(lines[0])
        next_indent = indent
        for line in lines[1:]:
            if line:
                next_indent = self._get_indent(line)
                break
        return next_indent > indent

    def _is_section_header(self):
        # type: () -> bool
        section = self._line_iter.peek().lower()
        match = _google_section_regex.match(section)
        if match and section.strip(':') in self._sections:
            header_indent = self._get_indent(section)
            section_indent = self._get_current_indent(peek_ahead=1)
            return section_indent > header_indent
        elif self._directive_sections:
            if _directive_regex.match(section):
                for directive_section in self._directive_sections:
                    if section.startswith(directive_section):
                        return True
        return False

    def _is_section_break(self):
        # type: () -> bool
        line = self._line_iter.peek()
        return (not self._line_iter.has_next() or
                self._is_section_header() or
                (self._is_in_section and
                    line and
                    not self._is_indented(line, self._section_indent)))

    def _load_custom_sections(self):
        # type: () -> None

        if self._config.napoleon_custom_sections is not None:
            for entry in self._config.napoleon_custom_sections:
                if isinstance(entry, string_types):
                    # if entry is just a label, add to sections list,
                    # using generic section logic.
                    self._sections[entry.lower()] = self._parse_custom_generic_section
                else:
                    # otherwise, assume entry is container;
                    # [0] is new section, [1] is the section to alias.
                    # in the case of key mismatch, just handle as generic section.
                    self._sections[entry[0].lower()] = \
                        self._sections.get(entry[1].lower(),
                                           self._parse_custom_generic_section)

    def _parse(self):
        # type: () -> None
        self._parsed_lines = self._consume_empty()

        if self._name and (self._what == 'attribute' or self._what == 'data'):
            # Implicit stop using StopIteration no longer allowed in
            # Python 3.7; see PEP 479
            res = []  # type: List[unicode]
            try:
                res = self._parse_attribute_docstring()
            except StopIteration:
                pass
            self._parsed_lines.extend(res)
            return

        while self._line_iter.has_next():
            if self._is_section_header():
                try:
                    section = self._consume_section_header()
                    self._is_in_section = True
                    self._section_indent = self._get_current_indent()
                    if _directive_regex.match(section):
                        lines = [section] + self._consume_to_next_section()
                    else:
                        lines = self._sections[section.lower()](section)
                finally:
                    self._is_in_section = False
                    self._section_indent = 0
            else:
                if not self._parsed_lines:
                    lines = self._consume_contiguous() + self._consume_empty()
                else:
                    lines = self._consume_to_next_section()
            self._parsed_lines.extend(lines)

    def _parse_admonition(self, admonition, section):
        # type (unicode, unicode) -> List[unicode]
        lines = self._consume_to_next_section()
        return self._format_admonition(admonition, lines)

    def _parse_attribute_docstring(self):
        # type: () -> List[unicode]
        _type, _desc = self._consume_inline_attribute()
        lines = self._format_field('', '', _desc)
        if _type:
            lines.extend(['', ':type: %s' % _type])
        return lines

    def _parse_attributes_section(self, section):
        # type: (unicode) -> List[unicode]
        lines = []
        for _name, _type, _desc in self._consume_fields():
            if self._config.napoleon_use_ivar:
                field = ':ivar %s: ' % _name  # type: unicode
                lines.extend(self._format_block(field, _desc))
                if _type:
                    lines.append(':vartype %s: %s' % (_name, _type))
            else:
                lines.extend(['.. attribute:: ' + _name, ''])
                fields = self._format_field('', '', _desc)
                lines.extend(self._indent(fields, 3))
                if _type:
                    lines.append('')
                    lines.extend(self._indent([':type: %s' % _type], 3))
                lines.append('')
        if self._config.napoleon_use_ivar:
            lines.append('')
        return lines

    def _parse_examples_section(self, section):
        # type: (unicode) -> List[unicode]
        labels = {
            'example': _('Example'),
            'examples': _('Examples'),
        }  # type: Dict[unicode, unicode]
        use_admonition = self._config.napoleon_use_admonition_for_examples
        label = labels.get(section.lower(), section)
        return self._parse_generic_section(label, use_admonition)

    def _parse_custom_generic_section(self, section):
        # for now, no admonition for simple custom sections
        return self._parse_generic_section(section, False)

    def _parse_usage_section(self, section):
        # type: (unicode) -> List[unicode]
        header = ['.. rubric:: Usage:', '']  # type: List[unicode]
        block = ['.. code-block:: python', '']  # type: List[unicode]
        lines = self._consume_usage_section()
        lines = self._indent(lines, 3)
        return header + block + lines + ['']

    def _parse_generic_section(self, section, use_admonition):
        # type: (unicode, bool) -> List[unicode]
        lines = self._strip_empty(self._consume_to_next_section())
        lines = self._dedent(lines)
        if use_admonition:
            header = '.. admonition:: %s' % section  # type: unicode
            lines = self._indent(lines, 3)
        else:
            header = '.. rubric:: %s' % section
        if lines:
            return [header, ''] + lines + ['']
        else:
            return [header, '']

    def _parse_keyword_arguments_section(self, section):
        # type: (unicode) -> List[unicode]
        fields = self._consume_fields()
        if self._config.napoleon_use_keyword:
            return self._format_docutils_params(
                fields,
                field_role="keyword",
                type_role="kwtype")
        else:
            return self._format_fields(_('Keyword Arguments'), fields)

    def _parse_methods_section(self, section):
        # type: (unicode) -> List[unicode]
        lines = []  # type: List[unicode]
        for _name, _type, _desc in self._consume_fields(parse_type=False):
            lines.append('.. method:: %s' % _name)
            if _desc:
                lines.extend([u''] + self._indent(_desc, 3))
            lines.append('')
        return lines

    def _parse_notes_section(self, section):
        # type: (unicode) -> List[unicode]
        use_admonition = self._config.napoleon_use_admonition_for_notes
        return self._parse_generic_section(_('Notes'), use_admonition)

    def _parse_other_parameters_section(self, section):
        # type: (unicode) -> List[unicode]
        return self._format_fields(_('Other Parameters'), self._consume_fields())

    def _parse_parameters_section(self, section):
        # type: (unicode) -> List[unicode]
        fields = self._consume_fields()
        if self._config.napoleon_use_param:
            return self._format_docutils_params(fields)
        else:
            return self._format_fields(_('Parameters'), fields)

    def _parse_raises_section(self, section):
        # type: (unicode) -> List[unicode]
        fields = self._consume_fields(parse_type=False, prefer_type=True)
        field_type = ':raises:'
        padding = ' ' * len(field_type)
        multi = len(fields) > 1
        lines = []  # type: List[unicode]
        for _name, _type, _desc in fields:
            _desc = self._strip_empty(_desc)
            has_desc = any(_desc)
            separator = has_desc and ' -- ' or ''
            if _type:
                has_refs = '`' in _type or ':' in _type
                has_space = any(c in ' \t\n\v\f ' for c in _type)

                if not has_refs and not has_space:
                    _type = ':exc:`%s`%s' % (_type, separator)
                elif has_desc and has_space:
                    _type = '*%s*%s' % (_type, separator)
                else:
                    _type = '%s%s' % (_type, separator)

                if has_desc:
                    field = [_type + _desc[0]] + _desc[1:]
                else:
                    field = [_type]
            else:
                field = _desc
            if multi:
                if lines:
                    lines.extend(self._format_block(padding + ' * ', field))
                else:
                    lines.extend(self._format_block(field_type + ' * ', field))
            else:
                lines.extend(self._format_block(field_type + ' ', field))
        if lines and lines[-1]:
            lines.append('')
        return lines

    def _parse_references_section(self, section):
        # type: (unicode) -> List[unicode]
        use_admonition = self._config.napoleon_use_admonition_for_references
        return self._parse_generic_section(_('References'), use_admonition)

    def _parse_returns_section(self, section):
        # type: (unicode) -> List[unicode]
        fields = self._consume_returns_section()
        multi = len(fields) > 1
        if multi:
            use_rtype = False
        else:
            use_rtype = self._config.napoleon_use_rtype

        lines = []  # type: List[unicode]
        for _name, _type, _desc in fields:
            if use_rtype:
                field = self._format_field(_name, '', _desc)
            else:
                field = self._format_field(_name, _type, _desc)

            if multi:
                if lines:
                    lines.extend(self._format_block('          * ', field))
                else:
                    lines.extend(self._format_block(':returns: * ', field))
            else:
                lines.extend(self._format_block(':returns: ', field))
                if _type and use_rtype:
                    lines.extend([':rtype: %s' % _type, ''])
        if lines and lines[-1]:
            lines.append('')
        return lines

    def _parse_see_also_section(self, section):
        # type (unicode) -> List[unicode]
        return self._parse_admonition('seealso', section)

    def _parse_warns_section(self, section):
        # type: (unicode) -> List[unicode]
        return self._format_fields(_('Warns'), self._consume_fields())

    def _parse_yields_section(self, section):
        # type: (unicode) -> List[unicode]
        fields = self._consume_returns_section()
        return self._format_fields(_('Yields'), fields)

    def _partition_field_on_colon(self, line):
        # type: (unicode) -> Tuple[unicode, unicode, unicode]
        before_colon = []
        after_colon = []
        colon = ''  # type: unicode
        found_colon = False
        for i, source in enumerate(_xref_regex.split(line)):
            if found_colon:
                after_colon.append(source)
            else:
                m = _single_colon_regex.search(source)
                if (i % 2) == 0 and m:
                    found_colon = True
                    colon = source[m.start(): m.end()]
                    before_colon.append(source[:m.start()])
                    after_colon.append(source[m.end():])
                else:
                    before_colon.append(source)

        return ("".join(before_colon).strip(),
                colon,
                "".join(after_colon).strip())

    def _strip_empty(self, lines):
        # type: (List[unicode]) -> List[unicode]
        if lines:
            start = -1
            for i, line in enumerate(lines):
                if line:
                    start = i
                    break
            if start == -1:
                lines = []
            end = -1
            for i in reversed(range(len(lines))):
                line = lines[i]
                if line:
                    end = i
                    break
            if start > 0 or end + 1 < len(lines):
                lines = lines[start:end + 1]
        return lines


class NumpyDocstring(GoogleDocstring):
    """Convert NumPy style docstrings to reStructuredText.

    Parameters
    ----------
    docstring : :obj:`str` or :obj:`list` of :obj:`str`
        The docstring to parse, given either as a string or split into
        individual lines.
    config: :obj:`sphinx.ext.napoleon.Config` or :obj:`sphinx.config.Config`
        The configuration settings to use. If not given, defaults to the
        config object on `app`; or if `app` is not given defaults to the
        a new :class:`sphinx.ext.napoleon.Config` object.


    Other Parameters
    ----------------
    app : :class:`sphinx.application.Sphinx`, optional
        Application object representing the Sphinx process.
    what : :obj:`str`, optional
        A string specifying the type of the object to which the docstring
        belongs. Valid values: "module", "class", "exception", "function",
        "method", "attribute".
    name : :obj:`str`, optional
        The fully qualified name of the object.
    obj : module, class, exception, function, method, or attribute
        The object to which the docstring belongs.
    options : :class:`sphinx.ext.autodoc.Options`, optional
        The options given to the directive: an object with attributes
        inherited_members, undoc_members, show_inheritance and noindex that
        are True if the flag option of same name was given to the auto
        directive.


    Example
    -------
    >>> from sphinx.ext.napoleon import Config
    >>> config = Config(napoleon_use_param=True, napoleon_use_rtype=True)
    >>> docstring = '''One line summary.
    ...
    ... Extended description.
    ...
    ... Parameters
    ... ----------
    ... arg1 : int
    ...     Description of `arg1`
    ... arg2 : str
    ...     Description of `arg2`
    ... Returns
    ... -------
    ... str
    ...     Description of return value.
    ... '''
    >>> print(NumpyDocstring(docstring, config))
    One line summary.
    <BLANKLINE>
    Extended description.
    <BLANKLINE>
    :param arg1: Description of `arg1`
    :type arg1: int
    :param arg2: Description of `arg2`
    :type arg2: str
    <BLANKLINE>
    :returns: Description of return value.
    :rtype: str
    <BLANKLINE>

    Methods
    -------
    __str__()
        Return the parsed docstring in reStructuredText format.

        Returns
        -------
        str
            UTF-8 encoded version of the docstring.

    __unicode__()
        Return the parsed docstring in reStructuredText format.

        Returns
        -------
        unicode
            Unicode version of the docstring.

    lines()
        Return the parsed lines of the docstring in reStructuredText format.

        Returns
        -------
        list(str)
            The lines of the docstring in a list.

    """
    def __init__(self, docstring, config=None, app=None, what='', name='',
                 obj=None, options=None):
        # type: (Union[unicode, List[unicode]], SphinxConfig, Sphinx, unicode, unicode, Any, Any) -> None  # NOQA
        self._directive_sections = ['.. index::']
        super(NumpyDocstring, self).__init__(docstring, config, app, what,
                                             name, obj, options)

    def _consume_field(self, parse_type=True, prefer_type=False):
        # type: (bool, bool) -> Tuple[unicode, unicode, List[unicode]]
        line = next(self._line_iter)
        if parse_type:
            _name, _, _type = self._partition_field_on_colon(line)
        else:
            _name, _type = line, ''
        _name, _type = _name.strip(), _type.strip()
        _name = self._escape_args_and_kwargs(_name)

        if prefer_type and not _type:
            _type, _name = _name, _type
        indent = self._get_indent(line) + 1
        _desc = self._dedent(self._consume_indented_block(indent))
        _desc = self.__class__(_desc, self._config).lines()
        return _name, _type, _desc

    def _consume_returns_section(self):
        # type: () -> List[Tuple[unicode, unicode, List[unicode]]]
        return self._consume_fields(prefer_type=True)

    def _consume_section_header(self):
        # type: () -> unicode
        section = next(self._line_iter)
        if not _directive_regex.match(section):
            # Consume the header underline
            next(self._line_iter)
        return section

    def _is_section_break(self):
        # type: () -> bool
        line1, line2 = self._line_iter.peek(2)
        return (not self._line_iter.has_next() or
                self._is_section_header() or
                ['', ''] == [line1, line2] or
                (self._is_in_section and
                    line1 and
                    not self._is_indented(line1, self._section_indent)))

    def _is_section_header(self):
        # type: () -> bool
        section, underline = self._line_iter.peek(2)
        section = section.lower()
        if section in self._sections and isinstance(underline, string_types):
            return bool(_numpy_section_regex.match(underline))
        elif self._directive_sections:
            if _directive_regex.match(section):
                for directive_section in self._directive_sections:
                    if section.startswith(directive_section):
                        return True
        return False

    _name_rgx = re.compile(r"^\s*(:(?P<role>\w+):`(?P<name>[a-zA-Z0-9_.-]+)`|"
                           r" (?P<name2>[a-zA-Z0-9_.-]+))\s*", re.X)

    def _parse_see_also_section(self, section):
        # type: (unicode) -> List[unicode]
        lines = self._consume_to_next_section()
        try:
            return self._parse_numpydoc_see_also_section(lines)
        except ValueError:
            return self._format_admonition('seealso', lines)

    def _parse_numpydoc_see_also_section(self, content):
        # type: (List[unicode]) -> List[unicode]
        """
        Derived from the NumpyDoc implementation of _parse_see_also.

        See Also
        --------
        func_name : Descriptive text
            continued text
        another_func_name : Descriptive text
        func_name1, func_name2, :meth:`func_name`, func_name3

        """
        items = []

        def parse_item_name(text):
            # type: (unicode) -> Tuple[unicode, unicode]
            """Match ':role:`name`' or 'name'"""
            m = self._name_rgx.match(text)
            if m:
                g = m.groups()
                if g[1] is None:
                    return g[3], None
                else:
                    return g[2], g[1]
            raise ValueError("%s is not a item name" % text)

        def push_item(name, rest):
            # type: (unicode, List[unicode]) -> None
            if not name:
                return
            name, role = parse_item_name(name)
            items.append((name, list(rest), role))
            del rest[:]

        current_func = None
        rest = []  # type: List[unicode]

        for line in content:
            if not line.strip():
                continue

            m = self._name_rgx.match(line)
            if m and line[m.end():].strip().startswith(':'):
                push_item(current_func, rest)
                current_func, line = line[:m.end()], line[m.end():]
                rest = [line.split(':', 1)[1].strip()]
                if not rest[0]:
                    rest = []
            elif not line.startswith(' '):
                push_item(current_func, rest)
                current_func = None
                if ',' in line:
                    for func in line.split(','):
                        if func.strip():
                            push_item(func, [])
                elif line.strip():
                    current_func = line
            elif current_func is not None:
                rest.append(line.strip())
        push_item(current_func, rest)

        if not items:
            return []

        roles = {
            'method': 'meth',
            'meth': 'meth',
            'function': 'func',
            'func': 'func',
            'class': 'class',
            'exception': 'exc',
            'exc': 'exc',
            'object': 'obj',
            'obj': 'obj',
            'module': 'mod',
            'mod': 'mod',
            'data': 'data',
            'constant': 'const',
            'const': 'const',
            'attribute': 'attr',
            'attr': 'attr'
        }  # type: Dict[unicode, unicode]
        if self._what is None:
            func_role = 'obj'  # type: unicode
        else:
            func_role = roles.get(self._what, '')
        lines = []  # type: List[unicode]
        last_had_desc = True
        for func, desc, role in items:
            if role:
                link = ':%s:`%s`' % (role, func)
            elif func_role:
                link = ':%s:`%s`' % (func_role, func)
            else:
                link = "`%s`_" % func
            if desc or last_had_desc:
                lines += ['']
                lines += [link]
            else:
                lines[-1] += ", %s" % link
            if desc:
                lines += self._indent([' '.join(desc)])
                last_had_desc = True
            else:
                last_had_desc = False
        lines += ['']

        return self._format_admonition('seealso', lines)
