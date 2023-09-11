# $Id: __init__.py 9331 2023-03-25 17:54:40Z aa-turner $
# Author: Engelbert Gruber, Günter Milde
# Maintainer: docutils-develop@lists.sourceforge.net
# Copyright: This module has been placed in the public domain.

"""LaTeX2e document tree Writer."""

__docformat__ = 'reStructuredText'

# code contributions from several people included, thanks to all.
# some named: David Abrahams, Julien Letessier, Lele Gaifax, and others.
#
# convention deactivate code by two # i.e. ##.

from pathlib import Path
import re
import string
from urllib.request import url2pathname
import warnings
try:
    import roman
except ImportError:
    import docutils.utils.roman as roman

from docutils import frontend, nodes, languages, writers, utils
from docutils.transforms import writer_aux
from docutils.utils.math import pick_math_environment, unichar2tex

LATEX_WRITER_DIR = Path(__file__).parent


class Writer(writers.Writer):

    supported = ('latex', 'latex2e')
    """Formats this writer supports."""

    default_template = 'default.tex'
    default_template_path = LATEX_WRITER_DIR
    default_preamble = ('% PDF Standard Fonts\n'
                        '\\usepackage{mathptmx} % Times\n'
                        '\\usepackage[scaled=.90]{helvet}\n'
                        '\\usepackage{courier}')
    table_style_values = [  # TODO: align-left, align-center, align-right, ??
                          'booktabs', 'borderless', 'colwidths-auto',
                          'nolines', 'standard']

    settings_spec = (
        'LaTeX-Specific Options',
        None,
        (('Specify LaTeX documentclass.  Default: "article".',
          ['--documentclass'],
          {'default': 'article', }),
         ('Specify document options.  Multiple options can be given, '
          'separated by commas.  Default: "a4paper".',
          ['--documentoptions'],
          {'default': 'a4paper', }),
         ('Format for footnote references: one of "superscript" or '
          '"brackets".  Default: "superscript".',
          ['--footnote-references'],
          {'choices': ['superscript', 'brackets'], 'default': 'superscript',
           'metavar': '<format>',
           'overrides': 'trim_footnote_reference_space'}),
         ('Use \\cite command for citations. (future default)',
          ['--use-latex-citations'],
          {'default': None, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Use figure floats for citations '
          '(might get mixed with real figures). (provisional default)',
          ['--figure-citations'],
          {'dest': 'use_latex_citations', 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ('Format for block quote attributions: one of "dash" (em-dash '
          'prefix), "parentheses"/"parens", or "none".  Default: "dash".',
          ['--attribution'],
          {'choices': ['dash', 'parentheses', 'parens', 'none'],
           'default': 'dash', 'metavar': '<format>'}),
         ('Specify LaTeX packages/stylesheets. '
          'A style is referenced with "\\usepackage" if extension is '
          '".sty" or omitted and with "\\input" else. '
          ' Overrides previous --stylesheet and --stylesheet-path settings.',
          ['--stylesheet'],
          {'default': '', 'metavar': '<file[,file,...]>',
           'overrides': 'stylesheet_path',
           'validator': frontend.validate_comma_separated_list}),
         ('Comma separated list of LaTeX packages/stylesheets. '
          'Relative paths are expanded if a matching file is found in '
          'the --stylesheet-dirs. With --link-stylesheet, '
          'the path is rewritten relative to the output *.tex file. ',
          ['--stylesheet-path'],
          {'metavar': '<file[,file,...]>', 'overrides': 'stylesheet',
           'validator': frontend.validate_comma_separated_list}),
         ('Link to the stylesheet(s) in the output file. (default)',
          ['--link-stylesheet'],
          {'dest': 'embed_stylesheet', 'action': 'store_false'}),
         ('Embed the stylesheet(s) in the output file. '
          'Stylesheets must be accessible during processing. ',
          ['--embed-stylesheet'],
          {'default': False, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Comma-separated list of directories where stylesheets are found. '
          'Used by --stylesheet-path when expanding relative path arguments. '
          'Default: ".".',
          ['--stylesheet-dirs'],
          {'metavar': '<dir[,dir,...]>',
           'validator': frontend.validate_comma_separated_list,
           'default': ['.']}),
         ('Customization by LaTeX code in the preamble. '
          'Default: select PDF standard fonts (Times, Helvetica, Courier).',
          ['--latex-preamble'],
          {'default': default_preamble}),
         ('Specify the template file. Default: "%s".' % default_template,
          ['--template'],
          {'default': default_template, 'metavar': '<file>'}),
         ('Table of contents by LaTeX. (default)',
          ['--use-latex-toc'],
          {'default': True, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Table of contents by Docutils (without page numbers).',
          ['--use-docutils-toc'],
          {'dest': 'use_latex_toc', 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ('Add parts on top of the section hierarchy.',
          ['--use-part-section'],
          {'default': False, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Attach author and date to the document info table. (default)',
          ['--use-docutils-docinfo'],
          {'dest': 'use_latex_docinfo', 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ('Attach author and date to the document title.',
          ['--use-latex-docinfo'],
          {'default': False, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ("Typeset abstract as topic. (default)",
          ['--topic-abstract'],
          {'dest': 'use_latex_abstract', 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ("Use LaTeX abstract environment for the document's abstract.",
          ['--use-latex-abstract'],
          {'default': False, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Color of any hyperlinks embedded in text. '
          'Default: "blue" (use "false" to disable).',
          ['--hyperlink-color'], {'default': 'blue'}),
         ('Additional options to the "hyperref" package.',
          ['--hyperref-options'], {'default': ''}),
         ('Enable compound enumerators for nested enumerated lists '
          '(e.g. "1.2.a.ii").',
          ['--compound-enumerators'],
          {'default': False, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Disable compound enumerators for nested enumerated lists. '
          '(default)',
          ['--no-compound-enumerators'],
          {'action': 'store_false', 'dest': 'compound_enumerators'}),
         ('Enable section ("." subsection ...) prefixes for compound '
          'enumerators.  This has no effect without --compound-enumerators.',
          ['--section-prefix-for-enumerators'],
          {'default': None, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Disable section prefixes for compound enumerators. (default)',
          ['--no-section-prefix-for-enumerators'],
          {'action': 'store_false', 'dest': 'section_prefix_for_enumerators'}),
         ('Set the separator between section number and enumerator '
          'for compound enumerated lists.  Default: "-".',
          ['--section-enumerator-separator'],
          {'default': '-', 'metavar': '<char>'}),
         ('When possible, use the specified environment for literal-blocks. '
          'Default: "" (fall back to "alltt").',
          ['--literal-block-env'],
          {'default': ''}),
         ('Deprecated alias for "--literal-block-env=verbatim".',
          ['--use-verbatim-when-possible'],
          {'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Table style. "standard" with horizontal and vertical lines, '
          '"booktabs" (LaTeX booktabs style) only horizontal lines '
          'above and below the table and below the header, or "borderless". '
          'Default: "standard"',
          ['--table-style'],
          {'default': ['standard'],
           'metavar': '<format>',
           'action': 'append',
           'validator': frontend.validate_comma_separated_list,
           'choices': table_style_values}),
         ('LaTeX graphicx package option. '
          'Possible values are "dvipdfmx", "dvips", "dvisvgm", '
          '"luatex", "pdftex", and "xetex".'
          'Default: "".',
          ['--graphicx-option'],
          {'default': ''}),
         ('LaTeX font encoding. '
          'Possible values are "", "T1" (default), "OT1", "LGR,T1" or '
          'any other combination of options to the `fontenc` package. ',
          ['--font-encoding'],
          {'default': 'T1'}),
         ('Per default the latex-writer puts the reference title into '
          'hyperreferences. Specify "ref*" or "pageref*" to get the section '
          'number or the page number.',
          ['--reference-label'],
          {'default': ''}),
         ('Specify style and database(s) for bibtex, for example '
          '"--use-bibtex=unsrt,mydb1,mydb2". Provisional!',
          ['--use-bibtex'],
          {'default': '',
           'metavar': '<style,bibfile[,bibfile,...]>',
           'validator': frontend.validate_comma_separated_list}),
         ('Use legacy functions with class value list for '
          '\\DUtitle and \\DUadmonition.',
          ['--legacy-class-functions'],
          {'default': False,
           'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Use \\DUrole and "DUclass" wrappers for class values. '
          'Place admonition content in an environment. (default)',
          ['--new-class-functions'],
          {'dest': 'legacy_class_functions',
           'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ('Use legacy algorithm to determine table column widths. '
          '(provisional default)',
          ['--legacy-column-widths'],
          {'default': None,
           'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Use new algorithm to determine table column widths. '
          '(future default)',
          ['--new-column-widths'],
          {'dest': 'legacy_column_widths',
           'action': 'store_false',
           'validator': frontend.validate_boolean}),
         # TODO: implement "latex footnotes" alternative
         ('Footnotes with numbers/symbols by Docutils. (default) '
          '(The alternative, --latex-footnotes, is not implemented yet.)',
          ['--docutils-footnotes'],
          {'default': True,
           'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ),
        )

    settings_defaults = {'sectnum_depth': 0}  # updated by SectNum transform
    config_section = 'latex2e writer'
    config_section_dependencies = ('writers', 'latex writers')

    head_parts = ('head_prefix', 'requirements', 'latex_preamble',
                  'stylesheet', 'fallbacks', 'pdfsetup', 'titledata')
    visitor_attributes = head_parts + ('title', 'subtitle',
                                       'body_pre_docinfo', 'docinfo',
                                       'dedication', 'abstract', 'body')

    output = None
    """Final translated form of `document`."""

    def __init__(self):
        writers.Writer.__init__(self)
        self.translator_class = LaTeXTranslator

    def get_transforms(self):
        # Override parent method to add latex-specific transforms
        return super().get_transforms() + [
                   # Convert specific admonitions to generic one
                   writer_aux.Admonitions,
                   # TODO: footnote collection transform
                   ]

    def translate(self):
        visitor = self.translator_class(self.document)
        self.document.walkabout(visitor)
        # copy parts
        for part in self.visitor_attributes:
            setattr(self, part, getattr(visitor, part))
        # get template string from file
        templatepath = Path(self.document.settings.template)
        if not templatepath.exists():
            templatepath = self.default_template_path / templatepath
        template = templatepath.read_text(encoding='utf-8')
        # fill template
        self.assemble_parts()  # create dictionary of parts
        self.output = string.Template(template).substitute(self.parts)

    def assemble_parts(self):
        """Assemble the `self.parts` dictionary of output fragments."""
        writers.Writer.assemble_parts(self)
        for part in self.visitor_attributes:
            lines = getattr(self, part)
            if part in self.head_parts:
                if lines:
                    lines.append('')  # to get a trailing newline
                self.parts[part] = '\n'.join(lines)
            else:
                # body contains inline elements, so join without newline
                self.parts[part] = ''.join(lines)


class Babel:
    """Language specifics for LaTeX."""

    # TeX (babel) language names:
    # ! not all of these are supported by Docutils!
    #
    # based on LyX' languages file with adaptions to `BCP 47`_
    # (https://www.rfc-editor.org/rfc/bcp/bcp47.txt) and
    # http://www.tug.org/TUGboat/Articles/tb29-3/tb93miklavec.pdf
    # * the key without subtags is the default
    # * case is ignored
    # cf. https://docutils.sourceforge.io/docs/howto/i18n.html
    #     https://www.w3.org/International/articles/language-tags/
    # and http://www.iana.org/assignments/language-subtag-registry
    language_codes = {
        # code          TeX/Babel-name    comment
        'af':           'afrikaans',
        'ar':           'arabic',
        # 'be':           'belarusian',
        'bg':           'bulgarian',
        'br':           'breton',
        'ca':           'catalan',
        # 'cop':          'coptic',
        'cs':           'czech',
        'cy':           'welsh',
        'da':           'danish',
        'de':           'ngerman',        # new spelling (de_1996)
        'de-1901':      'german',         # old spelling
        'de-AT':        'naustrian',
        'de-AT-1901':   'austrian',
        'dsb':          'lowersorbian',
        'el':           'greek',          # monotonic (el-monoton)
        'el-polyton':   'polutonikogreek',
        'en':           'english',        # TeX' default language
        'en-AU':        'australian',
        'en-CA':        'canadian',
        'en-GB':        'british',
        'en-NZ':        'newzealand',
        'en-US':        'american',
        'eo':           'esperanto',
        'es':           'spanish',
        'et':           'estonian',
        'eu':           'basque',
        # 'fa':           'farsi',
        'fi':           'finnish',
        'fr':           'french',
        'fr-CA':        'canadien',
        'ga':           'irish',          # Irish Gaelic
        # 'grc':                          # Ancient Greek
        'grc-ibycus':   'ibycus',         # Ibycus encoding
        'gl':           'galician',
        'he':           'hebrew',
        'hr':           'croatian',
        'hsb':          'uppersorbian',
        'hu':           'magyar',
        'ia':           'interlingua',
        'id':           'bahasai',        # Bahasa (Indonesian)
        'is':           'icelandic',
        'it':           'italian',
        'ja':           'japanese',
        'kk':           'kazakh',
        'la':           'latin',
        'lt':           'lithuanian',
        'lv':           'latvian',
        'mn':           'mongolian',      # Mongolian, Cyrillic (mn-cyrl)
        'ms':           'bahasam',        # Bahasa (Malay)
        'nb':           'norsk',          # Norwegian Bokmal
        'nl':           'dutch',
        'nn':           'nynorsk',        # Norwegian Nynorsk
        'no':           'norsk',          # Norwegian (Bokmal)
        'pl':           'polish',
        'pt':           'portuges',
        'pt-BR':        'brazil',
        'ro':           'romanian',
        'ru':           'russian',
        'se':           'samin',          # North Sami
        'sh-Cyrl':      'serbianc',       # Serbo-Croatian, Cyrillic
        'sh-Latn':      'serbian',        # Serbo-Croatian, Latin (cf. 'hr')
        'sk':           'slovak',
        'sl':           'slovene',
        'sq':           'albanian',
        'sr':           'serbianc',       # Serbian, Cyrillic (contributed)
        'sr-Latn':      'serbian',        # Serbian, Latin script
        'sv':           'swedish',
        # 'th':           'thai',
        'tr':           'turkish',
        'uk':           'ukrainian',
        'vi':           'vietnam',
        # zh-Latn:      Chinese Pinyin
        }
    # normalize (downcase) keys
    language_codes = {k.lower(): v for k, v in language_codes.items()}

    warn_msg = 'Language "%s" not supported by LaTeX (babel)'

    # "Active characters" are shortcuts that start a LaTeX macro and may need
    # escaping for literals use. Characters that prevent literal use (e.g.
    # starting accent macros like "a -> ä) will be deactivated if one of the
    # defining languages is used in the document.
    # Special cases:
    #  ~ (tilde) -- used in estonian, basque, galician, and old versions of
    #    spanish -- cannot be deactivated as it denotes a no-break space macro,
    #  " (straight quote) -- used in albanian, austrian, basque
    #    brazil, bulgarian, catalan, czech, danish, dutch, estonian,
    #    finnish, galician, german, icelandic, italian, latin, naustrian,
    #    ngerman, norsk, nynorsk, polish, portuges, russian, serbian, slovak,
    #    slovene, spanish, swedish, ukrainian, and uppersorbian --
    #    is escaped as ``\textquotedbl``.
    active_chars = {
                    # TeX/Babel-name:  active characters to deactivate
                    # 'breton':        ':;!?'  # ensure whitespace
                    # 'esperanto':     '^',
                    # 'estonian':      '~"`',
                    # 'french':        ':;!?'  # ensure whitespace
                    'galician':        '.<>',  # also '~"'
                    # 'magyar':        '`',  # for special hyphenation cases
                    'spanish':         '.<>',  # old versions also '~'
                    # 'turkish':       ':!='  # ensure whitespace
                   }

    def __init__(self, language_code, reporter=None):
        self.reporter = reporter
        self.language = self.language_name(language_code)
        self.otherlanguages = {}

    def __call__(self):
        """Return the babel call with correct options and settings"""
        languages = sorted(self.otherlanguages.keys())
        languages.append(self.language or 'english')
        self.setup = [r'\usepackage[%s]{babel}' % ','.join(languages)]
        # Deactivate "active characters"
        shorthands = []
        for c in ''.join(self.active_chars.get(lng, '') for lng in languages):
            if c not in shorthands:
                shorthands.append(c)
        if shorthands:
            self.setup.append(r'\AtBeginDocument{\shorthandoff{%s}}'
                              % ''.join(shorthands))
        # Including '~' in shorthandoff prevents its use as no-break space
        if 'galician' in languages:
            self.setup.append(r'\deactivatetilden % restore ~ in Galician')
        if 'estonian' in languages:
            self.setup.extend([r'\makeatletter',
                               r'  \addto\extrasestonian{\bbl@deactivate{~}}',
                               r'\makeatother'])
        if 'basque' in languages:
            self.setup.extend([r'\makeatletter',
                               r'  \addto\extrasbasque{\bbl@deactivate{~}}',
                               r'\makeatother'])
        if (languages[-1] == 'english'
            and 'french' in self.otherlanguages.keys()):
            self.setup += ['% Prevent side-effects if French hyphenation '
                           'patterns are not loaded:',
                           r'\frenchbsetup{StandardLayout}',
                           r'\AtBeginDocument{\selectlanguage{%s}'
                           r'\noextrasfrench}' % self.language]
        return '\n'.join(self.setup)

    def language_name(self, language_code):
        """Return TeX language name for `language_code`"""
        for tag in utils.normalize_language_tag(language_code):
            try:
                return self.language_codes[tag]
            except KeyError:
                pass
        if self.reporter is not None:
            self.reporter.warning(self.warn_msg % language_code)
        return ''

    def get_language(self):
        # Obsolete, kept for backwards compatibility with Sphinx
        return self.language


# Building blocks for the latex preamble
# --------------------------------------

class SortableDict(dict):
    """Dictionary with additional sorting methods

    Tip: use key starting with with '_' for sorting before small letters
         and with '~' for sorting after small letters.
    """
    def sortedkeys(self):
        """Return sorted list of keys"""
        return sorted(self.keys())

    def sortedvalues(self):
        """Return list of values sorted by keys"""
        return [self[key] for key in self.sortedkeys()]


# PreambleCmds
# `````````````
# A container for LaTeX code snippets that can be
# inserted into the preamble if required in the document.
#
# .. The package 'makecmds' would enable shorter definitions using the
#    \providelength and \provideenvironment commands.
#    However, it is pretty non-standard (texlive-latex-extra).

class PreambleCmds:
    """Building blocks for the latex preamble."""


# Requirements and Setup

PreambleCmds.color = r"""\usepackage{color}"""

PreambleCmds.float = r"""\usepackage{float} % extended float configuration
\floatplacement{figure}{H} % place figures here definitely"""

PreambleCmds.linking = r"""%% hyperlinks:
\ifthenelse{\isundefined{\hypersetup}}{
  \usepackage[%s]{hyperref}
  \usepackage{bookmark}
  \urlstyle{same} %% normal text font (alternatives: tt, rm, sf)
}{}"""

PreambleCmds.minitoc = r"""%% local table of contents
\usepackage{minitoc}"""

PreambleCmds.table = r"""\usepackage{longtable,ltcaption,array}
\setlength{\extrarowheight}{2pt}
\newlength{\DUtablewidth} % internal use in tables"""

PreambleCmds.table_columnwidth = (
    r'\newcommand{\DUcolumnwidth}[1]'
    r'{\dimexpr#1\DUtablewidth-2\tabcolsep\relax}')

PreambleCmds.textcomp = r"""\usepackage{textcomp} % text symbol macros"""
# TODO? Options [force,almostfull] prevent spurious error messages,
# see de.comp.text.tex/2005-12/msg01855

# backwards compatibility definitions

PreambleCmds.abstract_legacy = r"""
% abstract title
\providecommand*{\DUtitleabstract}[1]{\centerline{\textbf{#1}}}"""

# see https://sourceforge.net/p/docutils/bugs/339/
PreambleCmds.admonition_legacy = r"""
% admonition (specially marked topic)
\providecommand{\DUadmonition}[2][class-arg]{%
  % try \DUadmonition#1{#2}:
  \ifcsname DUadmonition#1\endcsname%
    \csname DUadmonition#1\endcsname{#2}%
  \else
    \begin{center}
      \fbox{\parbox{0.9\linewidth}{#2}}
    \end{center}
  \fi
}"""

PreambleCmds.error_legacy = r"""
% error admonition title
\providecommand*{\DUtitleerror}[1]{\DUtitle{\color{red}#1}}"""

PreambleCmds.title_legacy = r"""
% title for topics, admonitions, unsupported section levels, and sidebar
\providecommand*{\DUtitle}[2][class-arg]{%
  % call \DUtitle#1{#2} if it exists:
  \ifcsname DUtitle#1\endcsname%
    \csname DUtitle#1\endcsname{#2}%
  \else
    \smallskip\noindent\textbf{#2}\smallskip%
  \fi
}"""

PreambleCmds.toc_list = r"""
\providecommand*{\DUCLASScontents}{%
  \renewenvironment{itemize}%
    {\begin{list}{}{\setlength{\partopsep}{0pt}
                    \setlength{\parsep}{0pt}}
                   }%
    {\end{list}}%
}"""

PreambleCmds.ttem = r"""
% character width in monospaced font
\newlength{\ttemwidth}
\settowidth{\ttemwidth}{\ttfamily M}"""

## PreambleCmds.caption = r"""% configure caption layout
## \usepackage{caption}
## \captionsetup{singlelinecheck=false}% no exceptions for one-liners"""


# Definitions from docutils.sty::

def _read_block(fp):
    block = [next(fp)]  # first line (empty)
    for line in fp:
        if not line.strip():
            break
        block.append(line)
    return ''.join(block).rstrip()


with open(LATEX_WRITER_DIR/'docutils.sty', encoding='utf-8') as fp:
    for line in fp:
        line = line.strip('% \n')
        if not line.endswith('::'):
            continue
        block_name = line.rstrip(':')
        if not block_name:
            continue
        definitions = _read_block(fp)
        if block_name in ('color', 'float', 'table', 'textcomp'):
            definitions = definitions.strip()
        # print('Block: `%s`'% block_name)
        # print(definitions)
        setattr(PreambleCmds, block_name, definitions)


# LaTeX encoding maps
# -------------------
# ::

class CharMaps:
    """LaTeX representations for active and Unicode characters."""

    # characters that need escaping even in `alltt` environments:
    alltt = {
        ord('\\'): '\\textbackslash{}',
        ord('{'): '\\{',
        ord('}'): '\\}',
    }
    # characters that normally need escaping:
    special = {
        ord('#'): '\\#',
        ord('$'): '\\$',
        ord('%'): '\\%',
        ord('&'): '\\&',
        ord('~'): '\\textasciitilde{}',
        ord('_'): '\\_',
        ord('^'): '\\textasciicircum{}',
        # straight double quotes are 'active' in many languages
        ord('"'): '\\textquotedbl{}',
        # Square brackets are ordinary chars and cannot be escaped with '\',
        # so we put them in a group '{[}'. (Alternative: ensure that all
        # macros with optional arguments are terminated with {} and text
        # inside any optional argument is put in a group ``[{text}]``).
        # Commands with optional args inside an optional arg must be put in a
        # group, e.g. ``\item[{\hyperref[label]{text}}]``.
        ord('['): '{[}',
        ord(']'): '{]}',
        # the soft hyphen is unknown in 8-bit text
        # and not properly handled by XeTeX
        0x00AD: '\\-',  # SOFT HYPHEN
    }
    # Unicode chars that are not recognized by LaTeX's utf8 encoding
    unsupported_unicode = {
        # TODO: ensure white space also at the beginning of a line?
        # 0x00A0: '\\leavevmode\\nobreak\\vadjust{}~'
        0x2000: '\\enskip',                        # EN QUAD
        0x2001: '\\quad',                          # EM QUAD
        0x2002: '\\enskip',                        # EN SPACE
        0x2003: '\\quad',                          # EM SPACE
        0x2008: '\\,',                             # PUNCTUATION SPACE
        0x200b: '\\hspace{0pt}',                   # ZERO WIDTH SPACE
        0x202F: '\\,',                             # NARROW NO-BREAK SPACE
        # 0x02d8: '\\\u{ }',                       # BREVE
        0x2011: '\\hbox{-}',                       # NON-BREAKING HYPHEN
        0x212b: '\\AA',                            # ANGSTROM SIGN
        0x21d4: '\\ensuremath{\\Leftrightarrow}',  # LEFT RIGHT DOUBLE ARROW
        0x2260: '\\ensuremath{\\neq}',             # NOT EQUAL TO
        0x2261: '\\ensuremath{\\equiv}',           # IDENTICAL TO
        0x2264: '\\ensuremath{\\le}',              # LESS-THAN OR EQUAL TO
        0x2265: '\\ensuremath{\\ge}',              # GREATER-THAN OR EQUAL TO
        # Docutils footnote symbols:
        0x2660: '\\ensuremath{\\spadesuit}',
        0x2663: '\\ensuremath{\\clubsuit}',
        0xfb00: 'ff',                              # LATIN SMALL LIGATURE FF
        0xfb01: 'fi',                              # LATIN SMALL LIGATURE FI
        0xfb02: 'fl',                              # LATIN SMALL LIGATURE FL
        0xfb03: 'ffi',                             # LATIN SMALL LIGATURE FFI
        0xfb04: 'ffl',                             # LATIN SMALL LIGATURE FFL
    }
    # Unicode chars that are recognized by LaTeX's utf8 encoding
    utf8_supported_unicode = {
        0x00A0: '~',                   # NO-BREAK SPACE
        0x00AB: '\\guillemotleft{}',   # LEFT-POINTING DOUBLE ANGLE QUOTATION
        0x00bb: '\\guillemotright{}',  # RIGHT-POINTING DOUBLE ANGLE QUOTATION
        0x200C: '\\textcompwordmark{}',  # ZERO WIDTH NON-JOINER
        0x2013: '\\textendash{}',
        0x2014: '\\textemdash{}',
        0x2018: '\\textquoteleft{}',
        0x2019: '\\textquoteright{}',
        0x201A: '\\quotesinglbase{}',    # SINGLE LOW-9 QUOTATION MARK
        0x201C: '\\textquotedblleft{}',
        0x201D: '\\textquotedblright{}',
        0x201E: '\\quotedblbase{}',      # DOUBLE LOW-9 QUOTATION MARK
        0x2030: '\\textperthousand{}',   # PER MILLE SIGN
        0x2031: '\\textpertenthousand{}',  # PER TEN THOUSAND SIGN
        0x2039: '\\guilsinglleft{}',
        0x203A: '\\guilsinglright{}',
        0x2423: '\\textvisiblespace{}',  # OPEN BOX
        0x2020: '\\dag{}',
        0x2021: '\\ddag{}',
        0x2026: '\\dots{}',
        0x2122: '\\texttrademark{}',
    }
    # recognized with 'utf8', if textcomp is loaded
    textcomp = {
        # Latin-1 Supplement
        0x00a2: '\\textcent{}',              # ¢ CENT SIGN
        0x00a4: '\\textcurrency{}',          # ¤ CURRENCY SYMBOL
        0x00a5: '\\textyen{}',               # ¥ YEN SIGN
        0x00a6: '\\textbrokenbar{}',         # ¦ BROKEN BAR
        0x00a7: '\\textsection{}',           # § SECTION SIGN
        0x00a8: '\\textasciidieresis{}',     # ¨ DIAERESIS
        0x00a9: '\\textcopyright{}',         # © COPYRIGHT SIGN
        0x00aa: '\\textordfeminine{}',       # ª FEMININE ORDINAL INDICATOR
        0x00ac: '\\textlnot{}',              # ¬ NOT SIGN
        0x00ae: '\\textregistered{}',        # ® REGISTERED SIGN
        0x00af: '\\textasciimacron{}',       # ¯ MACRON
        0x00b0: '\\textdegree{}',            # ° DEGREE SIGN
        0x00b1: '\\textpm{}',                # ± PLUS-MINUS SIGN
        0x00b2: '\\texttwosuperior{}',       # ² SUPERSCRIPT TWO
        0x00b3: '\\textthreesuperior{}',     # ³ SUPERSCRIPT THREE
        0x00b4: '\\textasciiacute{}',        # ´ ACUTE ACCENT
        0x00b5: '\\textmu{}',                # µ MICRO SIGN
        0x00b6: '\\textparagraph{}',         # ¶ PILCROW SIGN # != \textpilcrow
        0x00b9: '\\textonesuperior{}',       # ¹ SUPERSCRIPT ONE
        0x00ba: '\\textordmasculine{}',      # º MASCULINE ORDINAL INDICATOR
        0x00bc: '\\textonequarter{}',        # 1/4 FRACTION
        0x00bd: '\\textonehalf{}',           # 1/2 FRACTION
        0x00be: '\\textthreequarters{}',     # 3/4 FRACTION
        0x00d7: '\\texttimes{}',             # × MULTIPLICATION SIGN
        0x00f7: '\\textdiv{}',               # ÷ DIVISION SIGN
        # others
        0x0192: '\\textflorin{}',            # LATIN SMALL LETTER F WITH HOOK
        0x02b9: '\\textasciiacute{}',        # MODIFIER LETTER PRIME
        0x02ba: '\\textacutedbl{}',          # MODIFIER LETTER DOUBLE PRIME
        0x2016: '\\textbardbl{}',            # DOUBLE VERTICAL LINE
        0x2022: '\\textbullet{}',            # BULLET
        0x2032: '\\textasciiacute{}',        # PRIME
        0x2033: '\\textacutedbl{}',          # DOUBLE PRIME
        0x2035: '\\textasciigrave{}',        # REVERSED PRIME
        0x2036: '\\textgravedbl{}',          # REVERSED DOUBLE PRIME
        0x203b: '\\textreferencemark{}',     # REFERENCE MARK
        0x203d: '\\textinterrobang{}',       # INTERROBANG
        0x2044: '\\textfractionsolidus{}',   # FRACTION SLASH
        0x2045: '\\textlquill{}',            # LEFT SQUARE BRACKET WITH QUILL
        0x2046: '\\textrquill{}',            # RIGHT SQUARE BRACKET WITH QUILL
        0x2052: '\\textdiscount{}',          # COMMERCIAL MINUS SIGN
        0x20a1: '\\textcolonmonetary{}',     # COLON SIGN
        0x20a3: '\\textfrenchfranc{}',       # FRENCH FRANC SIGN
        0x20a4: '\\textlira{}',              # LIRA SIGN
        0x20a6: '\\textnaira{}',             # NAIRA SIGN
        0x20a9: '\\textwon{}',               # WON SIGN
        0x20ab: '\\textdong{}',              # DONG SIGN
        0x20ac: '\\texteuro{}',              # EURO SIGN
        0x20b1: '\\textpeso{}',              # PESO SIGN
        0x20b2: '\\textguarani{}',           # GUARANI SIGN
        0x2103: '\\textcelsius{}',           # DEGREE CELSIUS
        0x2116: '\\textnumero{}',            # NUMERO SIGN
        0x2117: '\\textcircledP{}',          # SOUND RECORDING COPYRIGHT
        0x211e: '\\textrecipe{}',            # PRESCRIPTION TAKE
        0x2120: '\\textservicemark{}',       # SERVICE MARK
        0x2122: '\\texttrademark{}',         # TRADE MARK SIGN
        0x2126: '\\textohm{}',               # OHM SIGN
        0x2127: '\\textmho{}',               # INVERTED OHM SIGN
        0x212e: '\\textestimated{}',         # ESTIMATED SYMBOL
        0x2190: '\\textleftarrow{}',         # LEFTWARDS ARROW
        0x2191: '\\textuparrow{}',           # UPWARDS ARROW
        0x2192: '\\textrightarrow{}',        # RIGHTWARDS ARROW
        0x2193: '\\textdownarrow{}',         # DOWNWARDS ARROW
        0x2212: '\\textminus{}',             # MINUS SIGN
        0x2217: '\\textasteriskcentered{}',  # ASTERISK OPERATOR
        0x221a: '\\textsurd{}',              # SQUARE ROOT
        0x2422: '\\textblank{}',             # BLANK SYMBOL
        0x25e6: '\\textopenbullet{}',        # WHITE BULLET
        0x25ef: '\\textbigcircle{}',         # LARGE CIRCLE
        0x266a: '\\textmusicalnote{}',       # EIGHTH NOTE
        0x26ad: '\\textmarried{}',           # MARRIAGE SYMBOL
        0x26ae: '\\textdivorced{}',          # DIVORCE SYMBOL
        0x27e8: '\\textlangle{}',            # MATHEMATICAL LEFT ANGLE BRACKET
        0x27e9: '\\textrangle{}',            # MATHEMATICAL RIGHT ANGLE BRACKET
    }
    # Unicode chars that require a feature/package to render
    pifont = {
        0x2665: '\\ding{170}',               # black heartsuit
        0x2666: '\\ding{169}',               # black diamondsuit
        0x2713: '\\ding{51}',                # check mark
        0x2717: '\\ding{55}',                # check mark
    }
    # TODO: greek alphabet ... ?
    # see also LaTeX codec
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/252124
    # and unimap.py from TeXML


class DocumentClass:
    """Details of a LaTeX document class."""

    def __init__(self, document_class, with_part=False):
        self.document_class = document_class
        self._with_part = with_part
        self.sections = ['section', 'subsection', 'subsubsection',
                         'paragraph', 'subparagraph']
        if self.document_class in ('book', 'memoir', 'report',
                                   'scrbook', 'scrreprt'):
            self.sections.insert(0, 'chapter')
        if self._with_part:
            self.sections.insert(0, 'part')

    def section(self, level):
        """Return the LaTeX section name for section `level`.

        The name depends on the specific document class.
        Level is 1,2,3..., as level 0 is the title.
        """
        if level <= len(self.sections):
            return self.sections[level-1]
        # unsupported levels
        return 'DUtitle'

    def latex_section_depth(self, depth):
        """
        Return LaTeX equivalent of Docutils section level `depth`.

        Given the value of the ``:depth:`` option of the "contents" or
        "sectnum" directive, return the corresponding value for the
        LaTeX ``tocdepth`` or ``secnumdepth`` counters.
        """
        depth = min(depth, len(self.sections))  # limit to supported levels
        if 'chapter' in self.sections:
            depth -= 1
        if self.sections[0] == 'part':
            depth -= 1
        return depth


class Table:
    """Manage a table while traversing.

    Table style might be

    :standard:   horizontal and vertical lines
    :booktabs:   only horizontal lines (requires "booktabs" LaTeX package)
    :borderless: no borders around table cells
    :nolines:    alias for borderless

    :colwidths-auto:  column widths determined by LaTeX
    """
    def __init__(self, translator, latex_type):
        self._translator = translator
        self._latex_type = latex_type
        self.legacy_column_widths = False

        self.close()
        self._colwidths = []
        self._rowspan = []
        self._in_thead = 0

    def open(self):
        self._open = True
        self._col_specs = []
        self.caption = []
        self._attrs = {}
        self._in_head = False  # maybe context with search

    def close(self):
        self._open = False
        self._col_specs = None
        self.caption = []
        self._attrs = {}
        self.stubs = []
        self.colwidths_auto = False

    def is_open(self):
        return self._open

    def set_table_style(self, node, settings):
        self.legacy_column_widths = settings.legacy_column_widths
        if 'align' in node:
            self.set('align', node['align'])
        # TODO: elif 'align' in classes/settings.table-style:
        #           self.set('align', ...)
        borders = [cls.replace('nolines', 'borderless')
                   for cls in (['standard']
                               + settings.table_style
                               + node['classes'])
                   if cls in ('standard', 'booktabs', 'borderless', 'nolines')]
        self.borders = borders[-1]
        self.colwidths_auto = (('colwidths-auto' in node['classes']
                                or 'colwidths-auto' in settings.table_style)
                               and 'colwidths-given' not in node['classes']
                               and 'width' not in node)

    def get_latex_type(self):
        if self._latex_type == 'longtable' and not self.caption:
            # do not advance the "table" counter (requires "ltcaption" package)
            return 'longtable*'
        return self._latex_type

    def set(self, attr, value):
        self._attrs[attr] = value

    def get(self, attr):
        if attr in self._attrs:
            return self._attrs[attr]
        return None

    def get_vertical_bar(self):
        if self.borders == 'standard':
            return '|'
        return ''

    # horizontal lines are drawn below a row,
    def get_opening(self, width=r'\linewidth'):
        align_map = {'left': '[l]',
                     'center': '[c]',
                     'right': '[r]',
                     None: ''}
        align = align_map.get(self.get('align'))
        latex_type = self.get_latex_type()
        if align and latex_type not in ("longtable", "longtable*"):
            opening = [r'\noindent\makebox[\linewidth]%s{%%' % (align,),
                       r'\begin{%s}' % (latex_type,)]
        else:
            opening = [r'\begin{%s}%s' % (latex_type, align)]
        if not self.colwidths_auto:
            if self.borders == 'standard' and not self.legacy_column_widths:
                opening.insert(-1, r'\setlength{\DUtablewidth}'
                               r'{\dimexpr%s-%i\arrayrulewidth\relax}%%'
                               % (width, len(self._col_specs)+1))
            else:
                opening.insert(-1, r'\setlength{\DUtablewidth}{%s}%%' % width)
        return '\n'.join(opening)

    def get_closing(self):
        closing = []
        if self.borders == 'booktabs':
            closing.append(r'\bottomrule')
        # elif self.borders == 'standard':
        #     closing.append(r'\hline')
        closing.append(r'\end{%s}' % self.get_latex_type())
        if (self.get('align')
            and self.get_latex_type() not in ("longtable", "longtable*")):
            closing.append('}')
        return '\n'.join(closing)

    def visit_colspec(self, node):
        self._col_specs.append(node)
        # "stubs" list is an attribute of the tgroup element:
        self.stubs.append(node.attributes.get('stub'))

    def get_colspecs(self, node):
        """Return column specification for longtable.
        """
        bar = self.get_vertical_bar()
        self._rowspan = [0] * len(self._col_specs)
        if self.colwidths_auto:
            self._colwidths = []
            latex_colspecs = ['l'] * len(self._col_specs)
        elif self.legacy_column_widths:
            # use old algorithm for backwards compatibility
            width = 80  # assumed standard line length
            factor = 0.93  # do not make it full linewidth
            # first see if we get too wide.
            total_width = sum(node['colwidth']+1 for node in self._col_specs)
            if total_width > width:
                factor *= width / total_width
            self._colwidths = [(factor * (node['colwidth']+1)/width)
                               + 0.005 for node in self._col_specs]
            latex_colspecs = ['p{%.3f\\DUtablewidth}' % colwidth
                              for colwidth in self._colwidths]
        else:
            # No of characters corresponding to table width = 100%
            #   Characters/line with LaTeX article, A4, Times, default margins
            #   depends on character:  M: 40, A: 50, x: 70, i: 120.
            norm_length = 40
            # Allowance to prevent unpadded columns like
            #   === ==
            #   ABC DE
            #   === ==
            # getting too narrow:
            if 'colwidths-given' not in node.parent.parent['classes']:
                allowance = 1
            else:
                allowance = 0  # "widths" option specified, use exact ratio
            self._colwidths = [(node['colwidth']+allowance)/norm_length
                               for node in self._col_specs]
            total_width = sum(self._colwidths)
            # Limit to 100%, force 100% if table width is specified:
            if total_width > 1 or 'width' in node.parent.parent.attributes:
                self._colwidths = [colwidth/total_width
                                   for colwidth in self._colwidths]
            latex_colspecs = ['p{\\DUcolumnwidth{%.3f}}' % colwidth
                              for colwidth in self._colwidths]
        return bar + bar.join(latex_colspecs) + bar

    def get_column_width(self):
        """Return columnwidth for current cell (not multicell)."""
        try:
            if self.legacy_column_widths:
                return '%.2f\\DUtablewidth'%self._colwidths[self._cell_in_row]
            return '\\DUcolumnwidth{%.2f}'%self._colwidths[self._cell_in_row]
        except IndexError:
            return '*'

    def get_multicolumn_width(self, start, len_):
        """Return sum of columnwidths for multicell."""
        try:
            multicol_width = sum(self._colwidths[start + co]
                                 for co in range(len_))
            if self.legacy_column_widths:
                return 'p{%.2f\\DUtablewidth}' % multicol_width
            return 'p{\\DUcolumnwidth{%.3f}}' % multicol_width
        except IndexError:
            return 'l'

    def get_caption(self):
        if not self.caption:
            return ''
        caption = ''.join(self.caption)
        if 1 == self._translator.thead_depth():
            return r'\caption{%s}\\' '\n' % caption
        return r'\caption[]{%s (... continued)}\\' '\n' % caption

    def need_recurse(self):
        if self._latex_type == 'longtable':
            return 1 == self._translator.thead_depth()
        return 0

    def visit_thead(self):
        self._in_thead += 1
        if self.borders == 'standard':
            return ['\\hline\n']
        elif self.borders == 'booktabs':
            return ['\\toprule\n']
        return []

    def depart_thead(self):
        a = []
        ## if self.borders == 'standard':
        ##     a.append('\\hline\n')
        if self.borders == 'booktabs':
            a.append('\\midrule\n')
        if self._latex_type == 'longtable':
            if 1 == self._translator.thead_depth():
                a.append('\\endfirsthead\n')
            else:
                n_c = len(self._col_specs)
                a.append('\\endhead\n')
                # footer on all but last page (if it fits):
                twidth = sum(node['colwidth']+2 for node in self._col_specs)
                if twidth > 30 or (twidth > 12 and not self.colwidths_auto):
                    a.append(r'\multicolumn{%d}{%s}'
                             % (n_c, self.get_multicolumn_width(0, n_c))
                             + r'{\raggedleft\ldots continued on next page}\\'
                             + '\n')
                a.append('\\endfoot\n\\endlastfoot\n')
            # for longtable one could add firsthead, foot and lastfoot
        self._in_thead -= 1
        return a

    def visit_row(self):
        self._cell_in_row = 0

    def depart_row(self):
        res = [' \\\\\n']
        self._cell_in_row = None  # remove cell counter
        for i in range(len(self._rowspan)):
            if self._rowspan[i] > 0:
                self._rowspan[i] -= 1

        if self.borders == 'standard':
            rowspans = [i+1 for i in range(len(self._rowspan))
                        if self._rowspan[i] <= 0]
            if len(rowspans) == len(self._rowspan):
                res.append('\\hline\n')
            else:
                cline = ''
                rowspans.reverse()
                # TODO merge clines
                while True:
                    try:
                        c_start = rowspans.pop()
                    except IndexError:
                        break
                    cline += '\\cline{%d-%d}\n' % (c_start, c_start)
                res.append(cline)
        return res

    def set_rowspan(self, cell, value):
        try:
            self._rowspan[cell] = value
        except IndexError:
            pass

    def get_rowspan(self, cell):
        try:
            return self._rowspan[cell]
        except IndexError:
            return 0

    def get_entry_number(self):
        return self._cell_in_row

    def visit_entry(self):
        self._cell_in_row += 1

    def is_stub_column(self):
        if len(self.stubs) >= self._cell_in_row:
            return self.stubs[self._cell_in_row]
        return False


class LaTeXTranslator(nodes.NodeVisitor):
    """
    Generate code for 8-bit LaTeX from a Docutils document tree.

    See the docstring of docutils.writers._html_base.HTMLTranslator for
    notes on and examples of safe subclassing.
    """

    # When options are given to the documentclass, latex will pass them
    # to other packages, as done with babel.
    # Dummy settings might be taken from document settings

    # Generate code for typesetting with 8-bit latex/pdflatex vs.
    # xelatex/lualatex engine. Overwritten by the XeTeX writer
    is_xetex = False

    # Config setting defaults
    # -----------------------

    # TODO: use mixins for different implementations.
    # list environment for docinfo. else tabularx
    ## use_optionlist_for_docinfo = False # TODO: NOT YET IN USE

    # Use compound enumerations (1.A.1.)
    compound_enumerators = False

    # If using compound enumerations, include section information.
    section_prefix_for_enumerators = False

    # This is the character that separates the section ("." subsection ...)
    # prefix from the regular list enumerator.
    section_enumerator_separator = '-'

    # Auxiliary variables
    # -------------------

    has_latex_toc = False  # is there a toc in the doc? (needed by minitoc)
    section_level = 0

    # Flags to encode():
    # inside citation reference labels underscores dont need to be escaped
    inside_citation_reference_label = False
    verbatim = False                    # do not encode
    insert_non_breaking_blanks = False  # replace blanks by "~"
    insert_newline = False              # add latex newline commands
    literal = False                     # literal text (block or inline)
    alltt = False                       # inside `alltt` environment

    def __init__(self, document, babel_class=Babel):
        super().__init__(document)
        # Reporter
        # ~~~~~~~~
        self.warn = self.document.reporter.warning
        self.error = self.document.reporter.error

        # Settings
        # ~~~~~~~~
        self.settings = settings = document.settings
        # warn of deprecated settings and changing defaults:
        if settings.use_latex_citations is None and not settings.use_bibtex:
            settings.use_latex_citations = False
            warnings.warn('The default for the setting "use_latex_citations" '
                          'will change to "True" in Docutils 1.0.',
                          FutureWarning, stacklevel=7)
        if settings.legacy_column_widths is None:
            settings.legacy_column_widths = True
            warnings.warn('The default for the setting "legacy_column_widths" '
                          'will change to "False" in Docutils 1.0.)',
                          FutureWarning, stacklevel=7)
        if settings.use_verbatim_when_possible is not None:
            warnings.warn(
                'The configuration setting "use_verbatim_when_possible" '
                'will be removed in Docutils 2.0. '
                'Use "literal_block_env: verbatim".',
                FutureWarning, stacklevel=7)

        self.latex_encoding = self.to_latex_encoding(settings.output_encoding)
        self.use_latex_toc = settings.use_latex_toc
        self.use_latex_docinfo = settings.use_latex_docinfo
        self.use_latex_citations = settings.use_latex_citations
        self._reference_label = settings.reference_label
        self.hyperlink_color = settings.hyperlink_color
        self.compound_enumerators = settings.compound_enumerators
        self.font_encoding = getattr(settings, 'font_encoding', '')
        self.section_prefix_for_enumerators = (
            settings.section_prefix_for_enumerators)
        self.section_enumerator_separator = (
            settings.section_enumerator_separator.replace('_', r'\_'))
        # literal blocks:
        self.literal_block_env = ''
        self.literal_block_options = ''
        if settings.literal_block_env:
            (none,
             self.literal_block_env,
             self.literal_block_options,
             none) = re.split(r'(\w+)(.*)', settings.literal_block_env)
        elif settings.use_verbatim_when_possible:
            self.literal_block_env = 'verbatim'

        if settings.use_bibtex:
            self.use_latex_citations = True
        self.bibtex = settings.use_bibtex
        # language module for Docutils-generated text
        # (labels, bibliographic_fields, and author_separators)
        self.language_module = languages.get_language(settings.language_code,
                                                      document.reporter)
        self.babel = babel_class(settings.language_code, document.reporter)
        self.author_separator = self.language_module.author_separators[0]
        d_options = [settings.documentoptions]
        if self.babel.language not in ('english', ''):
            d_options.append(self.babel.language)
        self.documentoptions = ','.join(filter(None, d_options))
        self.d_class = DocumentClass(settings.documentclass,
                                     settings.use_part_section)
        # graphic package options:
        if settings.graphicx_option == '':
            self.graphicx_package = r'\usepackage{graphicx}'
        else:
            self.graphicx_package = (r'\usepackage[%s]{graphicx}' %
                                     settings.graphicx_option)
        # footnotes: TODO: implement LaTeX footnotes
        self.docutils_footnotes = settings.docutils_footnotes

        # Output collection stacks
        # ~~~~~~~~~~~~~~~~~~~~~~~~

        # Document parts
        self.head_prefix = [r'\documentclass[%s]{%s}' %
                            (self.documentoptions,
                             settings.documentclass)]
        self.requirements = SortableDict()  # made a list in depart_document()
        self.requirements['__static'] = r'\usepackage{ifthen}'
        self.latex_preamble = [settings.latex_preamble]
        self.fallbacks = SortableDict()  # made a list in depart_document()
        self.pdfsetup = []  # PDF properties (hyperref package)
        self.title = []
        self.subtitle = []
        self.titledata = []  # \title, \author, \date
        ## self.body_prefix = ['\\begin{document}\n']
        self.body_pre_docinfo = []  # \maketitle
        self.docinfo = []
        self.dedication = []
        self.abstract = []
        self.body = []
        ## self.body_suffix = ['\\end{document}\n']

        self.context = []
        """Heterogeneous stack.

        Used by visit_* and depart_* functions in conjunction with the tree
        traversal. Make sure that the pops correspond to the pushes."""

        # Title metadata:
        self.title_labels = []
        self.subtitle_labels = []
        # (if use_latex_docinfo: collects lists of
        # author/organization/contact/address lines)
        self.author_stack = []
        self.date = []

        # PDF properties: pdftitle, pdfauthor
        self.pdfauthor = []
        self.pdfinfo = []
        if settings.language_code != 'en':
            self.pdfinfo.append('  pdflang={%s},'%settings.language_code)

        # Stack of section counters so that we don't have to use_latex_toc.
        # This will grow and shrink as processing occurs.
        # Initialized for potential first-level sections.
        self._section_number = [0]

        # The current stack of enumerations so that we can expand
        # them into a compound enumeration.
        self._enumeration_counters = []
        # The maximum number of enumeration counters we've used.
        # If we go beyond this number, we need to create a new
        # counter; otherwise, just reuse an old one.
        self._max_enumeration_counters = 0

        self._bibitems = []

        # object for a table while processing.
        self.table_stack = []
        self.active_table = Table(self, 'longtable')

        # Where to collect the output of visitor methods (default: body)
        self.out = self.body
        self.out_stack = []  # stack of output collectors

        # Process settings
        # ~~~~~~~~~~~~~~~~
        # Encodings:
        # Docutils' output-encoding => TeX input encoding
        if self.latex_encoding not in ('ascii', 'unicode', 'utf8'):
            self.requirements['_inputenc'] = (r'\usepackage[%s]{inputenc}'
                                              % self.latex_encoding)
        # TeX font encoding
        if not self.is_xetex:
            if self.font_encoding:
                self.requirements['_fontenc'] = (r'\usepackage[%s]{fontenc}' %
                                                 self.font_encoding)
            # ensure \textquotedbl is defined:
            for enc in self.font_encoding.split(','):
                enc = enc.strip()
                if enc == 'OT1':
                    self.requirements['_textquotedblOT1'] = (
                        r'\DeclareTextSymbol{\textquotedbl}{OT1}{`\"}')
                elif enc not in ('T1', 'T2A', 'T2B', 'T2C', 'T4', 'T5'):
                    self.requirements['_textquotedbl'] = (
                        r'\DeclareTextSymbolDefault{\textquotedbl}{T1}')
        # page layout with typearea (if there are relevant document options)
        if (settings.documentclass.find('scr') == -1
            and (self.documentoptions.find('DIV') != -1
                 or self.documentoptions.find('BCOR') != -1)):
            self.requirements['typearea'] = r'\usepackage{typearea}'

        # Stylesheets
        # (the name `self.stylesheet` is singular because only one
        # stylesheet was supported before Docutils 0.6).
        stylesheet_list = utils.get_stylesheet_list(settings)
        self.fallback_stylesheet = 'docutils' in stylesheet_list
        if self.fallback_stylesheet:
            stylesheet_list.remove('docutils')
            if settings.legacy_class_functions:
                # docutils.sty is incompatible with legacy functions
                self.fallback_stylesheet = False
            else:
                # require a minimal version:
                self.fallbacks['docutils.sty'] = (
                    r'\usepackage{docutils}[2020/08/28]')

        self.stylesheet = [self.stylesheet_call(path)
                           for path in stylesheet_list]

        # PDF setup
        if self.hyperlink_color in ('0', 'false', 'False', ''):
            self.hyperref_options = ''
        else:
            self.hyperref_options = ('colorlinks=true,'
                                     f'linkcolor={self.hyperlink_color},'
                                     f'urlcolor={self.hyperlink_color}')
        if settings.hyperref_options:
            self.hyperref_options += ',' + settings.hyperref_options

        # LaTeX Toc
        # include all supported sections in toc and PDF bookmarks
        # (or use documentclass-default (as currently))?

        # Section numbering
        if settings.sectnum_xform:  # section numbering by Docutils
            PreambleCmds.secnumdepth = r'\setcounter{secnumdepth}{0}'
        else:  # section numbering by LaTeX:
            secnumdepth = settings.sectnum_depth
            # Possible values of settings.sectnum_depth:
            # None  "sectnum" directive without depth arg -> LaTeX default
            #  0    no "sectnum" directive -> no section numbers
            # >0    value of "depth" argument -> translate to LaTeX levels:
            #       -1  part    (0 with "article" document class)
            #        0  chapter (missing in "article" document class)
            #        1  section
            #        2  subsection
            #        3  subsubsection
            #        4  paragraph
            #        5  subparagraph
            if secnumdepth is not None:
                PreambleCmds.secnumdepth = (
                    r'\setcounter{secnumdepth}{%d}'
                    % self.d_class.latex_section_depth(secnumdepth))
            # start with specified number:
            if (hasattr(settings, 'sectnum_start')
                and settings.sectnum_start != 1):
                self.requirements['sectnum_start'] = (
                    r'\setcounter{%s}{%d}' % (self.d_class.sections[0],
                                              settings.sectnum_start-1))
            # TODO: currently ignored (configure in a stylesheet):
            ## settings.sectnum_prefix
            ## settings.sectnum_suffix

    # Auxiliary Methods
    # -----------------

    def stylesheet_call(self, path):
        """Return code to reference or embed stylesheet file `path`"""
        path = Path(path)
        # is it a package (no extension or *.sty) or "normal" tex code:
        is_package = path.suffix in ('.sty', '')
        # Embed content of style file:
        if self.settings.embed_stylesheet:
            if is_package:
                path = path.with_suffix('.sty')  # ensure extension
            try:
                content = path.read_text(encoding='utf-8')
            except OSError as err:
                msg = f'Cannot embed stylesheet:\n {err}'.replace('\\\\', '/')
                self.document.reporter.error(msg)
                return '% ' + msg.replace('\n', '\n% ')
            else:
                self.settings.record_dependencies.add(path.as_posix())
            if is_package:
                # allow '@' in macro names:
                content = (f'\\makeatletter\n{content}\n\\makeatother')
            return (f'% embedded stylesheet: {path.as_posix()}\n'
                    f'{content}')
        # Link to style file:
        if is_package:
            path = path.parent / path.stem  # drop extension
            cmd = r'\usepackage{%s}'
        else:
            cmd = r'\input{%s}'
        if self.settings.stylesheet_path:
            # adapt path relative to output (cf. config.html#stylesheet-path)
            return cmd % utils.relative_path(self.settings._destination, path)
        return cmd % path.as_posix()

    def to_latex_encoding(self, docutils_encoding):
        """Translate docutils encoding name into LaTeX's.

        Default method is remove "-" and "_" chars from docutils_encoding.
        """
        tr = {'iso-8859-1': 'latin1',     # west european
              'iso-8859-2': 'latin2',     # east european
              'iso-8859-3': 'latin3',     # esperanto, maltese
              'iso-8859-4': 'latin4',     # north european
              'iso-8859-5': 'iso88595',   # cyrillic (ISO)
              'iso-8859-9': 'latin5',     # turkish
              'iso-8859-15': 'latin9',    # latin9, update to latin1.
              'mac_cyrillic': 'maccyr',   # cyrillic (on Mac)
              'windows-1251': 'cp1251',   # cyrillic (on Windows)
              'koi8-r': 'koi8-r',         # cyrillic (Russian)
              'koi8-u': 'koi8-u',         # cyrillic (Ukrainian)
              'windows-1250': 'cp1250',   #
              'windows-1252': 'cp1252',   #
              'us-ascii': 'ascii',        # ASCII (US)
              # unmatched encodings
              # '': 'applemac',
              # '': 'ansinew',  # windows 3.1 ansi
              # '': 'ascii',    # ASCII encoding for the range 32--127.
              # '': 'cp437',    # dos latin us
              # '': 'cp850',    # dos latin 1
              # '': 'cp852',    # dos latin 2
              # '': 'decmulti',
              # '': 'latin10',
              # 'iso-8859-6': ''   # arabic
              # 'iso-8859-7': ''   # greek
              # 'iso-8859-8': ''   # hebrew
              # 'iso-8859-10': ''  # latin6, more complete iso-8859-4
              }
        encoding = docutils_encoding.lower()  # normalize case
        encoding = encoding.split(':')[0]     # strip the error handler
        if encoding in tr:
            return tr[encoding]
        # drop HYPHEN or LOW LINE from "latin_1", "utf-8" and similar
        return encoding.replace('_', '').replace('-', '')

    def language_label(self, docutil_label):
        return self.language_module.labels[docutil_label]

    def encode(self, text):
        """Return text with 'problematic' characters escaped.

        * Escape the special printing characters ``# $ % & ~ _ ^ \\ { }``,
          square brackets ``[ ]``, double quotes and (in OT1) ``< | >``.
        * Translate non-supported Unicode characters.
        * Separate ``-`` (and more in literal text) to prevent input ligatures.
        """
        if self.verbatim:
            return text
        # Set up the translation table:
        table = CharMaps.alltt.copy()
        if not self.alltt:
            table.update(CharMaps.special)
        # keep the underscore in citation references
        if self.inside_citation_reference_label and not self.alltt:
            del table[ord('_')]
        # Workarounds for OT1 font-encoding
        if self.font_encoding in ['OT1', ''] and not self.is_xetex:
            # * out-of-order characters in cmtt
            if self.literal:
                # replace underscore by underlined blank,
                # because this has correct width.
                table[ord('_')] = '\\underline{~}'
                # the backslash doesn't work, so we use a mirrored slash.
                # \reflectbox is provided by graphicx:
                self.requirements['graphicx'] = self.graphicx_package
                table[ord('\\')] = '\\reflectbox{/}'
            # * ``< | >`` come out as different chars (except for cmtt):
            else:
                table[ord('|')] = '\\textbar{}'
                table[ord('<')] = '\\textless{}'
                table[ord('>')] = '\\textgreater{}'
        if self.insert_non_breaking_blanks:
            table[ord(' ')] = '~'
            # tab chars may occur in included files (literal or code)
            # quick-and-dirty replacement with spaces
            # (for better results use `--literal-block-env=lstlisting`)
            table[ord('\t')] = '~' * self.settings.tab_width
        # Unicode replacements for 8-bit tex engines (not required with XeTeX)
        if not self.is_xetex:
            if not self.latex_encoding.startswith('utf8'):
                table.update(CharMaps.unsupported_unicode)
                table.update(CharMaps.utf8_supported_unicode)
                table.update(CharMaps.textcomp)
            table.update(CharMaps.pifont)
            # Characters that require a feature/package to render
            for ch in text:
                cp = ord(ch)
                if cp in CharMaps.textcomp and not self.fallback_stylesheet:
                    self.requirements['textcomp'] = PreambleCmds.textcomp
                elif cp in CharMaps.pifont:
                    self.requirements['pifont'] = '\\usepackage{pifont}'
                # preamble-definitions for unsupported Unicode characters
                elif (self.latex_encoding == 'utf8'
                      and cp in CharMaps.unsupported_unicode):
                    self.requirements['_inputenc'+str(cp)] = (
                        '\\DeclareUnicodeCharacter{%04X}{%s}'
                        % (cp, CharMaps.unsupported_unicode[cp]))
        text = text.translate(table)

        # Break up input ligatures e.g. '--' to '-{}-'.
        if not self.is_xetex:  # Not required with xetex/luatex
            separate_chars = '-'
            # In monospace-font, we also separate ',,', '``' and "''" and some
            # other characters which can't occur in non-literal text.
            if self.literal:
                separate_chars += ',`\'"<>'
            for char in separate_chars * 2:
                # Do it twice ("* 2") because otherwise we would replace
                # '---' by '-{}--'.
                text = text.replace(char + char, char + '{}' + char)

        # Literal line breaks (in address or literal blocks):
        if self.insert_newline:
            lines = text.split('\n')
            # Add a protected space to blank lines (except the last)
            # to avoid ``! LaTeX Error: There's no line here to end.``
            for i, line in enumerate(lines[:-1]):
                if not line.lstrip():
                    lines[i] += '~'
            text = (r'\\' + '\n').join(lines)
        if self.literal and not self.insert_non_breaking_blanks:
            # preserve runs of spaces but allow wrapping
            text = text.replace('  ', ' ~')
        return text

    def attval(self, text,
               whitespace=re.compile('[\n\r\t\v\f]')):
        """Cleanse, encode, and return attribute value text."""
        return self.encode(whitespace.sub(' ', text))

    # TODO: is this used anywhere? -> update (use template) or delete
    ## def astext(self):
    ##     """Assemble document parts and return as string."""
    ##     head = '\n'.join(self.head_prefix + self.stylesheet + self.head)
    ##     body = ''.join(self.body_prefix  + self.body + self.body_suffix)
    ##     return head + '\n' + body

    def is_inline(self, node):
        """Check whether a node represents an inline or block-level element"""
        return isinstance(node.parent, nodes.TextElement)

    def append_hypertargets(self, node):
        """Append hypertargets for all ids of `node`"""
        # hypertarget places the anchor at the target's baseline,
        # so we raise it explicitly
        self.out.append('%\n'.join('\\raisebox{1em}{\\hypertarget{%s}{}}' %
                                   id for id in node['ids']))

    def ids_to_labels(self, node, set_anchor=True, protect=False,
                      newline=False):
        """Return list of label definitions for all ids of `node`

        If `set_anchor` is True, an anchor is set with \\phantomsection.
        If `protect` is True, the \\label cmd is made robust.
        If `newline` is True, a newline is added if there are labels.
        """
        prefix = '\\protect' if protect else ''
        labels = [prefix + '\\label{%s}' % id for id in node['ids']]
        if set_anchor and labels:
            labels.insert(0, '\\phantomsection')
        if newline and labels:
            labels.append('\n')
        return labels

    def set_align_from_classes(self, node):
        """Convert ``align-*`` class arguments into alignment args."""
        # separate:
        align = [cls for cls in node['classes'] if cls.startswith('align-')]
        if align:
            node['align'] = align[-1].replace('align-', '')
            node['classes'] = [cls for cls in node['classes']
                               if not cls.startswith('align-')]

    def insert_align_declaration(self, node, default=None):
        align = node.get('align', default)
        if align == 'left':
            self.out.append('\\raggedright\n')
        elif align == 'center':
            self.out.append('\\centering\n')
        elif align == 'right':
            self.out.append('\\raggedleft\n')

    def duclass_open(self, node):
        """Open a group and insert declarations for class values."""
        if not isinstance(node.parent, nodes.compound):
            self.out.append('\n')
        for cls in node['classes']:
            if cls.startswith('language-'):
                language = self.babel.language_name(cls[9:])
                if language:
                    self.babel.otherlanguages[language] = True
                    self.out.append('\\begin{selectlanguage}{%s}\n' % language)
            elif (isinstance(node, nodes.table)
                  and cls in Writer.table_style_values + ['colwidths-given']):
                pass
            else:
                if not self.fallback_stylesheet:
                    self.fallbacks['DUclass'] = PreambleCmds.duclass
                self.out.append('\\begin{DUclass}{%s}\n' % cls)

    def duclass_close(self, node):
        """Close a group of class declarations."""
        for cls in reversed(node['classes']):
            if cls.startswith('language-'):
                language = self.babel.language_name(cls[9:])
                if language:
                    self.out.append('\\end{selectlanguage}\n')
            elif (isinstance(node, nodes.table)
                  and cls in Writer.table_style_values + ['colwidths-given']):
                pass
            else:
                if not self.fallback_stylesheet:
                    self.fallbacks['DUclass'] = PreambleCmds.duclass
                self.out.append('\\end{DUclass}\n')

    def push_output_collector(self, new_out):
        self.out_stack.append(self.out)
        self.out = new_out

    def pop_output_collector(self):
        self.out = self.out_stack.pop()

    def term_postfix(self, node):
        """
        Return LaTeX code required between term or field name and content.

        In a LaTeX "description" environment (used for definition
        lists and non-docinfo field lists), a ``\\leavevmode``
        between an item's label and content ensures the correct
        placement of certain block constructs.
        """
        for child in node:
            if not isinstance(child, (nodes.Invisible, nodes.footnote,
                                      nodes.citation)):
                break
        else:
            return ''
        if isinstance(child, (nodes.container, nodes.compound)):
            return self.term_postfix(child)
        if isinstance(child, nodes.image):
            return '\\leavevmode\n'  # Images get an additional newline.
        if not isinstance(child, (nodes.paragraph, nodes.math_block)):
            return '\\leavevmode'
        return ''

    # Visitor methods
    # ---------------

    def visit_Text(self, node):
        self.out.append(self.encode(node.astext()))

    def depart_Text(self, node):
        pass

    def visit_abbreviation(self, node):
        node['classes'].insert(0, 'abbreviation')
        self.visit_inline(node)

    def depart_abbreviation(self, node):
        self.depart_inline(node)

    def visit_acronym(self, node):
        node['classes'].insert(0, 'acronym')
        self.visit_inline(node)

    def depart_acronym(self, node):
        self.depart_inline(node)

    def visit_address(self, node):
        self.visit_docinfo_item(node, 'address')

    def depart_address(self, node):
        self.depart_docinfo_item(node)

    def visit_admonition(self, node):
        # strip the generic 'admonition' from the list of classes
        node['classes'] = [cls for cls in node['classes']
                           if cls != 'admonition']
        if self.settings.legacy_class_functions:
            self.fallbacks['admonition'] = PreambleCmds.admonition_legacy
            if 'error' in node['classes']:
                self.fallbacks['error'] = PreambleCmds.error_legacy
            self.out.append('\n\\DUadmonition[%s]{'%','.join(node['classes']))
            return
        if not self.fallback_stylesheet:
            self.fallbacks['admonition'] = PreambleCmds.admonition
        if 'error' in node['classes'] and not self.fallback_stylesheet:
            self.fallbacks['error'] = PreambleCmds.error
        self.duclass_open(node)
        self.out.append('\\begin{DUadmonition}')

    def depart_admonition(self, node):
        if self.settings.legacy_class_functions:
            self.out.append('}\n')
            return
        self.out.append('\\end{DUadmonition}\n')
        self.duclass_close(node)

    def visit_author(self, node):
        self.pdfauthor.append(self.attval(node.astext()))
        self.visit_docinfo_item(node, 'author')

    def depart_author(self, node):
        self.depart_docinfo_item(node)

    def visit_authors(self, node):
        # not used: visit_author is called anyway for each author.
        pass

    def depart_authors(self, node):
        pass

    def visit_block_quote(self, node):
        self.duclass_open(node)
        self.out.append('\\begin{quote}')

    def depart_block_quote(self, node):
        self.out.append('\\end{quote}\n')
        self.duclass_close(node)

    def visit_bullet_list(self, node):
        self.duclass_open(node)
        self.out.append('\\begin{itemize}')

    def depart_bullet_list(self, node):
        self.out.append('\\end{itemize}\n')
        self.duclass_close(node)

    def visit_superscript(self, node):
        self.out.append(r'\textsuperscript{')
        self.visit_inline(node)

    def depart_superscript(self, node):
        self.depart_inline(node)
        self.out.append('}')

    def visit_subscript(self, node):
        self.out.append(r'\textsubscript{')
        self.visit_inline(node)

    def depart_subscript(self, node):
        self.depart_inline(node)
        self.out.append('}')

    def visit_caption(self, node):
        self.out.append('\n\\caption{')

    def depart_caption(self, node):
        self.out.append('}\n')

    def visit_title_reference(self, node):
        if not self.fallback_stylesheet:
            self.fallbacks['titlereference'] = PreambleCmds.titlereference
        self.out.append(r'\DUroletitlereference{')
        self.visit_inline(node)

    def depart_title_reference(self, node):
        self.depart_inline(node)
        self.out.append('}')

    def visit_citation(self, node):
        if self.use_latex_citations:
            self.push_output_collector([])
        else:
            # self.requirements['~fnt_floats'] = PreambleCmds.footnote_floats
            self.out.append(r'\begin{figure}[b]')
            self.append_hypertargets(node)

    def depart_citation(self, node):
        if self.use_latex_citations:
            # TODO: normalize label
            label = self.out[0]
            text = ''.join(self.out[1:])
            self._bibitems.append([label, text])
            self.pop_output_collector()
        else:
            self.out.append('\\end{figure}\n')

    def visit_citation_reference(self, node):
        if self.bibtex:
            self._bibitems.append([node.astext()])
        if self.use_latex_citations:
            if not self.inside_citation_reference_label:
                self.out.append(r'\cite{')
                self.inside_citation_reference_label = 1
            else:
                assert self.out[-1] in (' ', '\n'),\
                        'unexpected non-whitespace while in reference label'
                del self.out[-1]
        else:
            href = ''
            if 'refid' in node:
                href = node['refid']
            elif 'refname' in node:
                href = self.document.nameids[node['refname']]
            self.out.append('\\hyperlink{%s}{[' % href)

    def depart_citation_reference(self, node):
        # TODO: normalize labels
        if self.use_latex_citations:
            followup_citation = False
            # check for a following citation separated by a space or newline
            sibling = node.next_node(descend=False, siblings=True)
            if (isinstance(sibling, nodes.Text)
                and sibling.astext() in (' ', '\n')):
                sibling2 = sibling.next_node(descend=False, siblings=True)
                if isinstance(sibling2, nodes.citation_reference):
                    followup_citation = True
            if followup_citation:
                self.out.append(',')
            else:
                self.out.append('}')
                self.inside_citation_reference_label = False
        else:
            self.out.append(']}')

    def visit_classifier(self, node):
        self.out.append('(\\textbf{')

    def depart_classifier(self, node):
        self.out.append('})')

    def visit_colspec(self, node):
        self.active_table.visit_colspec(node)

    def depart_colspec(self, node):
        pass

    def visit_comment(self, node):
        if not isinstance(node.parent, nodes.compound):
            self.out.append('\n')
        # Precede every line with a comment sign, wrap in newlines
        self.out.append('%% %s\n' % node.astext().replace('\n', '\n% '))
        raise nodes.SkipNode

    def depart_comment(self, node):
        pass

    def visit_compound(self, node):
        if isinstance(node.parent, nodes.compound):
            self.out.append('\n')
        node['classes'].insert(0, 'compound')
        self.duclass_open(node)

    def depart_compound(self, node):
        self.duclass_close(node)

    def visit_contact(self, node):
        self.visit_docinfo_item(node, 'contact')

    def depart_contact(self, node):
        self.depart_docinfo_item(node)

    def visit_container(self, node):
        self.duclass_open(node)

    def depart_container(self, node):
        self.duclass_close(node)

    def visit_copyright(self, node):
        self.visit_docinfo_item(node, 'copyright')

    def depart_copyright(self, node):
        self.depart_docinfo_item(node)

    def visit_date(self, node):
        self.visit_docinfo_item(node, 'date')

    def depart_date(self, node):
        self.depart_docinfo_item(node)

    def visit_decoration(self, node):
        # header and footer
        pass

    def depart_decoration(self, node):
        pass

    def visit_definition(self, node):
        pass

    def depart_definition(self, node):
        self.out.append('\n')                # TODO: just pass?

    def visit_definition_list(self, node):
        self.duclass_open(node)
        self.out.append('\\begin{description}\n')

    def depart_definition_list(self, node):
        self.out.append('\\end{description}\n')
        self.duclass_close(node)

    def visit_definition_list_item(self, node):
        pass

    def depart_definition_list_item(self, node):
        pass

    def visit_description(self, node):
        self.out.append(' ')

    def depart_description(self, node):
        pass

    def visit_docinfo(self, node):
        self.push_output_collector(self.docinfo)

    def depart_docinfo(self, node):
        self.pop_output_collector()
        # Some itmes (e.g. author) end up at other places
        if self.docinfo:
            # tabularx: automatic width of columns, no page breaks allowed.
            self.requirements['tabularx'] = r'\usepackage{tabularx}'
            if not self.fallback_stylesheet:
                self.fallbacks['_providelength'] = PreambleCmds.providelength
                self.fallbacks['docinfo'] = PreambleCmds.docinfo
            #
            self.docinfo.insert(0, '\n% Docinfo\n'
                                '\\begin{center}\n'
                                '\\begin{tabularx}{\\DUdocinfowidth}{lX}\n')
            self.docinfo.append('\\end{tabularx}\n'
                                '\\end{center}\n')

    def visit_docinfo_item(self, node, name):
        if self.use_latex_docinfo:
            if name in ('author', 'organization', 'contact', 'address'):
                # We attach these to the last author.  If any of them precedes
                # the first author, put them in a separate "author" group
                # (in lack of better semantics).
                if name == 'author' or not self.author_stack:
                    self.author_stack.append([])
                if name == 'address':   # newlines are meaningful
                    self.insert_newline = True
                    text = self.encode(node.astext())
                    self.insert_newline = False
                else:
                    text = self.attval(node.astext())
                self.author_stack[-1].append(text)
                raise nodes.SkipNode
            elif name == 'date':
                self.date.append(self.attval(node.astext()))
                raise nodes.SkipNode
        self.out.append('\\textbf{%s}: &\n\t' % self.language_label(name))
        if name == 'address':
            self.insert_newline = True
            self.out.append('{\\raggedright\n')
            self.context.append(' } \\\\\n')
        else:
            self.context.append(' \\\\\n')

    def depart_docinfo_item(self, node):
        self.out.append(self.context.pop())
        # for address we did set insert_newline
        self.insert_newline = False

    def visit_doctest_block(self, node):
        self.visit_literal_block(node)

    def depart_doctest_block(self, node):
        self.depart_literal_block(node)

    def visit_document(self, node):
        # titled document?
        if (self.use_latex_docinfo or len(node)
            and isinstance(node[0], nodes.title)):
            protect = (self.settings.documentclass == 'memoir')
            self.title_labels += self.ids_to_labels(node, set_anchor=False,
                                                    protect=protect)

    def depart_document(self, node):
        # Complete "parts" with information gained from walkabout
        # * language setup
        if (self.babel.otherlanguages
            or self.babel.language not in ('', 'english')):
            self.requirements['babel'] = self.babel()
        # * conditional requirements (before style sheet)
        self.requirements = self.requirements.sortedvalues()
        # * coditional fallback definitions (after style sheet)
        self.fallbacks = self.fallbacks.sortedvalues()
        # * PDF properties
        self.pdfsetup.append(PreambleCmds.linking % self.hyperref_options)
        if self.pdfauthor:
            authors = self.author_separator.join(self.pdfauthor)
            self.pdfinfo.append('  pdfauthor={%s}' % authors)
        if self.pdfinfo:
            self.pdfsetup += [r'\hypersetup{'] + self.pdfinfo + ['}']
        # * title (including author(s) and date if using "latex_docinfo")
        if self.title or (self.use_latex_docinfo
                          and (self.author_stack or self.date)):
            self.make_title()  # see below
        # * bibliography
        if self._bibitems:
            self.append_bibliogaphy()  # see below
        # * make sure to generate a toc file if needed for local contents:
        if 'minitoc' in self.requirements and not self.has_latex_toc:
            self.out.append('\n\\faketableofcontents % for local ToCs\n')

    def make_title(self):
        # Auxiliary function called by `self.depart_document()`.
        #
        # Append ``\title``, ``\author``, and ``\date`` to "titledata".
        # (We need all three, even if empty, to prevent errors
        # and/or automatic display of the current date by \maketitle.)
        # Append ``\maketitle`` to "body_pre_docinfo" parts.
        #
        # \title
        title_arg = [''.join(self.title)]  # ensure len == 1
        if self.title:
            title_arg += self.title_labels
        if self.subtitle:
            title_arg += [r'\\',
                          r'\DUdocumentsubtitle{%s}' % ''.join(self.subtitle),
                          ] + self.subtitle_labels
        self.titledata.append(r'\title{%s}' % '%\n  '.join(title_arg))
        # \author
        author_arg = ['\\\\\n'.join(author_entry)
                      for author_entry in self.author_stack]
        self.titledata.append(r'\author{%s}' %
                              ' \\and\n'.join(author_arg))
        # \date
        self.titledata.append(r'\date{%s}' % ', '.join(self.date))
        # \maketitle
        # Must be in the document body. We add it to `body_pre_docinfo`
        # to allow templates to put `titledata` into the document preamble.
        self.body_pre_docinfo.append('\\maketitle\n')

    def append_bibliogaphy(self):
        # Add bibliography at end of document.
        # TODO insertion point should be configurable.
        # Auxiliary function called by `depart_document`.
        if self.bibtex:
            self.out.append('\n\\bibliographystyle{%s}\n' % self.bibtex[0])
            self.out.append('\\bibliography{%s}\n' % ','.join(self.bibtex[1:]))
        elif self.use_latex_citations:
            # TODO: insert citations at point of definition.
            widest_label = ''
            for bibitem in self._bibitems:
                if len(widest_label) < len(bibitem[0]):
                    widest_label = bibitem[0]
            self.out.append('\n\\begin{thebibliography}{%s}\n' %
                            widest_label)
            for bibitem in self._bibitems:
                # cite_key: underscores must not be escaped
                cite_key = bibitem[0].replace(r'\_', '_')
                self.out.append('\\bibitem[%s]{%s}{%s}\n' %
                                (bibitem[0], cite_key, bibitem[1]))
            self.out.append('\\end{thebibliography}\n')

    def visit_emphasis(self, node):
        self.out.append('\\emph{')
        self.visit_inline(node)

    def depart_emphasis(self, node):
        self.depart_inline(node)
        self.out.append('}')

    # Append column delimiters and advance column counter,
    # if the current cell is a multi-row continuation."""
    def insert_additional_table_colum_delimiters(self):
        while self.active_table.get_rowspan(
                                self.active_table.get_entry_number()):
            self.out.append(' & ')
            self.active_table.visit_entry()  # increment cell count

    def visit_entry(self, node):
        # cell separation
        if self.active_table.get_entry_number() == 0:
            self.insert_additional_table_colum_delimiters()
        else:
            self.out.append(' & ')

        # multirow, multicolumn
        if 'morerows' in node and 'morecols' in node:
            raise NotImplementedError('Cells that span multiple rows *and* '
                                      'columns currently not supported '
                                      'by the LaTeX writer')
            # TODO: should be possible with LaTeX, see e.g.
            # http://texblog.org/2012/12/21/multi-column-and-multi-row-cells-in-latex-tables/
        # multirow in LaTeX simply will enlarge the cell over several rows
        # (the following n if n is positive, the former if negative).
        if 'morerows' in node:
            self.requirements['multirow'] = r'\usepackage{multirow}'
            mrows = node['morerows'] + 1
            self.active_table.set_rowspan(
                            self.active_table.get_entry_number(), mrows)
            self.out.append('\\multirow{%d}{%s}{' %
                            (mrows, self.active_table.get_column_width()))
            self.context.append('}')
        elif 'morecols' in node:
            # the vertical bar before column is missing if it is the first
            # column. the one after always.
            if self.active_table.get_entry_number() == 0:
                bar1 = self.active_table.get_vertical_bar()
            else:
                bar1 = ''
            mcols = node['morecols'] + 1
            self.out.append('\\multicolumn{%d}{%s%s%s}{' %
                            (mcols,
                             bar1,
                             self.active_table.get_multicolumn_width(
                                 self.active_table.get_entry_number(), mcols),
                             self.active_table.get_vertical_bar()))
            self.context.append('}')
        else:
            self.context.append('')

        # bold header/stub-column
        if len(node) and (isinstance(node.parent.parent, nodes.thead)
                          or self.active_table.is_stub_column()):
            self.out.append('\\textbf{')
            self.context.append('}')
        else:
            self.context.append('')

        # if line ends with '{', mask line break
        if (not self.active_table.colwidths_auto
            and self.out[-1].endswith("{")
            and node.astext()):
            self.out.append("%")

        self.active_table.visit_entry()  # increment cell count

    def depart_entry(self, node):
        self.out.append(self.context.pop())  # header / not header
        self.out.append(self.context.pop())  # multirow/column
        # insert extra "&"s, if following rows are spanned from above:
        self.insert_additional_table_colum_delimiters()

    def visit_row(self, node):
        self.active_table.visit_row()

    def depart_row(self, node):
        self.out.extend(self.active_table.depart_row())

    def visit_enumerated_list(self, node):
        # enumeration styles:
        types = {'': '',
                 'arabic': 'arabic',
                 'loweralpha': 'alph',
                 'upperalpha': 'Alph',
                 'lowerroman': 'roman',
                 'upperroman': 'Roman'}
        # default LaTeX enumeration labels:
        default_labels = [
                          # (präfix, enumtype, suffix)
                          ('',  'arabic', '.'),  # 1.
                          ('(', 'alph',   ')'),  # (a)
                          ('',  'roman',  '.'),  # i.
                          ('',  'Alph',   '.')]  # A.

        prefix = ''
        if self.compound_enumerators:
            if (self.section_prefix_for_enumerators and self.section_level
                and not self._enumeration_counters):
                prefix = '.'.join(str(n) for n in
                                  self._section_number[:self.section_level]
                                  ) + self.section_enumerator_separator
            if self._enumeration_counters:
                prefix += self._enumeration_counters[-1]
        prefix += node.get('prefix', '')
        enumtype = types[node.get('enumtype', 'arabic')]
        suffix = node.get('suffix', '.')

        enum_level = len(self._enumeration_counters)+1
        counter_name = 'enum' + roman.toRoman(enum_level).lower()
        label = r'%s\%s{%s}%s' % (prefix, enumtype, counter_name, suffix)
        self._enumeration_counters.append(label)

        self.duclass_open(node)
        if enum_level <= 4:
            self.out.append('\\begin{enumerate}')
            if (prefix, enumtype, suffix) != default_labels[enum_level-1]:
                self.out.append('\n\\renewcommand{\\label%s}{%s}' %
                                (counter_name, label))
        else:
            self.fallbacks[counter_name] = '\\newcounter{%s}' % counter_name
            self.out.append('\\begin{list}')
            self.out.append('{%s}' % label)
            self.out.append('{\\usecounter{%s}}' % counter_name)
        if 'start' in node:
            self.out.append('\n\\setcounter{%s}{%d}' %
                            (counter_name, node['start']-1))

    def depart_enumerated_list(self, node):
        if len(self._enumeration_counters) <= 4:
            self.out.append('\\end{enumerate}\n')
        else:
            self.out.append('\\end{list}\n')
        self.duclass_close(node)
        self._enumeration_counters.pop()

    def visit_field(self, node):
        # output is done in field_body, field_name
        pass

    def depart_field(self, node):
        pass

    def visit_field_body(self, node):
        if not isinstance(node.parent.parent, nodes.docinfo):
            self.out.append(self.term_postfix(node))

    def depart_field_body(self, node):
        if self.out is self.docinfo:
            self.out.append(r'\\'+'\n')

    def visit_field_list(self, node):
        self.duclass_open(node)
        if self.out is not self.docinfo:
            if not self.fallback_stylesheet:
                self.fallbacks['fieldlist'] = PreambleCmds.fieldlist
            self.out.append('\\begin{DUfieldlist}')

    def depart_field_list(self, node):
        if self.out is not self.docinfo:
            self.out.append('\\end{DUfieldlist}\n')
        self.duclass_close(node)

    def visit_field_name(self, node):
        if self.out is self.docinfo:
            self.out.append('\\textbf{')
        else:
            # Commands with optional args inside an optional arg must be put
            # in a group, e.g. ``\item[{\hyperref[label]{text}}]``.
            self.out.append('\n\\item[{')

    def depart_field_name(self, node):
        if self.out is self.docinfo:
            self.out.append('}: &')
        else:
            self.out.append(':}]')

    def visit_figure(self, node):
        self.requirements['float'] = PreambleCmds.float
        self.duclass_open(node)
        # The 'align' attribute sets the "outer alignment",
        # for "inner alignment" use LaTeX default alignment (similar to HTML)
        alignment = node.attributes.get('align', 'center')
        if alignment != 'center':
            # The LaTeX "figure" environment always uses the full linewidth,
            # so "outer alignment" is ignored. Just write a comment.
            # TODO: use the wrapfigure environment?
            self.out.append('\\begin{figure} %% align = "%s"\n' % alignment)
        else:
            self.out.append('\\begin{figure}\n')
        self.out += self.ids_to_labels(node, newline=True)

    def depart_figure(self, node):
        self.out.append('\\end{figure}\n')
        self.duclass_close(node)

    def visit_footer(self, node):
        self.push_output_collector([])
        self.out.append(r'\newcommand{\DUfooter}{')

    def depart_footer(self, node):
        self.out.append('}')
        self.requirements['~footer'] = ''.join(self.out)
        self.pop_output_collector()

    def visit_footnote(self, node):
        try:
            backref = node['backrefs'][0]
        except IndexError:
            backref = node['ids'][0]  # no backref, use self-ref instead
        if self.docutils_footnotes:
            if not self.fallback_stylesheet:
                self.fallbacks['footnotes'] = PreambleCmds.footnotes
            num = node[0].astext()
            if self.settings.footnote_references == 'brackets':
                num = '[%s]' % num
            self.out.append('%%\n\\DUfootnotetext{%s}{%s}{%s}{' %
                            (node['ids'][0], backref, self.encode(num)))
            if node['ids'] == node['names']:
                self.out += self.ids_to_labels(node)
            # prevent spurious whitespace if footnote starts with paragraph:
            if len(node) > 1 and isinstance(node[1], nodes.paragraph):
                self.out.append('%')
        # TODO: "real" LaTeX \footnote{}s (see visit_footnotes_reference())

    def depart_footnote(self, node):
        self.out.append('}\n')

    def visit_footnote_reference(self, node):
        href = ''
        if 'refid' in node:
            href = node['refid']
        elif 'refname' in node:
            href = self.document.nameids[node['refname']]
        # if not self.docutils_footnotes:
        #     # TODO: insert footnote content at (or near) this place
        #     #       see also docs/dev/todo.txt
        #     try:
        #         referenced_node = self.document.ids[node['refid']]
        #     except (AttributeError, KeyError):
        #         self.document.reporter.error(
        #             'unresolved footnote-reference %s' % node)
        #     print('footnote-ref to %s' % referenced_node)
        format = self.settings.footnote_references
        if format == 'brackets':
            self.append_hypertargets(node)
            self.out.append('\\hyperlink{%s}{[' % href)
            self.context.append(']}')
        else:
            if not self.fallback_stylesheet:
                self.fallbacks['footnotes'] = PreambleCmds.footnotes
            self.out.append(r'\DUfootnotemark{%s}{%s}{' %
                            (node['ids'][0], href))
            self.context.append('}')

    def depart_footnote_reference(self, node):
        self.out.append(self.context.pop())

    # footnote/citation label
    def label_delim(self, node, bracket, superscript):
        if isinstance(node.parent, nodes.footnote):
            raise nodes.SkipNode
        else:
            assert isinstance(node.parent, nodes.citation)
            if not self.use_latex_citations:
                self.out.append(bracket)

    def visit_label(self, node):
        """footnote or citation label: in brackets or as superscript"""
        self.label_delim(node, '[', '\\textsuperscript{')

    def depart_label(self, node):
        self.label_delim(node, ']', '}')

    # elements generated by the framework e.g. section numbers.
    def visit_generated(self, node):
        pass

    def depart_generated(self, node):
        pass

    def visit_header(self, node):
        self.push_output_collector([])
        self.out.append(r'\newcommand{\DUheader}{')

    def depart_header(self, node):
        self.out.append('}')
        self.requirements['~header'] = ''.join(self.out)
        self.pop_output_collector()

    def to_latex_length(self, length_str, pxunit=None):
        """Convert `length_str` with rst length to LaTeX length
        """
        if pxunit is not None:
            warnings.warn(
                'The optional argument `pxunit` '
                'of LaTeXTranslator.to_latex_length() is ignored '
                'and will be removed in Docutils 0.21 or later',
                DeprecationWarning, stacklevel=2)
        match = re.match(r'(\d*\.?\d*)\s*(\S*)', length_str)
        if not match:
            return length_str
        value, unit = match.groups()[:2]
        # no unit or "DTP" points (called 'bp' in TeX):
        if unit in ('', 'pt'):
            length_str = '%sbp' % value
        # percentage: relate to current line width
        elif unit == '%':
            length_str = '%.3f\\linewidth' % (float(value)/100.0)
        elif self.is_xetex and unit == 'px':
            # XeTeX does not know the length unit px.
            # Use \pdfpxdimen, the macro to set the value of 1 px in pdftex.
            # This way, configuring works the same for pdftex and xetex.
            if not self.fallback_stylesheet:
                self.fallbacks['_providelength'] = PreambleCmds.providelength
            self.fallbacks['px'] = '\n\\DUprovidelength{\\pdfpxdimen}{1bp}\n'
            length_str = r'%s\pdfpxdimen' % value
        return length_str

    def visit_image(self, node):
        self.requirements['graphicx'] = self.graphicx_package
        attrs = node.attributes
        # Convert image URI to a local file path
        imagepath = url2pathname(attrs['uri']).replace('\\', '/')
        # alignment defaults:
        if 'align' not in attrs:
            # Set default align of image in a figure to 'center'
            if isinstance(node.parent, nodes.figure):
                attrs['align'] = 'center'
            self.set_align_from_classes(node)
        # pre- and postfix (prefix inserted in reverse order)
        pre = []
        post = []
        include_graphics_options = []
        align_codes = {
            # inline images: by default latex aligns the bottom.
            'bottom': ('', ''),
            'middle': (r'\raisebox{-0.5\height}{', '}'),
            'top':    (r'\raisebox{-\height}{', '}'),
            # block level images:
            'center': (r'\noindent\makebox[\linewidth][c]{', '}'),
            'left':   (r'\noindent{', r'\hfill}'),
            'right':  (r'\noindent{\hfill', '}'),
            }
        if 'align' in attrs:
            # TODO: warn or ignore non-applicable alignment settings?
            try:
                align_code = align_codes[attrs['align']]
                pre.append(align_code[0])
                post.append(align_code[1])
            except KeyError:
                pass                    # TODO: warn?
        if 'height' in attrs:
            include_graphics_options.append(
                'height=%s' % self.to_latex_length(attrs['height']))
        if 'scale' in attrs:
            include_graphics_options.append(
                'scale=%f' % (attrs['scale'] / 100.0))
        if 'width' in attrs:
            include_graphics_options.append(
                'width=%s' % self.to_latex_length(attrs['width']))
        if not (self.is_inline(node)
                or isinstance(node.parent, (nodes.figure, nodes.compound))):
            pre.append('\n')
        if not (self.is_inline(node)
                or isinstance(node.parent, nodes.figure)):
            post.append('\n')
        pre.reverse()
        self.out.extend(pre)
        options = ''
        if include_graphics_options:
            options = '[%s]' % (','.join(include_graphics_options))
        self.out.append('\\includegraphics%s{%s}' % (options, imagepath))
        self.out.extend(post)

    def depart_image(self, node):
        self.out += self.ids_to_labels(node, newline=True)

    def visit_inline(self, node):  # <span>, i.e. custom roles
        for cls in node['classes']:
            if cls.startswith('language-'):
                language = self.babel.language_name(cls[9:])
                if language:
                    self.babel.otherlanguages[language] = True
                    self.out.append(r'\foreignlanguage{%s}{' % language)
            else:
                if not self.fallback_stylesheet:
                    self.fallbacks['inline'] = PreambleCmds.inline
                self.out.append(r'\DUrole{%s}{' % cls)

    def depart_inline(self, node):
        self.out.append('}' * len(node['classes']))

    def visit_legend(self, node):
        if not self.fallback_stylesheet:
            self.fallbacks['legend'] = PreambleCmds.legend
        self.out.append('\\begin{DUlegend}')

    def depart_legend(self, node):
        self.out.append('\\end{DUlegend}\n')

    def visit_line(self, node):
        self.out.append(r'\item[] ')

    def depart_line(self, node):
        self.out.append('\n')

    def visit_line_block(self, node):
        if not self.fallback_stylesheet:
            self.fallbacks['_providelength'] = PreambleCmds.providelength
            self.fallbacks['lineblock'] = PreambleCmds.lineblock
        self.set_align_from_classes(node)
        if isinstance(node.parent, nodes.line_block):
            self.out.append('\\item[]\n'
                            '\\begin{DUlineblock}{\\DUlineblockindent}\n')
            # nested line-blocks cannot be given class arguments
        else:
            self.duclass_open(node)
            self.out.append('\\begin{DUlineblock}{0em}\n')
            self.insert_align_declaration(node)

    def depart_line_block(self, node):
        self.out.append('\\end{DUlineblock}\n')
        self.duclass_close(node)

    def visit_list_item(self, node):
        self.out.append('\n\\item ')

    def depart_list_item(self, node):
        pass

    def visit_literal(self, node):
        self.literal = True
        if ('code' in node['classes']
            and self.settings.syntax_highlight != 'none'):
            self.requirements['color'] = PreambleCmds.color
            if not self.fallback_stylesheet:
                self.fallbacks['code'] = PreambleCmds.highlight_rules
        self.out.append('\\texttt{')
        self.visit_inline(node)

    def depart_literal(self, node):
        self.literal = False
        self.depart_inline(node)
        self.out.append('}')

    # Literal blocks are used for '::'-prefixed literal-indented
    # blocks of text, where the inline markup is not recognized,
    # but are also the product of the "parsed-literal" directive,
    # where the markup is respected.
    #
    # In both cases, we want to use a typewriter/monospaced typeface.
    # For "real" literal-blocks, we can use \verbatim, while for all
    # the others we must use \ttfamily and \raggedright.
    #
    # We can distinguish between the two kinds by the number of
    # siblings that compose this node: if it is composed by a
    # single element, it's either
    # * a real one,
    # * a parsed-literal that does not contain any markup, or
    # * a parsed-literal containing just one markup construct.
    def is_plaintext(self, node):
        """Check whether a node can be typeset verbatim"""
        return (len(node) == 1) and isinstance(node[0], nodes.Text)

    def visit_literal_block(self, node):
        """Render a literal block.

        Corresponding rST elements: literal block, parsed-literal, code.
        """
        packages = {'lstlisting':  r'\usepackage{listings}' '\n'
                                   r'\lstset{xleftmargin=\leftmargin}',
                    'listing': r'\usepackage{moreverb}',
                    'Verbatim': r'\usepackage{fancyvrb}',
                    'verbatimtab': r'\usepackage{moreverb}'}

        literal_env = self.literal_block_env

        # Check, if it is possible to use a literal-block environment
        _plaintext = self.is_plaintext(node)
        _in_table = self.active_table.is_open()
        # TODO: fails if normal text precedes the literal block.
        #       Check parent node instead?
        _autowidth_table = _in_table and self.active_table.colwidths_auto
        _no_env_nodes = (nodes.footnote, nodes.sidebar)
        if self.settings.legacy_class_functions:
            _no_env_nodes += (nodes.admonition, nodes.system_message)
        _use_env = _plaintext and not isinstance(node.parent, _no_env_nodes)
        _use_listings = (literal_env == 'lstlisting') and _use_env

        # Labels and classes:
        self.duclass_open(node)
        self.out += self.ids_to_labels(node, newline=True)
        # Highlight code?
        if (not _plaintext
            and 'code' in node['classes']
            and self.settings.syntax_highlight != 'none'):
            self.requirements['color'] = PreambleCmds.color
            if not self.fallback_stylesheet:
                self.fallbacks['code'] = PreambleCmds.highlight_rules
        # Wrap?
        if _in_table and _use_env and not _autowidth_table:
            # Wrap in minipage to prevent extra vertical space
            # with alltt and verbatim-like environments:
            self.fallbacks['ttem'] = PreambleCmds.ttem
            self.out.append(
                '\\begin{minipage}{%d\\ttemwidth}\n' %
                (max(len(line) for line in node.astext().split('\n'))))
            self.context.append('\n\\end{minipage}\n')
        elif not _in_table and not _use_listings:
            # Wrap in quote to set off vertically and indent
            self.out.append('\\begin{quote}\n')
            self.context.append('\n\\end{quote}\n')
        else:
            self.context.append('\n')

        # Use verbatim-like environment, if defined and possible
        # (in an auto-width table, only listings works):
        if literal_env and _use_env and (not _autowidth_table
                                         or _use_listings):
            try:
                self.requirements['literal_block'] = packages[literal_env]
            except KeyError:
                pass
            self.verbatim = True
            if _in_table and _use_listings:
                self.out.append('\\lstset{xleftmargin=0pt}\n')
            self.out.append('\\begin{%s}%s\n' %
                            (literal_env, self.literal_block_options))
            self.context.append('\n\\end{%s}' % literal_env)
        elif _use_env and not _autowidth_table:
            self.alltt = True
            self.requirements['alltt'] = r'\usepackage{alltt}'
            self.out.append('\\begin{alltt}\n')
            self.context.append('\n\\end{alltt}')
        else:
            self.literal = True
            self.insert_newline = True
            self.insert_non_breaking_blanks = True
            # \raggedright ensures leading blanks are respected but
            # leads to additional leading vspace if the first line
            # of the block is overfull :-(
            self.out.append('\\ttfamily\\raggedright\n')
            self.context.append('')

    def depart_literal_block(self, node):
        self.insert_non_breaking_blanks = False
        self.insert_newline = False
        self.literal = False
        self.verbatim = False
        self.alltt = False
        self.out.append(self.context.pop())
        self.out.append(self.context.pop())
        self.duclass_close(node)

    def visit_meta(self, node):
        name = node.attributes.get('name')
        content = node.attributes.get('content')
        if not name or not content:
            return
        if name in ('author', 'creator', 'keywords', 'subject', 'title'):
            # fields with dedicated hyperref options:
            self.pdfinfo.append('  pdf%s={%s},'%(name, content))
        elif name == 'producer':
            self.pdfinfo.append('  addtopdfproducer={%s},'%content)
        else:
            # generic interface (case sensitive!)
            # TODO: filter irrelevant nodes ("http-equiv", ...)?
            self.pdfinfo.append('  pdfinfo={%s={%s}},'%(name, content))

    def depart_meta(self, node):
        pass

    def visit_math(self, node, math_env='$'):
        """math role"""
        self.visit_inline(node)
        self.requirements['amsmath'] = r'\usepackage{amsmath}'
        math_code = node.astext().translate(unichar2tex.uni2tex_table)
        if math_env == '$':
            if self.alltt:
                wrapper = ['\\(', '\\)']
            else:
                wrapper = ['$', '$']
        else:
            labels = self.ids_to_labels(node, set_anchor=False, newline=True)
            wrapper = ['%%\n\\begin{%s}\n' % math_env,
                       '\n',
                       ''.join(labels),
                       '\\end{%s}' % math_env]
        wrapper.insert(1, math_code)
        self.out.extend(wrapper)
        self.depart_inline(node)
        # Content already processed:
        raise nodes.SkipNode

    def depart_math(self, node):
        pass  # never reached

    def visit_math_block(self, node):
        math_env = pick_math_environment(node.astext())
        self.visit_math(node, math_env=math_env)

    def depart_math_block(self, node):
        pass  # never reached

    def visit_option(self, node):
        if self.context[-1]:
            # this is not the first option
            self.out.append(', ')

    def depart_option(self, node):
        # flag that the first option is done.
        self.context[-1] += 1

    def visit_option_argument(self, node):
        """Append the delimiter between an option and its argument to body."""
        self.out.append(node.get('delimiter', ' '))

    def depart_option_argument(self, node):
        pass

    def visit_option_group(self, node):
        self.out.append('\n\\item[')
        # flag for first option
        self.context.append(0)

    def depart_option_group(self, node):
        self.context.pop()  # the flag
        self.out.append('] ')

    def visit_option_list(self, node):
        if not self.fallback_stylesheet:
            self.fallbacks['_providelength'] = PreambleCmds.providelength
            self.fallbacks['optionlist'] = PreambleCmds.optionlist
        self.duclass_open(node)
        self.out.append('\\begin{DUoptionlist}')

    def depart_option_list(self, node):
        self.out.append('\\end{DUoptionlist}\n')
        self.duclass_close(node)

    def visit_option_list_item(self, node):
        pass

    def depart_option_list_item(self, node):
        pass

    def visit_option_string(self, node):
        ## self.out.append(self.starttag(node, 'span', '', CLASS='option'))
        pass

    def depart_option_string(self, node):
        ## self.out.append('</span>')
        pass

    def visit_organization(self, node):
        self.visit_docinfo_item(node, 'organization')

    def depart_organization(self, node):
        self.depart_docinfo_item(node)

    def visit_paragraph(self, node):
        # insert blank line, unless
        # * the paragraph is first in a list item, compound, or container
        # * follows a non-paragraph node in a compound,
        # * is in a table with auto-width columns
        index = node.parent.index(node)
        if index == 0 and isinstance(node.parent,
                                     (nodes.list_item, nodes.description,
                                      nodes.compound, nodes.container)):
            pass
        elif (index > 0
              and isinstance(node.parent, nodes.compound)
              and not isinstance(node.parent[index - 1],
                                 (nodes.paragraph, nodes.compound))):
            pass
        elif self.active_table.colwidths_auto:
            if index == 1:  # second paragraph
                self.warn('LaTeX merges paragraphs in tables '
                          'with auto-sized columns!', base_node=node)
            if index > 0:
                self.out.append('\n')
        else:
            self.out.append('\n')
        self.out += self.ids_to_labels(node, newline=True)
        self.visit_inline(node)

    def depart_paragraph(self, node):
        self.depart_inline(node)
        if not self.active_table.colwidths_auto:
            self.out.append('\n')

    def visit_problematic(self, node):
        self.requirements['color'] = PreambleCmds.color
        self.out.append('%\n')
        self.append_hypertargets(node)
        self.out.append(r'\hyperlink{%s}{\textbf{\color{red}' % node['refid'])

    def depart_problematic(self, node):
        self.out.append('}}')

    def visit_raw(self, node):
        if 'latex' not in node.get('format', '').split():
            raise nodes.SkipNode
        if not (self.is_inline(node)
                or isinstance(node.parent, nodes.compound)):
            self.out.append('\n')
        self.visit_inline(node)
        # append "as-is" skipping any LaTeX-encoding
        self.verbatim = True

    def depart_raw(self, node):
        self.verbatim = False
        self.depart_inline(node)
        if not self.is_inline(node):
            self.out.append('\n')

    def has_unbalanced_braces(self, string):
        """Test whether there are unmatched '{' or '}' characters."""
        level = 0
        for ch in string:
            if ch == '{':
                level += 1
            if ch == '}':
                level -= 1
            if level < 0:
                return True
        return level != 0

    def visit_reference(self, node):
        # We need to escape #, \, and % if we use the URL in a command.
        special_chars = {ord('#'): '\\#',
                         ord('%'): '\\%',
                         ord('\\'): '\\\\',
                         }
        # external reference (URL)
        if 'refuri' in node:
            href = str(node['refuri']).translate(special_chars)
            # problematic chars double caret and unbalanced braces:
            if href.find('^^') != -1 or self.has_unbalanced_braces(href):
                self.error(
                    'External link "%s" not supported by LaTeX.\n'
                    ' (Must not contain "^^" or unbalanced braces.)' % href)
            if node['refuri'] == node.astext():
                self.out.append(r'\url{%s}' % href)
                raise nodes.SkipNode
            self.out.append(r'\href{%s}{' % href)
            return
        # internal reference
        if 'refid' in node:
            href = node['refid']
        elif 'refname' in node:
            href = self.document.nameids[node['refname']]
        else:
            raise AssertionError('Unknown reference.')
        if not self.is_inline(node):
            self.out.append('\n')
        self.out.append('\\hyperref[%s]{' % href)
        if self._reference_label:
            self.out.append('\\%s{%s}}' %
                            (self._reference_label, href.replace('#', '')))
            raise nodes.SkipNode

    def depart_reference(self, node):
        self.out.append('}')
        if not self.is_inline(node):
            self.out.append('\n')

    def visit_revision(self, node):
        self.visit_docinfo_item(node, 'revision')

    def depart_revision(self, node):
        self.depart_docinfo_item(node)

    def visit_rubric(self, node):
        if not self.fallback_stylesheet:
            self.fallbacks['rubric'] = PreambleCmds.rubric
        # class wrapper would interfere with ``\section*"`` type commands
        # (spacing/indent of first paragraph)
        self.out.append('\n\\DUrubric{')

    def depart_rubric(self, node):
        self.out.append('}\n')

    def visit_section(self, node):
        self.section_level += 1
        # Initialize counter for potential subsections:
        self._section_number.append(0)
        # Counter for this section's level (initialized by parent section):
        self._section_number[self.section_level - 1] += 1

    def depart_section(self, node):
        # Remove counter for potential subsections:
        self._section_number.pop()
        self.section_level -= 1

    def visit_sidebar(self, node):
        self.duclass_open(node)
        self.requirements['color'] = PreambleCmds.color
        if not self.fallback_stylesheet:
            self.fallbacks['sidebar'] = PreambleCmds.sidebar
        self.out.append('\\DUsidebar{')

    def depart_sidebar(self, node):
        self.out.append('}\n')
        self.duclass_close(node)

    attribution_formats = {'dash': ('—', ''),  # EM DASH
                           'parentheses': ('(', ')'),
                           'parens': ('(', ')'),
                           'none': ('', '')}

    def visit_attribution(self, node):
        prefix, suffix = self.attribution_formats[self.settings.attribution]
        self.out.append('\\nopagebreak\n\n\\raggedleft ')
        self.out.append(prefix)
        self.context.append(suffix)

    def depart_attribution(self, node):
        self.out.append(self.context.pop() + '\n')

    def visit_status(self, node):
        self.visit_docinfo_item(node, 'status')

    def depart_status(self, node):
        self.depart_docinfo_item(node)

    def visit_strong(self, node):
        self.out.append('\\textbf{')
        self.visit_inline(node)

    def depart_strong(self, node):
        self.depart_inline(node)
        self.out.append('}')

    def visit_substitution_definition(self, node):
        raise nodes.SkipNode

    def visit_substitution_reference(self, node):
        self.unimplemented_visit(node)

    def visit_subtitle(self, node):
        if isinstance(node.parent, nodes.document):
            self.push_output_collector(self.subtitle)
            if not self.fallback_stylesheet:
                self.fallbacks['documentsubtitle'] = PreambleCmds.documentsubtitle  # noqa:E501
            protect = (self.settings.documentclass == 'memoir')
            self.subtitle_labels += self.ids_to_labels(node, set_anchor=False,
                                                       protect=protect)
        # section subtitle: "starred" (no number, not in ToC)
        elif isinstance(node.parent, nodes.section):
            self.out.append(r'\%s*{' %
                            self.d_class.section(self.section_level + 1))
        else:
            if not self.fallback_stylesheet:
                self.fallbacks['subtitle'] = PreambleCmds.subtitle
            self.out.append('\n\\DUsubtitle{')

    def depart_subtitle(self, node):
        if isinstance(node.parent, nodes.document):
            self.pop_output_collector()
        else:
            self.out.append('}\n')

    def visit_system_message(self, node):
        self.requirements['color'] = PreambleCmds.color
        if not self.fallback_stylesheet:
            self.fallbacks['title'] = PreambleCmds.title
        if self.settings.legacy_class_functions:
            self.fallbacks['title'] = PreambleCmds.title_legacy
        node['classes'] = ['system-message']
        self.visit_admonition(node)
        if self.settings.legacy_class_functions:
            self.out.append('\n\\DUtitle[system-message]{system-message\n')
        else:
            self.out.append('\n\\DUtitle{system-message\n')
        self.append_hypertargets(node)
        try:
            line = ', line~%s' % node['line']
        except KeyError:
            line = ''
        self.out.append('}\n\n{\\color{red}%s/%s} in \\texttt{%s}%s\n' %
                        (node['type'], node['level'],
                         self.encode(node['source']), line))
        if len(node['backrefs']) == 1:
            self.out.append('\n\\hyperlink{%s}{' % node['backrefs'][0])
            self.context.append('}')
        else:
            backrefs = ['\\hyperlink{%s}{%d}' % (href, i+1)
                        for (i, href) in enumerate(node['backrefs'])]
            self.context.append('backrefs: ' + ' '.join(backrefs))

    def depart_system_message(self, node):
        self.out.append(self.context.pop())
        self.depart_admonition(node)

    def visit_table(self, node):
        self.duclass_open(node)
        self.requirements['table'] = PreambleCmds.table
        if not self.settings.legacy_column_widths:
            self.requirements['table1'] = PreambleCmds.table_columnwidth
        if self.active_table.is_open():
            self.table_stack.append(self.active_table)
            # nesting longtable does not work (e.g. 2007-04-18)
            self.active_table = Table(self, 'tabular')
        # A longtable moves before \paragraph and \subparagraph
        # section titles if it immediately follows them:
        if (self.active_table._latex_type == 'longtable'
            and isinstance(node.parent, nodes.section)
            and node.parent.index(node) == 1
            and self.d_class.section(
                   self.section_level).find('paragraph') != -1):
            self.out.append('\\leavevmode')
        self.active_table.open()
        self.active_table.set_table_style(node, self.settings)
        if self.active_table.borders == 'booktabs':
            self.requirements['booktabs'] = r'\usepackage{booktabs}'
        self.push_output_collector([])

    def depart_table(self, node):
        # wrap content in the right environment:
        content = self.out
        self.pop_output_collector()
        try:
            width = self.to_latex_length(node['width'])
        except KeyError:
            width = r'\linewidth'
        # TODO: Don't use a longtable or add \noindent before
        #       the next paragraph, when in a "compound paragraph".
        #       Start a new line or a new paragraph?
        #       if (isinstance(node.parent, nodes.compound)
        #       and self._latex_type != 'longtable')?
        self.out.append(self.active_table.get_opening(width))
        self.out += content
        self.out.append(self.active_table.get_closing() + '\n')
        self.active_table.close()
        if len(self.table_stack) > 0:
            self.active_table = self.table_stack.pop()
        # Insert hyperlabel after (long)table, as
        # other places (beginning, caption) result in LaTeX errors.
        self.out += self.ids_to_labels(node, set_anchor=False, newline=True)
        self.duclass_close(node)

    def visit_target(self, node):
        # Skip indirect targets:
        if ('refuri' in node        # external hyperlink
            or 'refid' in node      # resolved internal link
            or 'refname' in node):  # unresolved internal link
            ## self.out.append('%% %s\n' % node)   # for debugging
            return
        self.out.append('%\n')
        # do we need an anchor (\phantomsection)?
        set_anchor = not isinstance(node.parent, (nodes.caption, nodes.title))
        # TODO: where else can/must we omit the \phantomsection?
        self.out += self.ids_to_labels(node, set_anchor)

    def depart_target(self, node):
        pass

    def visit_tbody(self, node):
        # BUG write preamble if not yet done (colspecs not [])
        # for tables without heads.
        if not self.active_table.get('preamble written'):
            self.visit_thead(node)
            self.depart_thead(None)

    def depart_tbody(self, node):
        pass

    def visit_term(self, node):
        """definition list term"""
        # Commands with optional args inside an optional arg must be put
        # in a group, e.g. ``\item[{\hyperref[label]{text}}]``.
        self.out.append('\\item[{')

    def depart_term(self, node):
        self.out.append('}] ')
        # Do we need a \leavevmode (line break if the field body begins
        # with a list or environment)?
        next_node = node.next_node(descend=False, siblings=True)
        if not isinstance(next_node, nodes.classifier):
            self.out.append(self.term_postfix(next_node))

    def visit_tgroup(self, node):
        pass

    def depart_tgroup(self, node):
        pass

    _thead_depth = 0

    def thead_depth(self):
        return self._thead_depth

    def visit_thead(self, node):
        self._thead_depth += 1
        if 1 == self.thead_depth():
            self.out.append('{%s}\n' % self.active_table.get_colspecs(node))
            self.active_table.set('preamble written', 1)
        self.out.append(self.active_table.get_caption())
        self.out.extend(self.active_table.visit_thead())

    def depart_thead(self, node):
        if node is not None:
            self.out.extend(self.active_table.depart_thead())
            if self.active_table.need_recurse():
                node.walkabout(self)
        self._thead_depth -= 1

    def visit_title(self, node):
        """Append section and other titles."""
        # Document title
        if isinstance(node.parent, nodes.document):
            self.push_output_collector(self.title)
            self.context.append('')
            self.pdfinfo.append('  pdftitle={%s},' %
                                self.encode(node.astext()))
        # Topic titles (topic, admonition, sidebar)
        elif (isinstance(node.parent, nodes.topic)
              or isinstance(node.parent, nodes.admonition)
              or isinstance(node.parent, nodes.sidebar)):
            classes = node.parent['classes'] or [node.parent.tagname]
            if self.settings.legacy_class_functions:
                self.fallbacks['title'] = PreambleCmds.title_legacy
                self.out.append('\n\\DUtitle[%s]{' % ','.join(classes))
            else:
                if not self.fallback_stylesheet:
                    self.fallbacks['title'] = PreambleCmds.title
                self.out.append('\n\\DUtitle{')
            self.context.append('}\n')
        # Table caption
        elif isinstance(node.parent, nodes.table):
            self.push_output_collector(self.active_table.caption)
            self.context.append('')
        # Section title
        else:
            if hasattr(PreambleCmds, 'secnumdepth'):
                self.requirements['secnumdepth'] = PreambleCmds.secnumdepth
            level = self.section_level
            section_name = self.d_class.section(level)
            self.out.append('\n\n')
            if level > len(self.d_class.sections):
                # section level not supported by LaTeX
                if self.settings.legacy_class_functions:
                    self.fallbacks['title'] = PreambleCmds.title_legacy
                    section_name += '[section%s]' % roman.toRoman(level)
                else:
                    if not self.fallback_stylesheet:
                        self.fallbacks['title'] = PreambleCmds.title
                        self.fallbacks['DUclass'] = PreambleCmds.duclass
                    self.out.append('\\begin{DUclass}{section%s}\n'
                                    % roman.toRoman(level))

            # System messages heading in red:
            if 'system-messages' in node.parent['classes']:
                self.requirements['color'] = PreambleCmds.color
                section_title = self.encode(node.astext())
                self.out.append(r'\%s[%s]{\color{red}' % (
                                section_name, section_title))
            else:
                self.out.append(r'\%s{' % section_name)

            # label and ToC entry:
            bookmark = ['']
            # add sections with unsupported level to toc and pdfbookmarks?
            ## if level > len(self.d_class.sections):
            ##     section_title = self.encode(node.astext())
            ##     bookmark.append(r'\addcontentsline{toc}{%s}{%s}' %
            ##               (section_name, section_title))
            bookmark += self.ids_to_labels(node.parent, set_anchor=False)
            self.context.append('%\n  '.join(bookmark) + '%\n}\n')
            if (level > len(self.d_class.sections)
                and not self.settings.legacy_class_functions):
                self.context[-1] += '\\end{DUclass}\n'
            # MAYBE postfix paragraph and subparagraph with \leavevmode to
            # ensure floats stay in the section and text starts on a new line.

    def depart_title(self, node):
        self.out.append(self.context.pop())
        if isinstance(node.parent, (nodes.table, nodes.document)):
            self.pop_output_collector()

    def visit_contents(self, node):
        """Write the table of contents.

        Called from visit_topic() for "contents" topics.
        """
        # requirements/setup for local ToC with package "minitoc",
        if self.use_latex_toc and 'local' in node['classes']:
            section_name = self.d_class.section(self.section_level)
            # minitoc only supports "part" and toplevel sections
            minitoc_names = {'part': 'part',
                             'chapter': 'mini',
                             'section': 'sect'}
            if 'chapter' in self.d_class.sections:
                del minitoc_names['section']
            try:
                mtc_name = minitoc_names[section_name]
            except KeyError:
                self.warn('Skipping local ToC at "%s" level.\n'
                          '  Feature not supported with option "use-latex-toc"'
                          % section_name, base_node=node)
                raise nodes.SkipNode

        # labels and PDF bookmark (sidebar entry)
        self.out.append('\n')  # start new paragraph
        if node['names']:  # don't add labels just for auto-ids
            self.out += self.ids_to_labels(node, newline=True)
        if (isinstance(node.next_node(), nodes.title)
            and 'local' not in node['classes']
            and self.settings.documentclass != 'memoir'):
            self.out.append('\\pdfbookmark[%d]{%s}{%s}\n' %
                            (self.section_level+1,
                             node.next_node().astext(),
                             node.get('ids', ['contents'])[0]))

        # Docutils generated contents list (no page numbers)
        if not self.use_latex_toc:
            self.fallbacks['toc-list'] = PreambleCmds.toc_list
            self.duclass_open(node)
            return

        # ToC by LaTeX
        depth = node.get('depth', 0)
        maxdepth = len(self.d_class.sections)
        if isinstance(node.next_node(), nodes.title):
            title = self.encode(node[0].astext())
        else:
            title = ''
        if 'local' in node['classes']:
            # use the "minitoc" package
            self.requirements['minitoc'] = PreambleCmds.minitoc
            self.requirements['minitoc-'+mtc_name] = r'\do%stoc'%mtc_name
            self.requirements['minitoc-%s-depth' % mtc_name] = (
                r'\mtcsetdepth{%stoc}{%d}' % (mtc_name, maxdepth))
            # "depth" option: Docutils stores a relative depth while
            # minitoc  expects an absolute depth!:
            offset = {'sect': 1, 'mini': 0, 'part': 0}
            if 'chapter' in self.d_class.sections:
                offset['part'] = -1
            if depth:
                self.out.append('\\setcounter{%stocdepth}{%d}' %
                                (mtc_name, depth + offset[mtc_name]))
            # title:
            self.out.append('\\mtcsettitle{%stoc}{%s}\n' % (mtc_name, title))
            # the toc-generating command:
            self.out.append('\\%stoc\n' % mtc_name)
        else:
            if depth:
                self.out.append('\\setcounter{tocdepth}{%d}\n'
                                % self.d_class.latex_section_depth(depth))
            if title != 'Contents':
                self.out.append('\\renewcommand{\\contentsname}{%s}\n' % title)
            self.out.append('\\tableofcontents\n')
            self.has_latex_toc = True
        # ignore rest of node content
        raise nodes.SkipNode

    def visit_topic(self, node):
        # Topic nodes can be generic topic, abstract, dedication, or ToC.
        # table of contents:
        if 'contents' in node['classes']:
            self.visit_contents(node)
        elif ('abstract' in node['classes']
              and self.settings.use_latex_abstract):
            self.push_output_collector(self.abstract)
            self.out.append('\\begin{abstract}')
            if isinstance(node.next_node(), nodes.title):
                node.pop(0)  # LaTeX provides its own title
        else:
            # special topics:
            if 'abstract' in node['classes']:
                if not self.fallback_stylesheet:
                    self.fallbacks['abstract'] = PreambleCmds.abstract
                if self.settings.legacy_class_functions:
                    self.fallbacks['abstract'] = PreambleCmds.abstract_legacy
                self.push_output_collector(self.abstract)
            elif 'dedication' in node['classes']:
                if not self.fallback_stylesheet:
                    self.fallbacks['dedication'] = PreambleCmds.dedication
                self.push_output_collector(self.dedication)
            else:
                node['classes'].insert(0, 'topic')
            self.visit_block_quote(node)

    def depart_topic(self, node):
        if ('abstract' in node['classes']
            and self.settings.use_latex_abstract):
            self.out.append('\\end{abstract}\n')
        elif 'contents' in node['classes']:
            self.duclass_close(node)
        else:
            self.depart_block_quote(node)
        if ('abstract' in node['classes']
            or 'dedication' in node['classes']):
            self.pop_output_collector()

    def visit_transition(self, node):
        if not self.fallback_stylesheet:
            self.fallbacks['transition'] = PreambleCmds.transition
        self.out.append('\n%' + '_' * 75 + '\n')
        self.out.append('\\DUtransition\n')

    def depart_transition(self, node):
        pass

    def visit_version(self, node):
        self.visit_docinfo_item(node, 'version')

    def depart_version(self, node):
        self.depart_docinfo_item(node)

    def unimplemented_visit(self, node):
        raise NotImplementedError('visiting unimplemented node type: %s' %
                                  node.__class__.__name__)

#    def unknown_visit(self, node):
#    def default_visit(self, node):

# vim: set ts=4 et ai :
