# -*- coding: utf-8 -*-
"""
    sphinx.writers.latex
    ~~~~~~~~~~~~~~~~~~~~

    Custom docutils writer for LaTeX.

    Much of this code is adapted from Dave Kuhlman's "docpy" writer from his
    docutils sandbox.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import sys
import warnings
from collections import defaultdict
from os import path

from docutils import nodes, writers
from docutils.writers.latex2e import Babel
from six import itervalues, text_type

from sphinx import addnodes
from sphinx import highlighting
from sphinx.deprecation import RemovedInSphinx30Warning
from sphinx.errors import SphinxError
from sphinx.locale import admonitionlabels, _, __
from sphinx.util import split_into, logging
from sphinx.util.i18n import format_date
from sphinx.util.nodes import clean_astext, get_prev_node
from sphinx.util.template import LaTeXRenderer
from sphinx.util.texescape import tex_escape_map, tex_replace_map

try:
    from docutils.utils.roman import toRoman
except ImportError:
    # In Debain/Ubuntu, roman package is provided as roman, not as docutils.utils.roman
    from roman import toRoman

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Iterator, List, Pattern, Tuple, Set, Union  # NOQA
    from sphinx.builder import Builder  # NOQA

logger = logging.getLogger(__name__)

SHORTHANDOFF = r'''
\ifdefined\shorthandoff
  \ifnum\catcode`\=\string=\active\shorthandoff{=}\fi
  \ifnum\catcode`\"=\active\shorthandoff{"}\fi
\fi
'''

MAX_CITATION_LABEL_LENGTH = 8
LATEXSECTIONNAMES = ["part", "chapter", "section", "subsection",
                     "subsubsection", "paragraph", "subparagraph"]
ENUMERATE_LIST_STYLE = defaultdict(lambda: r'\arabic',
                                   {
                                       'arabic': r'\arabic',
                                       'loweralpha': r'\alph',
                                       'upperalpha': r'\Alph',
                                       'lowerroman': r'\roman',
                                       'upperroman': r'\Roman',
                                   })  # type: Dict[unicode, unicode]

DEFAULT_SETTINGS = {
    'latex_engine':    'pdflatex',
    'papersize':       'letterpaper',
    'pointsize':       '10pt',
    'pxunit':          '.75bp',
    'classoptions':    '',
    'extraclassoptions': '',
    'maxlistdepth':    '',
    'sphinxpkgoptions':     '',
    'sphinxsetup':     '',
    'fvset':           '\\fvset{fontsize=\\small}',
    'passoptionstopackages': '',
    'geometry':        '\\usepackage{geometry}',
    'inputenc':        '',
    'utf8extra':       '',
    'cmappkg':         '\\usepackage{cmap}',
    'fontenc':         '\\usepackage[T1]{fontenc}',
    'amsmath':         '\\usepackage{amsmath,amssymb,amstext}',
    'multilingual':    '',
    'babel':           '\\usepackage{babel}',
    'polyglossia':     '',
    'fontpkg':         '\\usepackage{times}',
    'fncychap':        '\\usepackage[Bjarne]{fncychap}',
    'hyperref':        ('% Include hyperref last.\n'
                        '\\usepackage{hyperref}\n'
                        '% Fix anchor placement for figures with captions.\n'
                        '\\usepackage{hypcap}% it must be loaded after hyperref.\n'
                        '% Set up styles of URL: it should be placed after hyperref.\n'
                        '\\urlstyle{same}'),
    'usepackages':     '',
    'numfig_format':   '',
    'contentsname':    '',
    'preamble':        '',
    'title':           '',
    'date':            '',
    'release':         '',
    'author':          '',
    'logo':            '\\vbox{}',
    'releasename':     '',
    'makeindex':       '\\makeindex',
    'shorthandoff':    '',
    'maketitle':       '\\sphinxmaketitle',
    'tableofcontents': '\\sphinxtableofcontents',
    'atendofbody':     '',
    'printindex':      '\\printindex',
    'transition':      '\n\n\\bigskip\\hrule\\bigskip\n\n',
    'figure_align':    'htbp',
    'tocdepth':        '',
    'secnumdepth':     '',
    'pageautorefname': '',
    'translatablestrings': '',
}  # type: Dict[unicode, unicode]

ADDITIONAL_SETTINGS = {
    'pdflatex': {
        'inputenc':     '\\usepackage[utf8]{inputenc}',
        'utf8extra':   ('\\ifdefined\\DeclareUnicodeCharacter\n'
                        '% support both utf8 and utf8x syntaxes\n'
                        '\\edef\\sphinxdqmaybe{'
                        '\\ifdefined\\DeclareUnicodeCharacterAsOptional'
                        '\\string"\\fi}\n'
                        '  \\DeclareUnicodeCharacter{\\sphinxdqmaybe00A0}'
                        '{\\nobreakspace}\n'
                        '  \\DeclareUnicodeCharacter{\\sphinxdqmaybe2500}'
                        '{\\sphinxunichar{2500}}\n'
                        '  \\DeclareUnicodeCharacter{\\sphinxdqmaybe2502}'
                        '{\\sphinxunichar{2502}}\n'
                        '  \\DeclareUnicodeCharacter{\\sphinxdqmaybe2514}'
                        '{\\sphinxunichar{2514}}\n'
                        '  \\DeclareUnicodeCharacter{\\sphinxdqmaybe251C}'
                        '{\\sphinxunichar{251C}}\n'
                        '  \\DeclareUnicodeCharacter{\\sphinxdqmaybe2572}'
                        '{\\textbackslash}\n'
                        '\\fi'),
    },
    'xelatex': {
        'latex_engine': 'xelatex',
        'polyglossia':  '\\usepackage{polyglossia}',
        'babel':        '',
        'fontenc':      '\\usepackage{fontspec}',
        'fontpkg':      '',
        'utf8extra':   ('\\catcode`^^^^00a0\\active\\protected\\def^^^^00a0'
                        '{\\leavevmode\\nobreak\\ }'),
        'fvset':        '\\fvset{fontsize=auto}',
    },
    'lualatex': {
        'latex_engine': 'lualatex',
        'polyglossia':  '\\usepackage{polyglossia}',
        'babel':        '',
        'fontenc':      '\\usepackage{fontspec}',
        'fontpkg':      '',
        'utf8extra':   ('\\catcode`^^^^00a0\\active\\protected\\def^^^^00a0'
                        '{\\leavevmode\\nobreak\\ }'),
        'fvset':        '\\fvset{fontsize=auto}',
    },
    'platex': {
        'latex_engine': 'platex',
        'babel':        '',
        'classoptions': ',dvipdfmx',
        'fncychap':     '',
        'geometry':     '\\usepackage[dvipdfm]{geometry}',
    },
}  # type: Dict[unicode, Dict[unicode, unicode]]

EXTRA_RE = re.compile(r'^(.*\S)\s+\(([^()]*)\)\s*$')


class collected_footnote(nodes.footnote):
    """Footnotes that are collected are assigned this class."""


class UnsupportedError(SphinxError):
    category = 'Markup is unsupported in LaTeX'


class LaTeXWriter(writers.Writer):

    supported = ('sphinxlatex',)

    settings_spec = ('LaTeX writer options', '', (
        ('Document name', ['--docname'], {'default': ''}),
        ('Document class', ['--docclass'], {'default': 'manual'}),
        ('Author', ['--author'], {'default': ''}),
    ))
    settings_defaults = {}  # type: Dict

    output = None

    def __init__(self, builder):
        # type: (Builder) -> None
        writers.Writer.__init__(self)
        self.builder = builder

    def translate(self):
        # type: () -> None
        visitor = self.builder.create_translator(self.document, self.builder)
        self.document.walkabout(visitor)
        self.output = visitor.astext()


# Helper classes

class ExtBabel(Babel):
    cyrillic_languages = ('bulgarian', 'kazakh', 'mongolian', 'russian', 'ukrainian')

    def __init__(self, language_code, use_polyglossia=False):
        # type: (unicode, bool) -> None
        self.language_code = language_code
        self.use_polyglossia = use_polyglossia
        self.supported = True
        super(ExtBabel, self).__init__(language_code or '')

    def get_shorthandoff(self):
        # type: () -> unicode
        warnings.warn('ExtBabel.get_shorthandoff() is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return SHORTHANDOFF

    def uses_cyrillic(self):
        # type: () -> bool
        return self.language in self.cyrillic_languages

    def is_supported_language(self):
        # type: () -> bool
        return self.supported

    def language_name(self, language_code):
        # type: (unicode) -> unicode
        language = super(ExtBabel, self).language_name(language_code)
        if language == 'ngerman' and self.use_polyglossia:
            # polyglossia calls new orthography (Neue Rechtschreibung) as
            # german (with new spelling option).
            return 'german'
        elif not language:
            self.supported = False
            return 'english'  # fallback to english
        else:
            return language

    def get_mainlanguage_options(self):
        # type: () -> unicode
        """Return options for polyglossia's ``\\setmainlanguage``."""
        if self.use_polyglossia is False:
            return None
        elif self.language == 'german':
            language = super(ExtBabel, self).language_name(self.language_code)
            if language == 'ngerman':
                return 'spelling=new'
            else:
                return 'spelling=old'
        else:
            return None


class Table(object):
    """A table data"""

    def __init__(self, node):
        # type: (nodes.table) -> None
        self.header = []                        # type: List[unicode]
        self.body = []                          # type: List[unicode]
        self.align = node.get('align')
        self.colcount = 0
        self.colspec = None                     # type: unicode
        self.colwidths = []                     # type: List[int]
        self.has_problematic = False
        self.has_oldproblematic = False
        self.has_verbatim = False
        self.caption = None                     # type: List[unicode]
        self.stubs = []                         # type: List[int]

        # current position
        self.col = 0
        self.row = 0

        # for internal use
        self.classes = node.get('classes', [])  # type: List[unicode]
        self.cells = defaultdict(int)           # type: Dict[Tuple[int, int], int]
                                                # it maps table location to cell_id
                                                # (cell = rectangular area)
        self.cell_id = 0                        # last assigned cell_id

    @property
    def caption_footnotetexts(self):
        # type: () -> List[unicode]
        warnings.warn('table.caption_footnotetexts is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return []

    @property
    def header_footnotetexts(self):
        # type: () -> List[unicode]
        warnings.warn('table.header_footnotetexts is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return []

    def is_longtable(self):
        # type: () -> bool
        """True if and only if table uses longtable environment."""
        return self.row > 30 or 'longtable' in self.classes

    def get_table_type(self):
        # type: () -> unicode
        """Returns the LaTeX environment name for the table.

        The class currently supports:

        * longtable
        * tabular
        * tabulary
        """
        if self.is_longtable():
            return 'longtable'
        elif self.has_verbatim:
            return 'tabular'
        elif self.colspec:
            return 'tabulary'
        elif self.has_problematic or (self.colwidths and 'colwidths-given' in self.classes):
            return 'tabular'
        else:
            return 'tabulary'

    def get_colspec(self):
        # type: () -> unicode
        """Returns a column spec of table.

        This is what LaTeX calls the 'preamble argument' of the used table environment.

        .. note:: the ``\\X`` and ``T`` column type specifiers are defined in ``sphinx.sty``.
        """
        if self.colspec:
            return self.colspec
        elif self.colwidths and 'colwidths-given' in self.classes:
            total = sum(self.colwidths)
            colspecs = ['\\X{%d}{%d}' % (width, total) for width in self.colwidths]
            return '{|%s|}\n' % '|'.join(colspecs)
        elif self.has_problematic:
            return '{|*{%d}{\\X{1}{%d}|}}\n' % (self.colcount, self.colcount)
        elif self.get_table_type() == 'tabulary':
            # sphinx.sty sets T to be J by default.
            return '{|' + ('T|' * self.colcount) + '}\n'
        elif self.has_oldproblematic:
            return '{|*{%d}{\\X{1}{%d}|}}\n' % (self.colcount, self.colcount)
        else:
            return '{|' + ('l|' * self.colcount) + '}\n'

    def add_cell(self, height, width):
        # type: (int, int) -> None
        """Adds a new cell to a table.

        It will be located at current position: (``self.row``, ``self.col``).
        """
        self.cell_id += 1
        for col in range(width):
            for row in range(height):
                assert self.cells[(self.row + row, self.col + col)] == 0
                self.cells[(self.row + row, self.col + col)] = self.cell_id

    def cell(self, row=None, col=None):
        # type: (int, int) -> TableCell
        """Returns a cell object (i.e. rectangular area) containing given position.

        If no option arguments: ``row`` or ``col`` are given, the current position;
        ``self.row`` and ``self.col`` are used to get a cell object by default.
        """
        try:
            if row is None:
                row = self.row
            if col is None:
                col = self.col
            return TableCell(self, row, col)
        except IndexError:
            return None


class TableCell(object):
    """A cell data of tables."""

    def __init__(self, table, row, col):
        # type: (Table, int, int) -> None
        if table.cells[(row, col)] == 0:
            raise IndexError

        self.table = table
        self.cell_id = table.cells[(row, col)]
        self.row = row
        self.col = col

        # adjust position for multirow/multicol cell
        while table.cells[(self.row - 1, self.col)] == self.cell_id:
            self.row -= 1
        while table.cells[(self.row, self.col - 1)] == self.cell_id:
            self.col -= 1

    @property
    def width(self):
        # type: () -> int
        """Returns the cell width."""
        width = 0
        while self.table.cells[(self.row, self.col + width)] == self.cell_id:
            width += 1
        return width

    @property
    def height(self):
        # type: () -> int
        """Returns the cell height."""
        height = 0
        while self.table.cells[(self.row + height, self.col)] == self.cell_id:
            height += 1
        return height


def escape_abbr(text):
    # type: (unicode) -> unicode
    """Adjust spacing after abbreviations."""
    return re.sub(r'\.(?=\s|$)', r'.\@', text)


def rstdim_to_latexdim(width_str, scale = 100):
    # type: (unicode, int) -> unicode
    """Convert `width_str` with rst length to LaTeX length."""
    match = re.match(r'^(\d*\.?\d*)\s*(\S*)$', width_str)
    if not match:
        raise ValueError
    res = width_str
    amount, unit = match.groups()[:2]
    if scale == 100:
        float(amount)  # validate amount is float
        if unit in ('', "px"):
            res = "%s\\sphinxpxdimen" % amount
        elif unit == 'pt':
            res = '%sbp' % amount  # convert to 'bp'
        elif unit == "%":
            res = "%.3f\\linewidth" % (float(amount) / 100.0)
    else:
        amount_float = float(amount) * scale / 100.0
        if unit in ('', "px"):
            res = "%.5f\\sphinxpxdimen" % amount_float
        elif unit == 'pt':
            res = '%.5fbp' % amount_float
        elif unit == "%":
            res = "%.5f\\linewidth" % (amount_float / 100.0)
        else:
            res = "%.5f%s" % (amount_float, unit)
    return res


class LaTeXTranslator(nodes.NodeVisitor):

    secnumdepth = 2  # legacy sphinxhowto.cls uses this, whereas article.cls
    # default is originally 3. For book/report, 2 is already LaTeX default.
    ignore_missing_images = False

    # sphinx specific document classes
    docclasses = ('howto', 'manual')

    def __init__(self, document, builder):
        # type: (nodes.Node, Builder) -> None
        nodes.NodeVisitor.__init__(self, document)
        self.builder = builder
        self.body = []  # type: List[unicode]

        # flags
        self.in_title = 0
        self.in_production_list = 0
        self.in_footnote = 0
        self.in_caption = 0
        self.in_term = 0
        self.needs_linetrimming = 0
        self.in_minipage = 0
        self.first_document = 1
        self.this_is_the_title = 1
        self.literal_whitespace = 0
        self.no_contractions = 0
        self.in_parsed_literal = 0
        self.compact_list = 0
        self.first_param = 0

        # sort out some elements
        self.elements = DEFAULT_SETTINGS.copy()
        self.elements.update(ADDITIONAL_SETTINGS.get(builder.config.latex_engine, {}))
        # for xelatex+French, don't use polyglossia
        if self.elements['latex_engine'] == 'xelatex':
            if builder.config.language:
                if builder.config.language[:2] == 'fr':
                    self.elements.update({
                        'polyglossia': '',
                        'babel':       '\\usepackage{babel}',
                    })
        # allow the user to override them all
        self.elements.update(builder.config.latex_elements)

        # but some have other interface in config file
        self.elements.update({
            'wrapperclass': self.format_docclass(document.settings.docclass),
            # if empty, the title is set to the first section title
            'title':        document.settings.title,    # treat as a raw LaTeX code
            'release':      self.encode(builder.config.release),
            'author':       document.settings.author,   # treat as a raw LaTeX code
            'indexname':    _('Index'),
            'use_xindy':    builder.config.latex_use_xindy,
        })
        if not self.elements['releasename'] and self.elements['release']:
            self.elements.update({
                'releasename':  _('Release'),
            })

        # we assume LaTeX class provides \chapter command except in case
        # of non-Japanese 'howto' case
        self.sectionnames = LATEXSECTIONNAMES[:]
        if document.settings.docclass == 'howto':
            docclass = builder.config.latex_docclass.get('howto', 'article')
            if docclass[0] == 'j':  # Japanese class...
                pass
            else:
                self.sectionnames.remove('chapter')
        else:
            docclass = builder.config.latex_docclass.get('manual', 'report')
        self.elements['docclass'] = docclass

        # determine top section level
        self.top_sectionlevel = 1
        if builder.config.latex_toplevel_sectioning:
            try:
                self.top_sectionlevel = \
                    self.sectionnames.index(builder.config.latex_toplevel_sectioning)
            except ValueError:
                logger.warning(__('unknown %r toplevel_sectioning for class %r') %
                               (builder.config.latex_toplevel_sectioning, docclass))

        if builder.config.today:
            self.elements['date'] = builder.config.today
        else:
            self.elements['date'] = format_date(builder.config.today_fmt or _('%b %d, %Y'),
                                                language=builder.config.language)

        if builder.config.numfig:
            self.numfig_secnum_depth = builder.config.numfig_secnum_depth
            if self.numfig_secnum_depth > 0:  # default is 1
                # numfig_secnum_depth as passed to sphinx.sty indices same names as in
                # LATEXSECTIONNAMES but with -1 for part, 0 for chapter, 1 for section...
                if len(self.sectionnames) < len(LATEXSECTIONNAMES) and \
                   self.top_sectionlevel > 0:
                    self.numfig_secnum_depth += self.top_sectionlevel
                else:
                    self.numfig_secnum_depth += self.top_sectionlevel - 1
                # this (minus one) will serve as minimum to LaTeX's secnumdepth
                self.numfig_secnum_depth = min(self.numfig_secnum_depth,
                                               len(LATEXSECTIONNAMES) - 1)
                # if passed key value is < 1 LaTeX will act as if 0; see sphinx.sty
                self.elements['sphinxpkgoptions'] += \
                    (',numfigreset=%s' % self.numfig_secnum_depth)
            else:
                self.elements['sphinxpkgoptions'] += ',nonumfigreset'
            try:
                if builder.config.math_numfig:
                    self.elements['sphinxpkgoptions'] += ',mathnumfig'
            except AttributeError:
                pass

        if builder.config.latex_logo:
            # no need for \\noindent here, used in flushright
            self.elements['logo'] = '\\sphinxincludegraphics{%s}\\par' % \
                                    path.basename(builder.config.latex_logo)

        if (builder.config.language and builder.config.language != 'ja' and
                'fncychap' not in builder.config.latex_elements):
            # use Sonny style if any language specified
            self.elements['fncychap'] = ('\\usepackage[Sonny]{fncychap}\n'
                                         '\\ChNameVar{\\Large\\normalfont'
                                         '\\sffamily}\n\\ChTitleVar{\\Large'
                                         '\\normalfont\\sffamily}')

        self.babel = ExtBabel(builder.config.language,
                              not self.elements['babel'])
        if builder.config.language and not self.babel.is_supported_language():
            # emit warning if specified language is invalid
            # (only emitting, nothing changed to processing)
            logger.warning(__('no Babel option known for language %r'),
                           builder.config.language)

        # set up multilingual module...
        # 'babel' key is public and user setting must be obeyed
        if self.elements['babel']:
            self.elements['classoptions'] += ',' + self.babel.get_language()
            # this branch is not taken for xelatex/lualatex if default settings
            self.elements['multilingual'] = self.elements['babel']
            if builder.config.language:
                self.elements['shorthandoff'] = SHORTHANDOFF

                # Times fonts don't work with Cyrillic languages
                if self.babel.uses_cyrillic() \
                   and 'fontpkg' not in builder.config.latex_elements:
                    self.elements['fontpkg'] = ''
        elif self.elements['polyglossia']:
            self.elements['classoptions'] += ',' + self.babel.get_language()
            options = self.babel.get_mainlanguage_options()
            if options:
                mainlanguage = r'\setmainlanguage[%s]{%s}' % (options,
                                                              self.babel.get_language())
            else:
                mainlanguage = r'\setmainlanguage{%s}' % self.babel.get_language()

            self.elements['multilingual'] = '%s\n%s' % (self.elements['polyglossia'],
                                                        mainlanguage)

        if getattr(builder, 'usepackages', None):
            def declare_package(packagename, options=None):
                # type:(unicode, unicode) -> unicode
                if options:
                    return '\\usepackage[%s]{%s}' % (options, packagename)
                else:
                    return '\\usepackage{%s}' % (packagename,)
            usepackages = (declare_package(*p) for p in builder.usepackages)
            self.elements['usepackages'] += "\n".join(usepackages)

        minsecnumdepth = self.secnumdepth  # 2 from legacy sphinx manual/howto
        if document.get('tocdepth'):
            # reduce tocdepth if `part` or `chapter` is used for top_sectionlevel
            #   tocdepth = -1: show only parts
            #   tocdepth =  0: show parts and chapters
            #   tocdepth =  1: show parts, chapters and sections
            #   tocdepth =  2: show parts, chapters, sections and subsections
            #   ...
            tocdepth = document['tocdepth'] + self.top_sectionlevel - 2
            if len(self.sectionnames) < len(LATEXSECTIONNAMES) and \
               self.top_sectionlevel > 0:
                tocdepth += 1  # because top_sectionlevel is shifted by -1
            if tocdepth > len(LATEXSECTIONNAMES) - 2:  # default is 5 <-> subparagraph
                logger.warning(__('too large :maxdepth:, ignored.'))
                tocdepth = len(LATEXSECTIONNAMES) - 2

            self.elements['tocdepth'] = '\\setcounter{tocdepth}{%d}' % tocdepth
            minsecnumdepth = max(minsecnumdepth, tocdepth)

        if builder.config.numfig and (builder.config.numfig_secnum_depth > 0):
            minsecnumdepth = max(minsecnumdepth, self.numfig_secnum_depth - 1)

        if minsecnumdepth > self.secnumdepth:
            self.elements['secnumdepth'] = '\\setcounter{secnumdepth}{%d}' %\
                                           minsecnumdepth

        if getattr(document.settings, 'contentsname', None):
            self.elements['contentsname'] = \
                self.babel_renewcommand('\\contentsname', document.settings.contentsname)

        if self.elements['maxlistdepth']:
            self.elements['sphinxpkgoptions'] += (',maxlistdepth=%s' %
                                                  self.elements['maxlistdepth'])
        if self.elements['sphinxpkgoptions']:
            self.elements['sphinxpkgoptions'] = ('[%s]' %
                                                 self.elements['sphinxpkgoptions'])
        if self.elements['sphinxsetup']:
            self.elements['sphinxsetup'] = ('\\sphinxsetup{%s}' %
                                            self.elements['sphinxsetup'])
        if self.elements['extraclassoptions']:
            self.elements['classoptions'] += ',' + \
                                             self.elements['extraclassoptions']
        self.elements['translatablestrings'] = (
            self.babel_renewcommand(
                '\\literalblockcontinuedname', self.encode(_('continued from previous page'))
            ) +
            self.babel_renewcommand(
                '\\literalblockcontinuesname', self.encode(_('continues on next page'))
            ) +
            self.babel_renewcommand(
                '\\sphinxnonalphabeticalgroupname', self.encode(_('Non-alphabetical'))
            ) +
            self.babel_renewcommand(
                '\\sphinxsymbolsname', self.encode(_('Symbols'))
            ) +
            self.babel_renewcommand(
                '\\sphinxnumbersname', self.encode(_('Numbers'))
            )
        )
        self.elements['pageautorefname'] = \
            self.babel_defmacro('\\pageautorefname', self.encode(_('page')))
        self.elements['numfig_format'] = self.generate_numfig_format(builder)

        self.highlighter = highlighting.PygmentsBridge('latex', builder.config.pygments_style)
        self.context = []               # type: List[Any]
        self.descstack = []             # type: List[unicode]
        self.table = None               # type: Table
        self.next_table_colspec = None  # type: unicode
        self.bodystack = []             # type: List[List[unicode]]
        self.footnote_restricted = False
        self.pending_footnotes = []     # type: List[nodes.footnote_reference]
        self.curfilestack = []          # type: List[unicode]
        self.handled_abbrs = set()      # type: Set[unicode]

    def pushbody(self, newbody):
        # type: (List[unicode]) -> None
        self.bodystack.append(self.body)
        self.body = newbody

    def popbody(self):
        # type: () -> List[unicode]
        body = self.body
        self.body = self.bodystack.pop()
        return body

    def restrict_footnote(self, node):
        # type: (nodes.Node) -> None
        warnings.warn('LaTeXWriter.restrict_footnote() is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)

        if self.footnote_restricted is False:
            self.footnote_restricted = node
            self.pending_footnotes = []

    def unrestrict_footnote(self, node):
        # type: (nodes.Node) -> None
        warnings.warn('LaTeXWriter.unrestrict_footnote() is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)

        if self.footnote_restricted == node:
            self.footnote_restricted = False
            for footnode in self.pending_footnotes:
                footnode['footnotetext'] = True
                footnode.walkabout(self)
            self.pending_footnotes = []

    def format_docclass(self, docclass):
        # type: (unicode) -> unicode
        """ prepends prefix to sphinx document classes
        """
        if docclass in self.docclasses:
            docclass = 'sphinx' + docclass
        return docclass

    def astext(self):
        # type: () -> unicode
        self.elements.update({
            'body': u''.join(self.body),
            'indices': self.generate_indices()
        })
        return self.render('latex.tex_t', self.elements)

    def hypertarget(self, id, withdoc=True, anchor=True):
        # type: (unicode, bool, bool) -> unicode
        if withdoc:
            id = self.curfilestack[-1] + ':' + id
        return (anchor and '\\phantomsection' or '') + \
            '\\label{%s}' % self.idescape(id)

    def hypertarget_to(self, node, anchor=False):
        # type: (nodes.Node, bool) -> unicode
        labels = ''.join(self.hypertarget(node_id, anchor=False) for node_id in node['ids'])
        if anchor:
            return r'\phantomsection' + labels
        else:
            return labels

    def hyperlink(self, id):
        # type: (unicode) -> unicode
        return '{\\hyperref[%s]{' % self.idescape(id)

    def hyperpageref(self, id):
        # type: (unicode) -> unicode
        return '\\autopageref*{%s}' % self.idescape(id)

    def idescape(self, id):
        # type: (unicode) -> unicode
        return '\\detokenize{%s}' % text_type(id).translate(tex_replace_map).\
            encode('ascii', 'backslashreplace').decode('ascii').\
            replace('\\', '_')

    def babel_renewcommand(self, command, definition):
        # type: (unicode, unicode) -> unicode
        if self.elements['multilingual']:
            prefix = '\\addto\\captions%s{' % self.babel.get_language()
            suffix = '}'
        else:  # babel is disabled (mainly for Japanese environment)
            prefix = ''
            suffix = ''

        return ('%s\\renewcommand{%s}{%s}%s\n' % (prefix, command, definition, suffix))

    def babel_defmacro(self, name, definition):
        # type: (unicode, unicode) -> unicode
        if self.elements['babel']:
            prefix = '\\addto\\extras%s{' % self.babel.get_language()
            suffix = '}'
        else:  # babel is disabled (mainly for Japanese environment)
            prefix = ''
            suffix = ''

        return ('%s\\def%s{%s}%s\n' % (prefix, name, definition, suffix))

    def generate_numfig_format(self, builder):
        # type: (Builder) -> unicode
        ret = []  # type: List[unicode]
        figure = self.builder.config.numfig_format['figure'].split('%s', 1)
        if len(figure) == 1:
            ret.append('\\def\\fnum@figure{%s}\n' %
                       text_type(figure[0]).strip().translate(tex_escape_map))
        else:
            definition = escape_abbr(text_type(figure[0]).translate(tex_escape_map))
            ret.append(self.babel_renewcommand('\\figurename', definition))
            ret.append('\\makeatletter\n')
            ret.append('\\def\\fnum@figure{\\figurename\\thefigure{}%s}\n' %
                       text_type(figure[1]).translate(tex_escape_map))
            ret.append('\\makeatother\n')

        table = self.builder.config.numfig_format['table'].split('%s', 1)
        if len(table) == 1:
            ret.append('\\def\\fnum@table{%s}\n' %
                       text_type(table[0]).strip().translate(tex_escape_map))
        else:
            definition = escape_abbr(text_type(table[0]).translate(tex_escape_map))
            ret.append(self.babel_renewcommand('\\tablename', definition))
            ret.append('\\makeatletter\n')
            ret.append('\\def\\fnum@table{\\tablename\\thetable{}%s}\n' %
                       text_type(table[1]).translate(tex_escape_map))
            ret.append('\\makeatother\n')

        codeblock = self.builder.config.numfig_format['code-block'].split('%s', 1)
        if len(codeblock) == 1:
            pass  # FIXME
        else:
            definition = text_type(codeblock[0]).strip().translate(tex_escape_map)
            ret.append(self.babel_renewcommand('\\literalblockname', definition))
            if codeblock[1]:
                pass  # FIXME

        return ''.join(ret)

    def generate_indices(self):
        # type: (Builder) -> unicode
        def generate(content, collapsed):
            # type: (List[Tuple[unicode, List[Tuple[unicode, unicode, unicode, unicode, unicode]]]], bool) -> None  # NOQA
            ret.append('\\begin{sphinxtheindex}\n')
            ret.append('\\let\\bigletter\\sphinxstyleindexlettergroup\n')
            for i, (letter, entries) in enumerate(content):
                if i > 0:
                    ret.append('\\indexspace\n')
                ret.append('\\bigletter{%s}\n' %
                           text_type(letter).translate(tex_escape_map))
                for entry in entries:
                    if not entry[3]:
                        continue
                    ret.append('\\item\\relax\\sphinxstyleindexentry{%s}' %
                               self.encode(entry[0]))
                    if entry[4]:
                        # add "extra" info
                        ret.append('\\sphinxstyleindexextra{%s}' % self.encode(entry[4]))
                    ret.append('\\sphinxstyleindexpageref{%s:%s}\n' %
                               (entry[2], self.idescape(entry[3])))
            ret.append('\\end{sphinxtheindex}\n')

        ret = []
        # latex_domain_indices can be False/True or a list of index names
        indices_config = self.builder.config.latex_domain_indices
        if indices_config:
            for domain in itervalues(self.builder.env.domains):
                for indexcls in domain.indices:
                    indexname = '%s-%s' % (domain.name, indexcls.name)
                    if isinstance(indices_config, list):
                        if indexname not in indices_config:
                            continue
                    content, collapsed = indexcls(domain).generate(
                        self.builder.docnames)
                    if not content:
                        continue
                    ret.append(u'\\renewcommand{\\indexname}{%s}\n' %
                               indexcls.localname)
                    generate(content, collapsed)

        return ''.join(ret)

    def render(self, template_name, variables):
        # type: (unicode, Dict) -> unicode
        for template_dir in self.builder.config.templates_path:
            template = path.join(self.builder.confdir, template_dir,
                                 template_name)
            if path.exists(template):
                return LaTeXRenderer().render(template, variables)

        return LaTeXRenderer().render(template_name, variables)

    def visit_document(self, node):
        # type: (nodes.Node) -> None
        self.curfilestack.append(node.get('docname', ''))
        if self.first_document == 1:
            # the first document is all the regular content ...
            self.first_document = 0
        elif self.first_document == 0:
            # ... and all others are the appendices
            self.body.append(u'\n\\appendix\n')
            self.first_document = -1
        if 'docname' in node:
            self.body.append(self.hypertarget(':doc'))
        # "- 1" because the level is increased before the title is visited
        self.sectionlevel = self.top_sectionlevel - 1

    def depart_document(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_start_of_file(self, node):
        # type: (nodes.Node) -> None
        self.curfilestack.append(node['docname'])

    def collect_footnotes(self, node):
        # type: (nodes.Node) -> Dict[unicode, List[Union[collected_footnote, bool]]]
        def footnotes_under(n):
            # type: (nodes.Node) -> Iterator[nodes.Node]
            if isinstance(n, nodes.footnote):
                yield n
            else:
                for c in n.children:
                    if isinstance(c, addnodes.start_of_file):
                        continue
                    for k in footnotes_under(c):
                        yield k

        fnotes = {}  # type: Dict[unicode, List[Union[collected_footnote, bool]]]
        for fn in footnotes_under(node):
            num = fn.children[0].astext().strip()
            newnode = collected_footnote(*fn.children, number=num)
            fnotes[num] = [newnode, False]
        return fnotes

    def depart_start_of_file(self, node):
        # type: (nodes.Node) -> None
        self.curfilestack.pop()

    def visit_section(self, node):
        # type: (nodes.Node) -> None
        if not self.this_is_the_title:
            self.sectionlevel += 1
        self.body.append('\n\n')

    def depart_section(self, node):
        # type: (nodes.Node) -> None
        self.sectionlevel = max(self.sectionlevel - 1,
                                self.top_sectionlevel - 1)

    def visit_problematic(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'{\color{red}\bfseries{}')

    def depart_problematic(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}')

    def visit_topic(self, node):
        # type: (nodes.Node) -> None
        self.in_minipage = 1
        self.body.append('\n\\begin{sphinxShadowBox}\n')

    def depart_topic(self, node):
        # type: (nodes.Node) -> None
        self.in_minipage = 0
        self.body.append('\\end{sphinxShadowBox}\n')
    visit_sidebar = visit_topic
    depart_sidebar = depart_topic

    def visit_glossary(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_glossary(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_productionlist(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n\n\\begin{productionlist}\n')
        self.in_production_list = 1

    def depart_productionlist(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\end{productionlist}\n\n')
        self.in_production_list = 0

    def visit_production(self, node):
        # type: (nodes.Node) -> None
        if node['tokenname']:
            tn = node['tokenname']
            self.body.append(self.hypertarget('grammar-token-' + tn))
            self.body.append('\\production{%s}{' % self.encode(tn))
        else:
            self.body.append('\\productioncont{')

    def depart_production(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}\n')

    def visit_transition(self, node):
        # type: (nodes.Node) -> None
        self.body.append(self.elements['transition'])

    def depart_transition(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_title(self, node):
        # type: (nodes.Node) -> None
        parent = node.parent
        if isinstance(parent, addnodes.seealso):
            # the environment already handles this
            raise nodes.SkipNode
        elif isinstance(parent, nodes.section):
            if self.this_is_the_title:
                if len(node.children) != 1 and not isinstance(node.children[0],
                                                              nodes.Text):
                    logger.warning(__('document title is not a single Text node'),
                                   location=(self.curfilestack[-1], node.line))
                if not self.elements['title']:
                    # text needs to be escaped since it is inserted into
                    # the output literally
                    self.elements['title'] = node.astext().translate(tex_escape_map)
                self.this_is_the_title = 0
                raise nodes.SkipNode
            else:
                short = ''
                if node.traverse(nodes.image):
                    short = ('[%s]' %
                             u' '.join(clean_astext(node).split()).translate(tex_escape_map))

                try:
                    self.body.append(r'\%s%s{' % (self.sectionnames[self.sectionlevel], short))
                except IndexError:
                    # just use "subparagraph", it's not numbered anyway
                    self.body.append(r'\%s%s{' % (self.sectionnames[-1], short))
                self.context.append('}\n' + self.hypertarget_to(node.parent))
        elif isinstance(parent, nodes.topic):
            self.body.append(r'\sphinxstyletopictitle{')
            self.context.append('}\n')
        elif isinstance(parent, nodes.sidebar):
            self.body.append(r'\sphinxstylesidebartitle{')
            self.context.append('}\n')
        elif isinstance(parent, nodes.Admonition):
            self.body.append('{')
            self.context.append('}\n')
        elif isinstance(parent, nodes.table):
            # Redirect body output until title is finished.
            self.pushbody([])
        else:
            logger.warning(__('encountered title node not in section, topic, table, '
                              'admonition or sidebar'),
                           location=(self.curfilestack[-1], node.line or ''))
            self.body.append('\\sphinxstyleothertitle{')
            self.context.append('}\n')
        self.in_title = 1

    def depart_title(self, node):
        # type: (nodes.Node) -> None
        self.in_title = 0
        if isinstance(node.parent, nodes.table):
            self.table.caption = self.popbody()
        else:
            self.body.append(self.context.pop())

    def visit_subtitle(self, node):
        # type: (nodes.Node) -> None
        if isinstance(node.parent, nodes.sidebar):
            self.body.append('\\sphinxstylesidebarsubtitle{')
            self.context.append('}\n')
        else:
            self.context.append('')

    def depart_subtitle(self, node):
        # type: (nodes.Node) -> None
        self.body.append(self.context.pop())

    def visit_desc(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n\n\\begin{fulllineitems}\n')
        if self.table:
            self.table.has_problematic = True

    def depart_desc(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n\\end{fulllineitems}\n\n')

    def _visit_signature_line(self, node):
        # type: (nodes.Node) -> None
        for child in node:
            if isinstance(child, addnodes.desc_parameterlist):
                self.body.append(r'\pysiglinewithargsret{')
                break
        else:
            self.body.append(r'\pysigline{')

    def _depart_signature_line(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}')

    def visit_desc_signature(self, node):
        # type: (nodes.Node) -> None
        if node.parent['objtype'] != 'describe' and node['ids']:
            hyper = self.hypertarget(node['ids'][0])
        else:
            hyper = ''
        self.body.append(hyper)
        if not node.get('is_multiline'):
            self._visit_signature_line(node)
        else:
            self.body.append('%\n\\pysigstartmultiline\n')

    def depart_desc_signature(self, node):
        # type: (nodes.Node) -> None
        if not node.get('is_multiline'):
            self._depart_signature_line(node)
        else:
            self.body.append('%\n\\pysigstopmultiline')

    def visit_desc_signature_line(self, node):
        # type: (nodes.Node) -> None
        self._visit_signature_line(node)

    def depart_desc_signature_line(self, node):
        # type: (nodes.Node) -> None
        self._depart_signature_line(node)

    def visit_desc_addname(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'\sphinxcode{\sphinxupquote{')
        self.literal_whitespace += 1

    def depart_desc_addname(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}}')
        self.literal_whitespace -= 1

    def visit_desc_type(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_type(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_returns(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'{ $\rightarrow$ ')

    def depart_desc_returns(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'}')

    def visit_desc_name(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'\sphinxbfcode{\sphinxupquote{')
        self.no_contractions += 1
        self.literal_whitespace += 1

    def depart_desc_name(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}}')
        self.literal_whitespace -= 1
        self.no_contractions -= 1

    def visit_desc_parameterlist(self, node):
        # type: (nodes.Node) -> None
        # close name, open parameterlist
        self.body.append('}{')
        self.first_param = 1

    def depart_desc_parameterlist(self, node):
        # type: (nodes.Node) -> None
        # close parameterlist, open return annotation
        self.body.append('}{')

    def visit_desc_parameter(self, node):
        # type: (nodes.Node) -> None
        if not self.first_param:
            self.body.append(', ')
        else:
            self.first_param = 0
        if not node.hasattr('noemph'):
            self.body.append(r'\emph{')

    def depart_desc_parameter(self, node):
        # type: (nodes.Node) -> None
        if not node.hasattr('noemph'):
            self.body.append('}')

    def visit_desc_optional(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'\sphinxoptional{')

    def depart_desc_optional(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}')

    def visit_desc_annotation(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'\sphinxbfcode{\sphinxupquote{')

    def depart_desc_annotation(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}}')

    def visit_desc_content(self, node):
        # type: (nodes.Node) -> None
        if node.children and not isinstance(node.children[0], nodes.paragraph):
            # avoid empty desc environment which causes a formatting bug
            self.body.append('~')

    def depart_desc_content(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_seealso(self, node):
        # type: (nodes.Node) -> None
        self.body.append(u'\n\n\\sphinxstrong{%s:}\n\n' % admonitionlabels['seealso'])

    def depart_seealso(self, node):
        # type: (nodes.Node) -> None
        self.body.append("\n\n")

    def visit_rubric(self, node):
        # type: (nodes.Node) -> None
        if len(node.children) == 1 and node.children[0].astext() in \
           ('Footnotes', _('Footnotes')):
            raise nodes.SkipNode
        self.body.append('\\subsubsection*{')
        self.context.append('}\n')
        self.in_title = 1

    def depart_rubric(self, node):
        # type: (nodes.Node) -> None
        self.in_title = 0
        self.body.append(self.context.pop())

    def visit_footnote(self, node):
        # type: (nodes.Node) -> None
        self.in_footnote += 1
        if self.in_parsed_literal:
            self.body.append('\\begin{footnote}[%s]' % node[0].astext())
        else:
            self.body.append('%%\n\\begin{footnote}[%s]' % node[0].astext())
        self.body.append('\\sphinxAtStartFootnote\n')

    def depart_footnote(self, node):
        # type: (nodes.Node) -> None
        if self.in_parsed_literal:
            self.body.append('\\end{footnote}')
        else:
            self.body.append('%\n\\end{footnote}')
        self.in_footnote -= 1

    def visit_label(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_tabular_col_spec(self, node):
        # type: (nodes.Node) -> None
        self.next_table_colspec = node['spec']
        raise nodes.SkipNode

    def visit_table(self, node):
        # type: (nodes.Node) -> None
        if self.table:
            raise UnsupportedError(
                '%s:%s: nested tables are not yet implemented.' %
                (self.curfilestack[-1], node.line or ''))
        self.table = Table(node)
        if self.next_table_colspec:
            self.table.colspec = '{%s}\n' % self.next_table_colspec
            if 'colwidths-given' in node.get('classes', []):
                logger.info('both tabularcolumns and :widths: option are given. '
                            ':widths: is ignored.', location=node)
        self.next_table_colspec = None

    def depart_table(self, node):
        # type: (nodes.Node) -> None
        labels = self.hypertarget_to(node)
        table_type = self.table.get_table_type()
        table = self.render(table_type + '.tex_t',
                            dict(table=self.table, labels=labels))
        self.body.append("\n\n")
        self.body.append(table)
        self.body.append("\n")

        self.table = None

    def visit_colspec(self, node):
        # type: (nodes.Node) -> None
        self.table.colcount += 1
        if 'colwidth' in node:
            self.table.colwidths.append(node['colwidth'])
        if 'stub' in node:
            self.table.stubs.append(self.table.colcount - 1)

    def depart_colspec(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_tgroup(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_tgroup(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_thead(self, node):
        # type: (nodes.Node) -> None
        # Redirect head output until header is finished.
        self.pushbody(self.table.header)

    def depart_thead(self, node):
        # type: (nodes.Node) -> None
        self.popbody()

    def visit_tbody(self, node):
        # type: (nodes.Node) -> None
        # Redirect body output until table is finished.
        self.pushbody(self.table.body)

    def depart_tbody(self, node):
        # type: (nodes.Node) -> None
        self.popbody()

    def visit_row(self, node):
        # type: (nodes.Node) -> None
        self.table.col = 0

        # fill columns if the row starts with the bottom of multirow cell
        while True:
            cell = self.table.cell(self.table.row, self.table.col)
            if cell is None:  # not a bottom of multirow cell
                break
            else:  # a bottom of multirow cell
                self.table.col += cell.width
                if cell.col:
                    self.body.append('&')
                if cell.width == 1:
                    # insert suitable strut for equalizing row heights in given multirow
                    self.body.append('\\sphinxtablestrut{%d}' % cell.cell_id)
                else:  # use \multicolumn for wide multirow cell
                    self.body.append('\\multicolumn{%d}{|l|}'
                                     '{\\sphinxtablestrut{%d}}' %
                                     (cell.width, cell.cell_id))

    def depart_row(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\\\\n')
        cells = [self.table.cell(self.table.row, i) for i in range(self.table.colcount)]
        underlined = [cell.row + cell.height == self.table.row + 1 for cell in cells]
        if all(underlined):
            self.body.append('\\hline')
        else:
            i = 0
            underlined.extend([False])  # sentinel
            while i < len(underlined):
                if underlined[i] is True:
                    j = underlined[i:].index(False)
                    self.body.append('\\cline{%d-%d}' % (i + 1, i + j))
                    i += j
                i += 1
        self.table.row += 1

    def visit_entry(self, node):
        # type: (nodes.Node) -> None
        if self.table.col > 0:
            self.body.append('&')
        self.table.add_cell(node.get('morerows', 0) + 1, node.get('morecols', 0) + 1)
        cell = self.table.cell()
        context = ''
        if cell.width > 1:
            if self.builder.config.latex_use_latex_multicolumn:
                if self.table.col == 0:
                    self.body.append('\\multicolumn{%d}{|l|}{%%\n' % cell.width)
                else:
                    self.body.append('\\multicolumn{%d}{l|}{%%\n' % cell.width)
                context = '}%\n'
            else:
                self.body.append('\\sphinxstartmulticolumn{%d}%%\n' % cell.width)
                context = '\\sphinxstopmulticolumn\n'
        if cell.height > 1:
            # \sphinxmultirow 2nd arg "cell_id" will serve as id for LaTeX macros as well
            self.body.append('\\sphinxmultirow{%d}{%d}{%%\n' % (cell.height, cell.cell_id))
            context = '}%\n' + context
        if cell.width > 1 or cell.height > 1:
            self.body.append('\\begin{varwidth}[t]{\\sphinxcolwidth{%d}{%d}}\n'
                             % (cell.width, self.table.colcount))
            context = ('\\par\n\\vskip-\\baselineskip'
                       '\\vbox{\\hbox{\\strut}}\\end{varwidth}%\n') + context
            self.needs_linetrimming = 1
        if len(node.traverse(nodes.paragraph)) >= 2:
            self.table.has_oldproblematic = True
        if isinstance(node.parent.parent, nodes.thead) or (cell.col in self.table.stubs):
            if len(node) == 1 and isinstance(node[0], nodes.paragraph) and node.astext() == '':
                pass
            else:
                self.body.append('\\sphinxstyletheadfamily ')
        if self.needs_linetrimming:
            self.pushbody([])
        self.context.append(context)

    def depart_entry(self, node):
        # type: (nodes.Node) -> None
        if self.needs_linetrimming:
            self.needs_linetrimming = 0
            body = self.popbody()

            # Remove empty lines from top of merged cell
            while body and body[0] == "\n":
                body.pop(0)
            self.body.extend(body)

        self.body.append(self.context.pop())

        cell = self.table.cell()
        self.table.col += cell.width

        # fill columns if next ones are a bottom of wide-multirow cell
        while True:
            nextcell = self.table.cell()
            if nextcell is None:  # not a bottom of multirow cell
                break
            else:  # a bottom part of multirow cell
                self.table.col += nextcell.width
                self.body.append('&')
                if nextcell.width == 1:
                    # insert suitable strut for equalizing row heights in multirow
                    # they also serve to clear colour panels which would hide the text
                    self.body.append('\\sphinxtablestrut{%d}' % nextcell.cell_id)
                else:
                    # use \multicolumn for wide multirow cell
                    self.body.append('\\multicolumn{%d}{l|}'
                                     '{\\sphinxtablestrut{%d}}' %
                                     (nextcell.width, nextcell.cell_id))

    def visit_acks(self, node):
        # type: (nodes.Node) -> None
        # this is a list in the source, but should be rendered as a
        # comma-separated list here
        self.body.append('\n\n')
        self.body.append(', '.join(n.astext()
                                   for n in node.children[0].children) + '.')
        self.body.append('\n\n')
        raise nodes.SkipNode

    def visit_bullet_list(self, node):
        # type: (nodes.Node) -> None
        if not self.compact_list:
            self.body.append('\\begin{itemize}\n')
        if self.table:
            self.table.has_problematic = True

    def depart_bullet_list(self, node):
        # type: (nodes.Node) -> None
        if not self.compact_list:
            self.body.append('\\end{itemize}\n')

    def visit_enumerated_list(self, node):
        # type: (nodes.Node) -> None
        def get_enumtype(node):
            # type: (nodes.Node) -> unicode
            enumtype = node.get('enumtype', 'arabic')
            if 'alpha' in enumtype and 26 < node.get('start', 0) + len(node):
                # fallback to arabic if alphabet counter overflows
                enumtype = 'arabic'

            return enumtype

        def get_nested_level(node):
            # type: (nodes.Node) -> int
            if node is None:
                return 0
            elif isinstance(node, nodes.enumerated_list):
                return get_nested_level(node.parent) + 1
            else:
                return get_nested_level(node.parent)

        enum = "enum%s" % toRoman(get_nested_level(node)).lower()
        enumnext = "enum%s" % toRoman(get_nested_level(node) + 1).lower()
        style = ENUMERATE_LIST_STYLE.get(get_enumtype(node))
        prefix = node.get('prefix', '')
        suffix = node.get('suffix', '.')

        self.body.append('\\begin{enumerate}\n')
        self.body.append('\\def\\the%s{%s{%s}}\n' % (enum, style, enum))
        self.body.append('\\def\\label%s{%s\\the%s %s}\n' %
                         (enum, prefix, enum, suffix))
        self.body.append('\\makeatletter\\def\\p@%s{\\p@%s %s\\the%s %s}\\makeatother\n' %
                         (enumnext, enum, prefix, enum, suffix))
        if 'start' in node:
            self.body.append('\\setcounter{%s}{%d}\n' % (enum, node['start'] - 1))
        if self.table:
            self.table.has_problematic = True

    def depart_enumerated_list(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\end{enumerate}\n')

    def visit_list_item(self, node):
        # type: (nodes.Node) -> None
        # Append "{}" in case the next character is "[", which would break
        # LaTeX's list environment (no numbering and the "[" is not printed).
        self.body.append(r'\item {} ')

    def depart_list_item(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n')

    def visit_definition_list(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\begin{description}\n')
        if self.table:
            self.table.has_problematic = True

    def depart_definition_list(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\end{description}\n')

    def visit_definition_list_item(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_definition_list_item(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_term(self, node):
        # type: (nodes.Node) -> None
        self.in_term += 1
        ctx = ''  # type: unicode
        if node.get('ids'):
            ctx = '\\phantomsection'
            for node_id in node['ids']:
                ctx += self.hypertarget(node_id, anchor=False)
        ctx += '}] \\leavevmode'
        self.body.append('\\item[{')
        self.context.append(ctx)

    def depart_term(self, node):
        # type: (nodes.Node) -> None
        self.body.append(self.context.pop())
        self.in_term -= 1

    def visit_classifier(self, node):
        # type: (nodes.Node) -> None
        self.body.append('{[}')

    def depart_classifier(self, node):
        # type: (nodes.Node) -> None
        self.body.append('{]}')

    def visit_definition(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_definition(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n')

    def visit_field_list(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\begin{quote}\\begin{description}\n')
        if self.table:
            self.table.has_problematic = True

    def depart_field_list(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\end{description}\\end{quote}\n')

    def visit_field(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_field(self, node):
        # type: (nodes.Node) -> None
        pass

    visit_field_name = visit_term
    depart_field_name = depart_term

    visit_field_body = visit_definition
    depart_field_body = depart_definition

    def visit_paragraph(self, node):
        # type: (nodes.Node) -> None
        index = node.parent.index(node)
        if (index > 0 and isinstance(node.parent, nodes.compound) and
                not isinstance(node.parent[index - 1], nodes.paragraph) and
                not isinstance(node.parent[index - 1], nodes.compound)):
            # insert blank line, if the paragraph follows a non-paragraph node in a compound
            self.body.append('\\noindent\n')
        elif index == 1 and isinstance(node.parent, (nodes.footnote, footnotetext)):
            # don't insert blank line, if the paragraph is second child of a footnote
            # (first one is label node)
            pass
        else:
            self.body.append('\n')

    def depart_paragraph(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n')

    def visit_centered(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n\\begin{center}')
        if self.table:
            self.table.has_problematic = True

    def depart_centered(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n\\end{center}')

    def visit_hlist(self, node):
        # type: (nodes.Node) -> None
        # for now, we don't support a more compact list format
        # don't add individual itemize environments, but one for all columns
        self.compact_list += 1
        self.body.append('\\begin{itemize}\\setlength{\\itemsep}{0pt}'
                         '\\setlength{\\parskip}{0pt}\n')
        if self.table:
            self.table.has_problematic = True

    def depart_hlist(self, node):
        # type: (nodes.Node) -> None
        self.compact_list -= 1
        self.body.append('\\end{itemize}\n')

    def visit_hlistcol(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_hlistcol(self, node):
        # type: (nodes.Node) -> None
        pass

    def latex_image_length(self, width_str, scale = 100):
        # type: (nodes.Node, int) -> unicode
        try:
            return rstdim_to_latexdim(width_str, scale)
        except ValueError:
            logger.warning(__('dimension unit %s is invalid. Ignored.'), width_str)
            return None

    def is_inline(self, node):
        # type: (nodes.Node) -> bool
        """Check whether a node represents an inline element."""
        return isinstance(node.parent, nodes.TextElement)

    def visit_image(self, node):
        # type: (nodes.Node) -> None
        attrs = node.attributes
        pre = []    # type: List[unicode]
                    # in reverse order
        post = []   # type: List[unicode]
        include_graphics_options = []
        has_hyperlink = isinstance(node.parent, nodes.reference)
        if has_hyperlink:
            is_inline = self.is_inline(node.parent)
        else:
            is_inline = self.is_inline(node)
        if 'width' in attrs:
            if 'scale' in attrs:
                w = self.latex_image_length(attrs['width'], attrs['scale'])
            else:
                w = self.latex_image_length(attrs['width'])
            if w:
                include_graphics_options.append('width=%s' % w)
        if 'height' in attrs:
            if 'scale' in attrs:
                h = self.latex_image_length(attrs['height'], attrs['scale'])
            else:
                h = self.latex_image_length(attrs['height'])
            if h:
                include_graphics_options.append('height=%s' % h)
        if 'scale' in attrs:
            if not include_graphics_options:
                # if no "width" nor "height", \sphinxincludegraphics will fit
                # to the available text width if oversized after rescaling.
                include_graphics_options.append('scale=%s'
                                                % (float(attrs['scale']) / 100.0))
        if 'align' in attrs:
            align_prepost = {
                # By default latex aligns the top of an image.
                (1, 'top'): ('', ''),
                (1, 'middle'): ('\\raisebox{-0.5\\height}{', '}'),
                (1, 'bottom'): ('\\raisebox{-\\height}{', '}'),
                (0, 'center'): ('{\\hspace*{\\fill}', '\\hspace*{\\fill}}'),
                # These 2 don't exactly do the right thing.  The image should
                # be floated alongside the paragraph.  See
                # https://www.w3.org/TR/html4/struct/objects.html#adef-align-IMG
                (0, 'left'): ('{', '\\hspace*{\\fill}}'),
                (0, 'right'): ('{\\hspace*{\\fill}', '}'),
            }
            try:
                pre.append(align_prepost[is_inline, attrs['align']][0])
                post.append(align_prepost[is_inline, attrs['align']][1])
            except KeyError:
                pass
        if self.in_parsed_literal:
            pre.append('{\\sphinxunactivateextrasandspace ')
            post.append('}')
        if not is_inline and not has_hyperlink:
            pre.append('\n\\noindent')
            post.append('\n')
        pre.reverse()
        if node['uri'] in self.builder.images:
            uri = self.builder.images[node['uri']]
        else:
            # missing image!
            if self.ignore_missing_images:
                return
            uri = node['uri']
        if uri.find('://') != -1:
            # ignore remote images
            return
        self.body.extend(pre)
        options = ''
        if include_graphics_options:
            options = '[%s]' % ','.join(include_graphics_options)
        base, ext = path.splitext(uri)
        if self.in_title and base:
            # Lowercase tokens forcely because some fncychap themes capitalize
            # the options of \sphinxincludegraphics unexpectly (ex. WIDTH=...).
            self.body.append('\\lowercase{\\sphinxincludegraphics%s}{{%s}%s}' %
                             (options, base, ext))
        else:
            self.body.append('\\sphinxincludegraphics%s{{%s}%s}' %
                             (options, base, ext))
        self.body.extend(post)

    def depart_image(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_figure(self, node):
        # type: (nodes.Node) -> None
        if self.table:
            # TODO: support align option
            if 'width' in node:
                length = self.latex_image_length(node['width'])
                if length:
                    self.body.append('\\begin{sphinxfigure-in-table}[%s]\n'
                                     '\\centering\n' % length)
            else:
                self.body.append('\\begin{sphinxfigure-in-table}\n\\centering\n')
            if any(isinstance(child, nodes.caption) for child in node):
                self.body.append('\\capstart')
            self.context.append('\\end{sphinxfigure-in-table}\\relax\n')
        elif node.get('align', '') in ('left', 'right'):
            length = None
            if 'width' in node:
                length = self.latex_image_length(node['width'])
            elif 'width' in node[0]:
                length = self.latex_image_length(node[0]['width'])
            self.body.append('\\begin{wrapfigure}{%s}{%s}\n\\centering' %
                             (node['align'] == 'right' and 'r' or 'l', length or '0pt'))
            self.context.append('\\end{wrapfigure}\n')
        elif self.in_minipage:
            self.body.append('\n\\begin{center}')
            self.context.append('\\end{center}\n')
        else:
            self.body.append('\n\\begin{figure}[%s]\n\\centering\n' %
                             self.elements['figure_align'])
            if any(isinstance(child, nodes.caption) for child in node):
                self.body.append('\\capstart\n')
            self.context.append('\\end{figure}\n')

    def depart_figure(self, node):
        # type: (nodes.Node) -> None
        self.body.append(self.context.pop())

    def visit_caption(self, node):
        # type: (nodes.Node) -> None
        self.in_caption += 1
        if isinstance(node.parent, captioned_literal_block):
            self.body.append('\\sphinxSetupCaptionForVerbatim{')
        elif self.in_minipage and isinstance(node.parent, nodes.figure):
            self.body.append('\\captionof{figure}{')
        elif self.table and node.parent.tagname == 'figure':
            self.body.append('\\sphinxfigcaption{')
        else:
            self.body.append('\\caption{')

    def depart_caption(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}')
        if isinstance(node.parent, nodes.figure):
            labels = self.hypertarget_to(node.parent)
            self.body.append(labels)
        self.in_caption -= 1

    def visit_legend(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n\\begin{sphinxlegend}')

    def depart_legend(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\end{sphinxlegend}\n')

    def visit_admonition(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n\\begin{sphinxadmonition}{note}')

    def depart_admonition(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\end{sphinxadmonition}\n')

    def _make_visit_admonition(name):
        # type: (unicode) -> Callable[[LaTeXTranslator, nodes.Node], None]
        def visit_admonition(self, node):
            # type: (nodes.Node) -> None
            self.body.append(u'\n\\begin{sphinxadmonition}{%s}{%s:}' %
                             (name, admonitionlabels[name]))
        return visit_admonition

    def _depart_named_admonition(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\end{sphinxadmonition}\n')

    visit_attention = _make_visit_admonition('attention')
    depart_attention = _depart_named_admonition
    visit_caution = _make_visit_admonition('caution')
    depart_caution = _depart_named_admonition
    visit_danger = _make_visit_admonition('danger')
    depart_danger = _depart_named_admonition
    visit_error = _make_visit_admonition('error')
    depart_error = _depart_named_admonition
    visit_hint = _make_visit_admonition('hint')
    depart_hint = _depart_named_admonition
    visit_important = _make_visit_admonition('important')
    depart_important = _depart_named_admonition
    visit_note = _make_visit_admonition('note')
    depart_note = _depart_named_admonition
    visit_tip = _make_visit_admonition('tip')
    depart_tip = _depart_named_admonition
    visit_warning = _make_visit_admonition('warning')
    depart_warning = _depart_named_admonition

    def visit_versionmodified(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_versionmodified(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_target(self, node):
        # type: (nodes.Node) -> None
        def add_target(id):
            # type: (unicode) -> None
            # indexing uses standard LaTeX index markup, so the targets
            # will be generated differently
            if id.startswith('index-'):
                return

            # equations also need no extra blank line nor hypertarget
            # TODO: fix this dependency on mathbase extension internals
            if id.startswith('equation-'):
                return

            # insert blank line, if the target follows a paragraph node
            index = node.parent.index(node)
            if index > 0 and isinstance(node.parent[index - 1], nodes.paragraph):
                self.body.append('\n')

            # do not generate \phantomsection in \section{}
            anchor = not self.in_title
            self.body.append(self.hypertarget(id, anchor=anchor))

        # skip if visitor for next node supports hyperlink
        next_node = node
        while isinstance(next_node, nodes.target):
            next_node = next_node.next_node(ascend=True)

        domain = self.builder.env.get_domain('std')
        if isinstance(next_node, HYPERLINK_SUPPORT_NODES):
            return
        elif domain.get_enumerable_node_type(next_node) and domain.get_numfig_title(next_node):
            return

        if 'refuri' in node:
            return
        if node.get('refid'):
            prev_node = get_prev_node(node)
            if isinstance(prev_node, nodes.reference) and node['refid'] == prev_node['refid']:
                # a target for a hyperlink reference having alias
                pass
            else:
                add_target(node['refid'])
        for id in node['ids']:
            add_target(id)

    def depart_target(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_attribution(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n\\begin{flushright}\n')
        self.body.append('---')

    def depart_attribution(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n\\end{flushright}\n')

    def visit_index(self, node, scre = None):
        # type: (nodes.Node, None) -> None
        def escape(value):
            value = self.encode(value)
            value = value.replace(r'\{', r'\sphinxleftcurlybrace{}')
            value = value.replace(r'\}', r'\sphinxrightcurlybrace{}')
            value = value.replace('"', '""')
            value = value.replace('@', '"@')
            value = value.replace('!', '"!')
            return value

        def style(string):
            match = EXTRA_RE.match(string)
            if match:
                return match.expand(r'\\spxentry{\1}\\spxextra{\2}')
            else:
                return '\\spxentry{%s}' % string

        if scre:
            warnings.warn(('LaTeXTranslator.visit_index() optional argument '
                           '"scre" is deprecated. It is ignored.'),
                          RemovedInSphinx30Warning, stacklevel=2)
        if not node.get('inline', True):
            self.body.append('\n')
        entries = node['entries']
        for type, string, tid, ismain, key_ in entries:
            m = ''
            if ismain:
                m = '|spxpagem'
            try:
                if type == 'single':
                    try:
                        p1, p2 = [escape(x) for x in split_into(2, 'single', string)]
                        P1, P2 = style(p1), style(p2)
                        self.body.append(r'\index{%s@%s!%s@%s%s}' % (p1, P1, p2, P2, m))
                    except ValueError:
                        p = escape(split_into(1, 'single', string)[0])
                        P = style(p)
                        self.body.append(r'\index{%s@%s%s}' % (p, P, m))
                elif type == 'pair':
                    p1, p2 = [escape(x) for x in split_into(2, 'pair', string)]
                    P1, P2 = style(p1), style(p2)
                    self.body.append(r'\index{%s@%s!%s@%s%s}\index{%s@%s!%s@%s%s}' %
                                     (p1, P1, p2, P2, m, p2, P2, p1, P1, m))
                elif type == 'triple':
                    p1, p2, p3 = [escape(x) for x in split_into(3, 'triple', string)]
                    P1, P2, P3 = style(p1), style(p2), style(p3)
                    self.body.append(
                        r'\index{%s@%s!%s %s@%s %s%s}'
                        r'\index{%s@%s!%s, %s@%s, %s%s}'
                        r'\index{%s@%s!%s %s@%s %s%s}' %
                        (p1, P1, p2, p3, P2, P3, m,
                         p2, P2, p3, p1, P3, P1, m,
                         p3, P3, p1, p2, P1, P2, m))
                elif type == 'see':
                    p1, p2 = [escape(x) for x in split_into(2, 'see', string)]
                    P1 = style(p1)
                    self.body.append(r'\index{%s@%s|see{%s}}' % (p1, P1, p2))
                elif type == 'seealso':
                    p1, p2 = [escape(x) for x in split_into(2, 'seealso', string)]
                    P1 = style(p1)
                    self.body.append(r'\index{%s@%s|see{%s}}' % (p1, P1, p2))
                else:
                    logger.warning(__('unknown index entry type %s found'), type)
            except ValueError as err:
                logger.warning(str(err))
        if not node.get('inline', True):
            self.body.append('\\ignorespaces ')
        raise nodes.SkipNode

    def visit_raw(self, node):
        # type: (nodes.Node) -> None
        if not self.is_inline(node):
            self.body.append('\n')
        if 'latex' in node.get('format', '').split():
            self.body.append(node.astext())
        if not self.is_inline(node):
            self.body.append('\n')
        raise nodes.SkipNode

    def visit_reference(self, node):
        # type: (nodes.Node) -> None
        if not self.in_title:
            for id in node.get('ids'):
                anchor = not self.in_caption
                self.body += self.hypertarget(id, anchor=anchor)
        if not self.is_inline(node):
            self.body.append('\n')
        uri = node.get('refuri', '')
        if not uri and node.get('refid'):
            uri = '%' + self.curfilestack[-1] + '#' + node['refid']
        if self.in_title or not uri:
            self.context.append('')
        elif uri.startswith('#'):
            # references to labels in the same document
            id = self.curfilestack[-1] + ':' + uri[1:]
            self.body.append(self.hyperlink(id))
            self.body.append(r'\emph{')
            if self.builder.config.latex_show_pagerefs and not \
                    self.in_production_list:
                self.context.append('}}} (%s)' % self.hyperpageref(id))
            else:
                self.context.append('}}}')
        elif uri.startswith('%'):
            # references to documents or labels inside documents
            hashindex = uri.find('#')
            if hashindex == -1:
                # reference to the document
                id = uri[1:] + '::doc'
            else:
                # reference to a label
                id = uri[1:].replace('#', ':')
            self.body.append(self.hyperlink(id))
            if len(node) and hasattr(node[0], 'attributes') and \
               'std-term' in node[0].get('classes', []):
                # don't add a pageref for glossary terms
                self.context.append('}}}')
                # mark up as termreference
                self.body.append(r'\sphinxtermref{')
            else:
                self.body.append(r'\sphinxcrossref{')
                if self.builder.config.latex_show_pagerefs and not \
                   self.in_production_list:
                    self.context.append('}}} (%s)' % self.hyperpageref(id))
                else:
                    self.context.append('}}}')
        else:
            if len(node) == 1 and uri == node[0]:
                if node.get('nolinkurl'):
                    self.body.append('\\sphinxnolinkurl{%s}' % self.encode_uri(uri))
                else:
                    self.body.append('\\sphinxurl{%s}' % self.encode_uri(uri))
                raise nodes.SkipNode
            else:
                self.body.append('\\sphinxhref{%s}{' % self.encode_uri(uri))
                self.context.append('}')

    def depart_reference(self, node):
        # type: (nodes.Node) -> None
        self.body.append(self.context.pop())
        if not self.is_inline(node):
            self.body.append('\n')

    def visit_number_reference(self, node):
        # type: (nodes.Node) -> None
        if node.get('refid'):
            id = self.curfilestack[-1] + ':' + node['refid']
        else:
            id = node.get('refuri', '')[1:].replace('#', ':')

        title = node.get('title', '%s')
        title = text_type(title).translate(tex_escape_map).replace('\\%s', '%s')
        if '\\{name\\}' in title or '\\{number\\}' in title:
            # new style format (cf. "Fig.%{number}")
            title = title.replace('\\{name\\}', '{name}').replace('\\{number\\}', '{number}')
            text = escape_abbr(title).format(name='\\nameref{%s}' % self.idescape(id),
                                             number='\\ref{%s}' % self.idescape(id))
        else:
            # old style format (cf. "Fig.%{number}")
            text = escape_abbr(title) % ('\\ref{%s}' % self.idescape(id))
        hyperref = '\\hyperref[%s]{%s}' % (self.idescape(id), text)
        self.body.append(hyperref)

        raise nodes.SkipNode

    def visit_download_reference(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_download_reference(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_pending_xref(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_pending_xref(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_emphasis(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'\sphinxstyleemphasis{')

    def depart_emphasis(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}')

    def visit_literal_emphasis(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'\sphinxstyleliteralemphasis{\sphinxupquote{')
        self.no_contractions += 1

    def depart_literal_emphasis(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}}')
        self.no_contractions -= 1

    def visit_strong(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'\sphinxstylestrong{')

    def depart_strong(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}')

    def visit_literal_strong(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'\sphinxstyleliteralstrong{\sphinxupquote{')
        self.no_contractions += 1

    def depart_literal_strong(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}}')
        self.no_contractions -= 1

    def visit_abbreviation(self, node):
        # type: (nodes.Node) -> None
        abbr = node.astext()
        self.body.append(r'\sphinxstyleabbreviation{')
        # spell out the explanation once
        if node.hasattr('explanation') and abbr not in self.handled_abbrs:
            self.context.append('} (%s)' % self.encode(node['explanation']))
            self.handled_abbrs.add(abbr)
        else:
            self.context.append('}')

    def depart_abbreviation(self, node):
        # type: (nodes.Node) -> None
        self.body.append(self.context.pop())

    def visit_manpage(self, node):
        # type: (nodes.Node) -> Any
        return self.visit_literal_emphasis(node)

    def depart_manpage(self, node):
        # type: (nodes.Node) -> Any
        return self.depart_literal_emphasis(node)

    def visit_title_reference(self, node):
        # type: (nodes.Node) -> None
        self.body.append(r'\sphinxtitleref{')

    def depart_title_reference(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}')

    def visit_thebibliography(self, node):
        # type: (nodes.Node) -> None
        longest_label = max((subnode[0].astext() for subnode in node), key=len)
        if len(longest_label) > MAX_CITATION_LABEL_LENGTH:
            # adjust max width of citation labels not to break the layout
            longest_label = longest_label[:MAX_CITATION_LABEL_LENGTH]

        self.body.append(u'\n\\begin{sphinxthebibliography}{%s}\n' %
                         self.encode(longest_label))

    def depart_thebibliography(self, node):
        # type: (nodes.Node) -> None
        self.body.append(u'\\end{sphinxthebibliography}\n')

    def visit_citation(self, node):
        # type: (nodes.Node) -> None
        label = node[0].astext()
        self.body.append(u'\\bibitem[%s]{%s:%s}' %
                         (self.encode(label), node['docname'], node['ids'][0]))

    def depart_citation(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_citation_reference(self, node):
        # type: (nodes.Node) -> None
        if self.in_title:
            pass
        else:
            self.body.append('\\sphinxcite{%s:%s}' % (node['docname'], node['refname']))
            raise nodes.SkipNode

    def depart_citation_reference(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_literal(self, node):
        # type: (nodes.Node) -> None
        self.no_contractions += 1
        if self.in_title:
            self.body.append(r'\sphinxstyleliteralintitle{\sphinxupquote{')
        else:
            self.body.append(r'\sphinxcode{\sphinxupquote{')

    def depart_literal(self, node):
        # type: (nodes.Node) -> None
        self.no_contractions -= 1
        self.body.append('}}')

    def visit_footnote_reference(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_footnotemark(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\sphinxfootnotemark[')

    def depart_footnotemark(self, node):
        # type: (nodes.Node) -> None
        self.body.append(']')

    def visit_footnotetext(self, node):
        # type: (nodes.Node) -> None
        number = node[0].astext()
        self.body.append('%%\n\\begin{footnotetext}[%s]'
                         '\\sphinxAtStartFootnote\n' % number)

    def depart_footnotetext(self, node):
        # type: (nodes.Node) -> None
        # the \ignorespaces in particular for after table header use
        self.body.append('%\n\\end{footnotetext}\\ignorespaces ')

    def visit_captioned_literal_block(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_captioned_literal_block(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_literal_block(self, node):
        # type: (nodes.Node) -> None
        if node.rawsource != node.astext():
            # most probably a parsed-literal block -- don't highlight
            self.in_parsed_literal += 1
            self.body.append('\\begin{sphinxalltt}\n')
        else:
            labels = self.hypertarget_to(node)
            if isinstance(node.parent, captioned_literal_block):
                labels += self.hypertarget_to(node.parent)
            if labels and not self.in_footnote:
                self.body.append('\n\\def\\sphinxLiteralBlockLabel{' + labels + '}')

            lang = node.get('language', 'default')
            linenos = node.get('linenos', False)
            highlight_args = node.get('highlight_args', {})
            highlight_args['force'] = node.get('force_highlighting', False)
            if lang is self.builder.config.highlight_language:
                # only pass highlighter options for original language
                opts = self.builder.config.highlight_options
            else:
                opts = {}

            hlcode = self.highlighter.highlight_block(
                node.rawsource, lang, opts=opts, linenos=linenos,
                location=(self.curfilestack[-1], node.line), **highlight_args
            )
            # workaround for Unicode issue
            hlcode = hlcode.replace(u'€', u'@texteuro[]')
            if self.in_footnote:
                self.body.append('\n\\sphinxSetupCodeBlockInFootnote')
                hlcode = hlcode.replace('\\begin{Verbatim}',
                                        '\\begin{sphinxVerbatim}')
            # if in table raise verbatim flag to avoid "tabulary" environment
            # and opt for sphinxVerbatimintable to handle caption & long lines
            elif self.table:
                self.table.has_problematic = True
                self.table.has_verbatim = True
                hlcode = hlcode.replace('\\begin{Verbatim}',
                                        '\\begin{sphinxVerbatimintable}')
            else:
                hlcode = hlcode.replace('\\begin{Verbatim}',
                                        '\\begin{sphinxVerbatim}')
            # get consistent trailer
            hlcode = hlcode.rstrip()[:-14]  # strip \end{Verbatim}
            if self.table and not self.in_footnote:
                hlcode += '\\end{sphinxVerbatimintable}'
            else:
                hlcode += '\\end{sphinxVerbatim}'

            hllines = str(highlight_args.get('hl_lines', []))[1:-1]
            if hllines:
                self.body.append('\n\\fvset{hllines={, %s,}}%%' % hllines)
            self.body.append('\n' + hlcode + '\n')
            if hllines:
                self.body.append('\\sphinxresetverbatimhllines\n')
            raise nodes.SkipNode

    def depart_literal_block(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n\\end{sphinxalltt}\n')
        self.in_parsed_literal -= 1
    visit_doctest_block = visit_literal_block
    depart_doctest_block = depart_literal_block

    def visit_line(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\item[] ')

    def depart_line(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n')

    def visit_line_block(self, node):
        # type: (nodes.Node) -> None
        if isinstance(node.parent, nodes.line_block):
            self.body.append('\\item[]\n'
                             '\\begin{DUlineblock}{\\DUlineblockindent}\n')
        else:
            self.body.append('\n\\begin{DUlineblock}{0em}\n')
        if self.table:
            self.table.has_problematic = True

    def depart_line_block(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\end{DUlineblock}\n')

    def visit_block_quote(self, node):
        # type: (nodes.Node) -> None
        # If the block quote contains a single object and that object
        # is a list, then generate a list not a block quote.
        # This lets us indent lists.
        done = 0
        if len(node.children) == 1:
            child = node.children[0]
            if isinstance(child, nodes.bullet_list) or \
                    isinstance(child, nodes.enumerated_list):
                done = 1
        if not done:
            self.body.append('\\begin{quote}\n')
            if self.table:
                self.table.has_problematic = True

    def depart_block_quote(self, node):
        # type: (nodes.Node) -> None
        done = 0
        if len(node.children) == 1:
            child = node.children[0]
            if isinstance(child, nodes.bullet_list) or \
                    isinstance(child, nodes.enumerated_list):
                done = 1
        if not done:
            self.body.append('\\end{quote}\n')

    # option node handling copied from docutils' latex writer

    def visit_option(self, node):
        # type: (nodes.Node) -> None
        if self.context[-1]:
            # this is not the first option
            self.body.append(', ')

    def depart_option(self, node):
        # type: (nodes.Node) -> None
        # flag that the first option is done.
        self.context[-1] += 1

    def visit_option_argument(self, node):
        # type: (nodes.Node) -> None
        """The delimiter betweeen an option and its argument."""
        self.body.append(node.get('delimiter', ' '))

    def depart_option_argument(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_option_group(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\item [')
        # flag for first option
        self.context.append(0)

    def depart_option_group(self, node):
        # type: (nodes.Node) -> None
        self.context.pop()  # the flag
        self.body.append('] ')

    def visit_option_list(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\begin{optionlist}{3cm}\n')
        if self.table:
            self.table.has_problematic = True

    def depart_option_list(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\\end{optionlist}\n')

    def visit_option_list_item(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_option_list_item(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_option_string(self, node):
        # type: (nodes.Node) -> None
        ostring = node.astext()
        self.no_contractions += 1
        self.body.append(self.encode(ostring))
        self.no_contractions -= 1
        raise nodes.SkipNode

    def visit_description(self, node):
        # type: (nodes.Node) -> None
        self.body.append(' ')

    def depart_description(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_superscript(self, node):
        # type: (nodes.Node) -> None
        self.body.append('$^{\\text{')

    def depart_superscript(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}}$')

    def visit_subscript(self, node):
        # type: (nodes.Node) -> None
        self.body.append('$_{\\text{')

    def depart_subscript(self, node):
        # type: (nodes.Node) -> None
        self.body.append('}}$')

    def visit_inline(self, node):
        # type: (nodes.Node) -> None
        classes = node.get('classes', [])
        if classes in [['menuselection']]:
            self.body.append(r'\sphinxmenuselection{')
            self.context.append('}')
        elif classes in [['guilabel']]:
            self.body.append(r'\sphinxguilabel{')
            self.context.append('}')
        elif classes in [['accelerator']]:
            self.body.append(r'\sphinxaccelerator{')
            self.context.append('}')
        elif classes and not self.in_title:
            self.body.append(r'\DUrole{%s}{' % ','.join(classes))
            self.context.append('}')
        else:
            self.context.append('')

    def depart_inline(self, node):
        # type: (nodes.Node) -> None
        self.body.append(self.context.pop())

    def visit_generated(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_generated(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_compound(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_compound(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_container(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_container(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_decoration(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_decoration(self, node):
        # type: (nodes.Node) -> None
        pass

    # docutils-generated elements that we don't support

    def visit_header(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_footer(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_docinfo(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    # text handling

    def encode(self, text):
        # type: (unicode) -> unicode
        text = text_type(text).translate(tex_escape_map)
        if self.literal_whitespace:
            # Insert a blank before the newline, to avoid
            # ! LaTeX Error: There's no line here to end.
            text = text.replace(u'\n', u'~\\\\\n').replace(u' ', u'~')
        if self.no_contractions:
            text = text.replace('--', u'-{-}')
            text = text.replace("''", u"'{'}")
        return text

    def encode_uri(self, text):
        # type: (unicode) -> unicode
        # in \href, the tilde is allowed and must be represented literally
        return self.encode(text).replace('\\textasciitilde{}', '~')

    def visit_Text(self, node):
        # type: (nodes.Node) -> None
        text = self.encode(node.astext())
        self.body.append(text)

    def depart_Text(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_comment(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_meta(self, node):
        # type: (nodes.Node) -> None
        # only valid for HTML
        raise nodes.SkipNode

    def visit_system_message(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_system_message(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n')

    def visit_math(self, node):
        # type: (nodes.Node) -> None
        if self.in_title:
            self.body.append(r'\protect\(%s\protect\)' % node.astext())
        else:
            self.body.append(r'\(%s\)' % node.astext())
        raise nodes.SkipNode

    def visit_math_block(self, node):
        # type: (nodes.Node) -> None
        if node.get('label'):
            label = "equation:%s:%s" % (node['docname'], node['label'])
        else:
            label = None

        if node.get('nowrap'):
            if label:
                self.body.append(r'\label{%s}' % label)
            self.body.append(node.astext())
        else:
            from sphinx.util.math import wrap_displaymath
            self.body.append(wrap_displaymath(node.astext(), label,
                                              self.builder.config.math_number_all))
        raise nodes.SkipNode

    def visit_math_reference(self, node):
        # type: (nodes.Node) -> None
        label = "equation:%s:%s" % (node['docname'], node['target'])
        eqref_format = self.builder.config.math_eqref_format
        if eqref_format:
            try:
                ref = r'\ref{%s}' % label
                self.body.append(eqref_format.format(number=ref))
            except KeyError as exc:
                logger.warning(__('Invalid math_eqref_format: %r'), exc,
                               location=node)
                self.body.append(r'\eqref{%s}' % label)
        else:
            self.body.append(r'\eqref{%s}' % label)

    def depart_math_reference(self, node):
        # type: (nodes.Node) -> None
        pass

    def unknown_visit(self, node):
        # type: (nodes.Node) -> None
        raise NotImplementedError('Unknown node: ' + node.__class__.__name__)

    # --------- METHODS FOR COMPATIBILITY --------------------------------------

    @property
    def footnotestack(self):
        # type: () -> List[Dict[unicode, List[Union[collected_footnote, bool]]]]
        warnings.warn('LaTeXWriter.footnotestack is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return []

    @property
    def bibitems(self):
        # type: () -> List[List[unicode]]
        warnings.warn('LaTeXTranslator.bibitems() is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return []

    @property
    def in_container_literal_block(self):
        # type: () -> int
        warnings.warn('LaTeXTranslator.in_container_literal_block is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return 0

    @property
    def next_section_ids(self):
        # type: () -> Set[unicode]
        warnings.warn('LaTeXTranslator.next_section_ids is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return set()

    @property
    def next_hyperlink_ids(self):
        # type: () -> Dict
        warnings.warn('LaTeXTranslator.next_hyperlink_ids is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return {}

    def push_hyperlink_ids(self, figtype, ids):
        # type: (unicode, Set[unicode]) -> None
        warnings.warn('LaTeXTranslator.push_hyperlink_ids() is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        pass

    def pop_hyperlink_ids(self, figtype):
        # type: (unicode) -> Set[unicode]
        warnings.warn('LaTeXTranslator.pop_hyperlink_ids() is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return set()

    @property
    def hlsettingstack(self):
        # type: () -> List[List[Union[unicode, int]]]
        warnings.warn('LaTeXTranslator.hlsettingstack is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return [[self.builder.config.highlight_language, sys.maxsize]]

    def check_latex_elements(self):
        # type: () -> None
        warnings.warn('check_latex_elements() is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)

        for key in self.builder.config.latex_elements:
            if key not in self.elements:
                msg = __("Unknown configure key: latex_elements[%r] is ignored.")
                logger.warning(msg % key)


# Import old modules here for compatibility
# They should be imported after `LaTeXTranslator` to avoid recursive import.
#
# refs: https://github.com/sphinx-doc/sphinx/issues/4889
from sphinx.builders.latex.transforms import URI_SCHEMES, ShowUrlsTransform  # NOQA

# FIXME: Workaround to avoid circular import
# refs: https://github.com/sphinx-doc/sphinx/issues/5433
from sphinx.builders.latex.nodes import HYPERLINK_SUPPORT_NODES, captioned_literal_block, footnotetext  # NOQA
