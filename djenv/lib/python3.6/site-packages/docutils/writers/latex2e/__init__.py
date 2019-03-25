# .. coding: utf-8
# $Id: __init__.py 8058 2017-04-19 16:45:32Z milde $
# Author: Engelbert Gruber, Günter Milde
# Maintainer: docutils-develop@lists.sourceforge.net
# Copyright: This module has been placed in the public domain.

"""LaTeX2e document tree Writer."""

__docformat__ = 'reStructuredText'

# code contributions from several people included, thanks to all.
# some named: David Abrahams, Julien Letessier, Lele Gaifax, and others.
#
# convention deactivate code by two # i.e. ##.

import sys
import os
import time
import re
import string
import urllib.request, urllib.parse, urllib.error
try:
    import roman
except ImportError:
    import docutils.utils.roman as roman
from docutils import frontend, nodes, languages, writers, utils, io
from docutils.utils.error_reporting import SafeString
from docutils.transforms import writer_aux
from docutils.utils.math import pick_math_environment, unichar2tex

class Writer(writers.Writer):

    supported = ('latex','latex2e')
    """Formats this writer supports."""

    default_template = 'default.tex'
    default_template_path = os.path.dirname(os.path.abspath(__file__))
    default_preamble = '\n'.join([r'% PDF Standard Fonts',
                                  r'\usepackage{mathptmx} % Times',
                                  r'\usepackage[scaled=.90]{helvet}',
                                  r'\usepackage{courier}'])
    table_style_values = ('standard', 'booktabs','nolines', 'borderless',
                          'colwidths-auto', 'colwidths-given')

    settings_spec = (
        'LaTeX-Specific Options',
        None,
        (('Specify documentclass.  Default is "article".',
          ['--documentclass'],
          {'default': 'article', }),
         ('Specify document options.  Multiple options can be given, '
          'separated by commas.  Default is "a4paper".',
          ['--documentoptions'],
          {'default': 'a4paper', }),
         ('Footnotes with numbers/symbols by Docutils. (default)',
          ['--docutils-footnotes'],
          {'default': True, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Format for footnote references: one of "superscript" or '
          '"brackets".  Default is "superscript".',
          ['--footnote-references'],
          {'choices': ['superscript', 'brackets'], 'default': 'superscript',
           'metavar': '<format>',
           'overrides': 'trim_footnote_reference_space'}),
         ('Use \\cite command for citations. ',
          ['--use-latex-citations'],
          {'default': 0, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Use figure floats for citations '
          '(might get mixed with real figures). (default)',
          ['--figure-citations'],
          {'dest': 'use_latex_citations', 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ('Format for block quote attributions: one of "dash" (em-dash '
          'prefix), "parentheses"/"parens", or "none".  Default is "dash".',
          ['--attribution'],
          {'choices': ['dash', 'parentheses', 'parens', 'none'],
           'default': 'dash', 'metavar': '<format>'}),
         ('Specify LaTeX packages/stylesheets. '
         ' A style is referenced with \\usepackage if extension is '
         '".sty" or omitted and with \\input else. '
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
          {'default': 0, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Comma-separated list of directories where stylesheets are found. '
          'Used by --stylesheet-path when expanding relative path arguments. '
          'Default: "."',
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
         ('Table of contents by LaTeX. (default) ',
          ['--use-latex-toc'],
          {'default': 1, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Table of contents by Docutils (without page numbers). ',
          ['--use-docutils-toc'],
          {'dest': 'use_latex_toc', 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ('Add parts on top of the section hierarchy.',
          ['--use-part-section'],
          {'default': 0, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Attach author and date to the document info table. (default) ',
          ['--use-docutils-docinfo'],
          {'dest': 'use_latex_docinfo', 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ('Attach author and date to the document title.',
          ['--use-latex-docinfo'],
          {'default': 0, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ("Typeset abstract as topic. (default)",
          ['--topic-abstract'],
          {'dest': 'use_latex_abstract', 'action': 'store_false',
           'validator': frontend.validate_boolean}),
         ("Use LaTeX abstract environment for the document's abstract. ",
          ['--use-latex-abstract'],
          {'default': 0, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Color of any hyperlinks embedded in text '
          '(default: "blue", "false" to disable).',
          ['--hyperlink-color'], {'default': 'blue'}),
         ('Additional options to the "hyperref" package '
          '(default: "").',
          ['--hyperref-options'], {'default': ''}),
         ('Enable compound enumerators for nested enumerated lists '
          '(e.g. "1.2.a.ii").  Default: disabled.',
          ['--compound-enumerators'],
          {'default': None, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Disable compound enumerators for nested enumerated lists. '
          'This is the default.',
          ['--no-compound-enumerators'],
          {'action': 'store_false', 'dest': 'compound_enumerators'}),
         ('Enable section ("." subsection ...) prefixes for compound '
          'enumerators.  This has no effect without --compound-enumerators.'
          'Default: disabled.',
          ['--section-prefix-for-enumerators'],
          {'default': None, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Disable section prefixes for compound enumerators.  '
          'This is the default.',
          ['--no-section-prefix-for-enumerators'],
          {'action': 'store_false', 'dest': 'section_prefix_for_enumerators'}),
         ('Set the separator between section number and enumerator '
          'for compound enumerated lists.  Default is "-".',
          ['--section-enumerator-separator'],
          {'default': '-', 'metavar': '<char>'}),
         ('When possibile, use the specified environment for literal-blocks. '
          'Default is quoting of whitespace and special chars.',
          ['--literal-block-env'],
          {'default': ''}),
         ('When possibile, use verbatim for literal-blocks. '
          'Compatibility alias for "--literal-block-env=verbatim".',
          ['--use-verbatim-when-possible'],
          {'default': 0, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Table style. "standard" with horizontal and vertical lines, '
          '"booktabs" (LaTeX booktabs style) only horizontal lines '
          'above and below the table and below the header or "borderless".  '
          'Default: "standard"',
          ['--table-style'],
          {'default': ['standard'],
           'metavar': '<format>',
           'action': 'append',
           'validator': frontend.validate_comma_separated_list,
           'choices': table_style_values}),
         ('LaTeX graphicx package option. '
          'Possible values are "dvips", "pdftex". "auto" includes LaTeX code '
          'to use "pdftex" if processing with pdf(la)tex and dvips otherwise. '
          'Default is no option.',
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
          {'default': None, }),
         ('Specify style and database for bibtex, for example '
          '"--use-bibtex=mystyle,mydb1,mydb2".',
          ['--use-bibtex'],
          {'default': None, }),
          ),)

    settings_defaults = {'sectnum_depth': 0 # updated by SectNum transform
                        }
    config_section = 'latex2e writer'
    config_section_dependencies = ('writers',)

    head_parts = ('head_prefix', 'requirements', 'latex_preamble',
                  'stylesheet', 'fallbacks', 'pdfsetup',
                  'title', 'subtitle', 'titledata')
    visitor_attributes = head_parts + ('body_pre_docinfo', 'docinfo',
                                       'dedication', 'abstract', 'body')

    output = None
    """Final translated form of `document`."""

    def __init__(self):
        writers.Writer.__init__(self)
        self.translator_class = LaTeXTranslator

    # Override parent method to add latex-specific transforms
    def get_transforms(self):
       return writers.Writer.get_transforms(self) + [
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
        try:
            template_file = open(self.document.settings.template, 'rb')
        except IOError:
            template_file = open(os.path.join(self.default_template_path,
                                     self.document.settings.template), 'rb')
        template = string.Template(str(template_file.read(), 'utf-8'))
        template_file.close()
        # fill template
        self.assemble_parts() # create dictionary of parts
        self.output = template.substitute(self.parts)

    def assemble_parts(self):
        """Assemble the `self.parts` dictionary of output fragments."""
        writers.Writer.assemble_parts(self)
        for part in self.visitor_attributes:
            lines = getattr(self, part)
            if part in self.head_parts:
                if lines:
                    lines.append('') # to get a trailing newline
                self.parts[part] = '\n'.join(lines)
            else:
                # body contains inline elements, so join without newline
                self.parts[part] = ''.join(lines)


class Babel(object):
    """Language specifics for LaTeX."""

    # TeX (babel) language names:
    # ! not all of these are supported by Docutils!
    #
    # based on LyX' languages file with adaptions to `BCP 47`_
    # (http://www.rfc-editor.org/rfc/bcp/bcp47.txt) and
    # http://www.tug.org/TUGboat/Articles/tb29-3/tb93miklavec.pdf
    # * the key without subtags is the default
    # * case is ignored
    # cf. http://docutils.sourceforge.net/docs/howto/i18n.html
    #     http://www.w3.org/International/articles/language-tags/
    # and http://www.iana.org/assignments/language-subtag-registry
    language_codes = {
        # code          TeX/Babel-name       comment
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
        'de':           'ngerman', # new spelling (de_1996)
        'de-1901':      'german', # old spelling
        'de-AT':        'naustrian',
        'de-AT-1901':   'austrian',
        'dsb':          'lowersorbian',
        'el':           'greek', # monotonic (el-monoton)
        'el-polyton':   'polutonikogreek',
        'en':           'english',  # TeX' default language
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
        'ga':           'irish',    # Irish Gaelic
        # 'grc':                    # Ancient Greek
        'grc-ibycus':   'ibycus',   # Ibycus encoding
        'gl':           'galician',
        'he':           'hebrew',
        'hr':           'croatian',
        'hsb':          'uppersorbian',
        'hu':           'magyar',
        'ia':           'interlingua',
        'id':           'bahasai',  # Bahasa (Indonesian)
        'is':           'icelandic',
        'it':           'italian',
        'ja':           'japanese',
        'kk':           'kazakh',
        'la':           'latin',
        'lt':           'lithuanian',
        'lv':           'latvian',
        'mn':           'mongolian', # Mongolian, Cyrillic script (mn-cyrl)
        'ms':           'bahasam',   # Bahasa (Malay)
        'nb':           'norsk',     # Norwegian Bokmal
        'nl':           'dutch',
        'nn':           'nynorsk',   # Norwegian Nynorsk
        'no':           'norsk',     # Norwegian (Bokmal)
        'pl':           'polish',
        'pt':           'portuges',
        'pt-BR':        'brazil',
        'ro':           'romanian',
        'ru':           'russian',
        'se':           'samin',     # North Sami
        'sh-Cyrl':      'serbianc',  # Serbo-Croatian, Cyrillic script
        'sh-Latn':      'serbian',   # Serbo-Croatian, Latin script see also 'hr'
        'sk':           'slovak',
        'sl':           'slovene',
        'sq':           'albanian',
        'sr':           'serbianc',  # Serbian, Cyrillic script (contributed)
        'sr-Latn':      'serbian',   # Serbian, Latin script
        'sv':           'swedish',
        # 'th':           'thai',
        'tr':           'turkish',
        'uk':           'ukrainian',
        'vi':           'vietnam',
        # zh-Latn:      Chinese Pinyin
        }
    # normalize (downcase) keys
    language_codes = dict([(k.lower(), v) for (k,v) in list(language_codes.items())])

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
    active_chars = {# TeX/Babel-name:  active characters to deactivate
                    # 'breton':        ':;!?' # ensure whitespace
                    # 'esperanto':     '^',
                    # 'estonian':      '~"`',
                    # 'french':        ':;!?' # ensure whitespace
                    'galician':        '.<>', # also '~"'
                    # 'magyar':        '`', # for special hyphenation cases
                    'spanish':         '.<>', # old versions also '~'
                    # 'turkish':       ':!=' # ensure whitespace
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
        for c in ''.join([self.active_chars.get(l, '') for l in languages]):
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
        if (languages[-1] == 'english' and
            'french' in list(self.otherlanguages.keys())):
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
        keys = list(self.keys())
        keys.sort()
        return keys

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

class PreambleCmds(object):
    """Building blocks for the latex preamble."""

PreambleCmds.abstract = r"""
% abstract title
\providecommand*{\DUtitleabstract}[1]{\centerline{\textbf{#1}}}"""

PreambleCmds.admonition = r"""
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

## PreambleCmds.caption = r"""% configure caption layout
## \usepackage{caption}
## \captionsetup{singlelinecheck=false}% no exceptions for one-liners"""

PreambleCmds.color = r"""\usepackage{color}"""

PreambleCmds.docinfo = r"""
% docinfo (width of docinfo table)
\DUprovidelength{\DUdocinfowidth}{0.9\linewidth}"""
# PreambleCmds.docinfo._depends = 'providelength'

PreambleCmds.dedication = r"""
% dedication topic
\providecommand*{\DUCLASSdedication}{%
  \renewenvironment{quote}{\begin{center}}{\end{center}}%
}"""

PreambleCmds.duclass = r"""
% class handling for environments (block-level elements)
% \begin{DUclass}{spam} tries \DUCLASSspam and
% \end{DUclass}{spam} tries \endDUCLASSspam
\ifx\DUclass\undefined % poor man's "provideenvironment"
 \newenvironment{DUclass}[1]%
  {\def\DocutilsClassFunctionName{DUCLASS#1}% arg cannot be used in end-part of environment.
     \csname \DocutilsClassFunctionName \endcsname}%
  {\csname end\DocutilsClassFunctionName \endcsname}%
\fi"""

PreambleCmds.error = r"""
% error admonition title
\providecommand*{\DUtitleerror}[1]{\DUtitle{\color{red}#1}}"""

PreambleCmds.fieldlist = r"""
% fieldlist environment
\ifthenelse{\isundefined{\DUfieldlist}}{
  \newenvironment{DUfieldlist}%
    {\quote\description}
    {\enddescription\endquote}
}{}"""

PreambleCmds.float_settings = r"""\usepackage{float} % float configuration
\floatplacement{figure}{H} % place figures here definitely"""

PreambleCmds.footnotes = r"""% numeric or symbol footnotes with hyperlinks
\providecommand*{\DUfootnotemark}[3]{%
  \raisebox{1em}{\hypertarget{#1}{}}%
  \hyperlink{#2}{\textsuperscript{#3}}%
}
\providecommand{\DUfootnotetext}[4]{%
  \begingroup%
  \renewcommand{\thefootnote}{%
    \protect\raisebox{1em}{\protect\hypertarget{#1}{}}%
    \protect\hyperlink{#2}{#3}}%
  \footnotetext{#4}%
  \endgroup%
}"""

PreambleCmds.graphicx_auto = r"""% Check output format
\ifx\pdftexversion\undefined
  \usepackage{graphicx}
\else
  \usepackage[pdftex]{graphicx}
\fi"""

PreambleCmds.highlight_rules = r"""% basic code highlight:
\providecommand*\DUrolecomment[1]{\textcolor[rgb]{0.40,0.40,0.40}{#1}}
\providecommand*\DUroledeleted[1]{\textcolor[rgb]{0.40,0.40,0.40}{#1}}
\providecommand*\DUrolekeyword[1]{\textbf{#1}}
\providecommand*\DUrolestring[1]{\textit{#1}}"""

PreambleCmds.inline = r"""
% inline markup (custom roles)
% \DUrole{#1}{#2} tries \DUrole#1{#2}
\providecommand*{\DUrole}[2]{%
  % backwards compatibility: try \docutilsrole#1{#2}
  \ifcsname docutilsrole#1\endcsname%
    \csname docutilsrole#1\endcsname{#2}%
  \else
    \csname DUrole#1\endcsname{#2}%
  \fi%
}"""

PreambleCmds.legend = r"""
% legend environment
\ifthenelse{\isundefined{\DUlegend}}{
  \newenvironment{DUlegend}{\small}{}
}{}"""

PreambleCmds.lineblock = r"""
% lineblock environment
\DUprovidelength{\DUlineblockindent}{2.5em}
\ifthenelse{\isundefined{\DUlineblock}}{
  \newenvironment{DUlineblock}[1]{%
    \list{}{\setlength{\partopsep}{\parskip}
            \addtolength{\partopsep}{\baselineskip}
            \setlength{\topsep}{0pt}
            \setlength{\itemsep}{0.15\baselineskip}
            \setlength{\parsep}{0pt}
            \setlength{\leftmargin}{#1}}
    \raggedright
  }
  {\endlist}
}{}"""
# PreambleCmds.lineblock._depends = 'providelength'

PreambleCmds.linking = r"""
%% hyperlinks:
\ifthenelse{\isundefined{\hypersetup}}{
  \usepackage[%s]{hyperref}
  \usepackage{bookmark}
  \urlstyle{same} %% normal text font (alternatives: tt, rm, sf)
}{}"""

PreambleCmds.minitoc = r"""%% local table of contents
\usepackage{minitoc}"""

PreambleCmds.optionlist = r"""
% optionlist environment
\providecommand*{\DUoptionlistlabel}[1]{\bf #1 \hfill}
\DUprovidelength{\DUoptionlistindent}{3cm}
\ifthenelse{\isundefined{\DUoptionlist}}{
  \newenvironment{DUoptionlist}{%
    \list{}{\setlength{\labelwidth}{\DUoptionlistindent}
            \setlength{\rightmargin}{1cm}
            \setlength{\leftmargin}{\rightmargin}
            \addtolength{\leftmargin}{\labelwidth}
            \addtolength{\leftmargin}{\labelsep}
            \renewcommand{\makelabel}{\DUoptionlistlabel}}
  }
  {\endlist}
}{}"""
# PreambleCmds.optionlist._depends = 'providelength'

PreambleCmds.providelength = r"""
% providelength (provide a length variable and set default, if it is new)
\providecommand*{\DUprovidelength}[2]{
  \ifthenelse{\isundefined{#1}}{\newlength{#1}\setlength{#1}{#2}}{}
}"""

PreambleCmds.rubric = r"""
% rubric (informal heading)
\providecommand*{\DUrubric}[1]{%
  \subsubsection*{\centering\textit{\textmd{#1}}}}"""

PreambleCmds.sidebar = r"""
% sidebar (text outside the main text flow)
\providecommand{\DUsidebar}[1]{%
  \begin{center}
    \colorbox[gray]{0.80}{\parbox{0.9\linewidth}{#1}}
  \end{center}
}"""

PreambleCmds.subtitle = r"""
% subtitle (for topic/sidebar)
\providecommand*{\DUsubtitle}[1]{\par\emph{#1}\smallskip}"""

PreambleCmds.documentsubtitle = r"""
% subtitle (in document title)
\providecommand*{\DUdocumentsubtitle}[1]{{\large #1}}"""

PreambleCmds.table = r"""\usepackage{longtable,ltcaption,array}
\setlength{\extrarowheight}{2pt}
\newlength{\DUtablewidth} % internal use in tables"""

# Options [force,almostfull] prevent spurious error messages, see
# de.comp.text.tex/2005-12/msg01855
PreambleCmds.textcomp = """\
\\usepackage{textcomp} % text symbol macros"""

PreambleCmds.textsubscript = r"""
% text mode subscript
\ifx\textsubscript\undefined
  \usepackage{fixltx2e} % since 2015 loaded by default
\fi"""

PreambleCmds.titlereference = r"""
% titlereference role
\providecommand*{\DUroletitlereference}[1]{\textsl{#1}}"""

PreambleCmds.title = r"""
% title for topics, admonitions, unsupported section levels, and sidebar
\providecommand*{\DUtitle}[2][class-arg]{%
  % call \DUtitle#1{#2} if it exists:
  \ifcsname DUtitle#1\endcsname%
    \csname DUtitle#1\endcsname{#2}%
  \else
    \smallskip\noindent\textbf{#2}\smallskip%
  \fi
}"""

PreambleCmds.transition = r"""
% transition (break, fancybreak, anonymous section)
\providecommand*{\DUtransition}{%
  \hspace*{\fill}\hrulefill\hspace*{\fill}
  \vskip 0.5\baselineskip
}"""


# LaTeX encoding maps
# -------------------
# ::

class CharMaps(object):
    """LaTeX representations for active and Unicode characters."""

    # characters that need escaping even in `alltt` environments:
    alltt = {
        ord('\\'): r'\textbackslash{}',
        ord('{'): r'\{',
        ord('}'): r'\}',
    }
    # characters that normally need escaping:
    special = {
        ord('#'): r'\#',
        ord('$'): r'\$',
        ord('%'): r'\%',
        ord('&'): r'\&',
        ord('~'): r'\textasciitilde{}',
        ord('_'): r'\_',
        ord('^'): r'\textasciicircum{}',
        # straight double quotes are 'active' in many languages
        ord('"'): r'\textquotedbl{}',
        # Square brackets are ordinary chars and cannot be escaped with '\',
        # so we put them in a group '{[}'. (Alternative: ensure that all
        # macros with optional arguments are terminated with {} and text
        # inside any optional argument is put in a group ``[{text}]``).
        # Commands with optional args inside an optional arg must be put in a
        # group, e.g. ``\item[{\hyperref[label]{text}}]``.
        ord('['): r'{[}',
        ord(']'): r'{]}',
        # the soft hyphen is unknown in 8-bit text
        # and not properly handled by XeTeX
        0x00AD: r'\-', # SOFT HYPHEN
    }
    # Unicode chars that are not recognized by LaTeX's utf8 encoding
    unsupported_unicode = {
        # TODO: ensure white space also at the beginning of a line?
        # 0x00A0: ur'\leavevmode\nobreak\vadjust{}~'
        0x2000: r'\enskip', # EN QUAD
        0x2001: r'\quad', # EM QUAD
        0x2002: r'\enskip', # EN SPACE
        0x2003: r'\quad', # EM SPACE
        0x2008: r'\,', # PUNCTUATION SPACE   
        0x200b: r'\hspace{0pt}', # ZERO WIDTH SPACE
        0x202F: r'\,', # NARROW NO-BREAK SPACE
        # 0x02d8: ur'\\u{ }', # BREVE
        0x2011: r'\hbox{-}', # NON-BREAKING HYPHEN
        0x212b: r'\AA', # ANGSTROM SIGN
        0x21d4: r'\ensuremath{\Leftrightarrow}',
        # Docutils footnote symbols:
        0x2660: r'\ensuremath{\spadesuit}',
        0x2663: r'\ensuremath{\clubsuit}',
        0xfb00: r'ff', # LATIN SMALL LIGATURE FF
        0xfb01: r'fi', # LATIN SMALL LIGATURE FI
        0xfb02: r'fl', # LATIN SMALL LIGATURE FL
        0xfb03: r'ffi', # LATIN SMALL LIGATURE FFI
        0xfb04: r'ffl', # LATIN SMALL LIGATURE FFL
    }
    # Unicode chars that are recognized by LaTeX's utf8 encoding
    utf8_supported_unicode = {
        0x00A0: r'~', # NO-BREAK SPACE
        0x00AB: r'\guillemotleft{}', # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
        0x00bb: r'\guillemotright{}', # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
        0x200C: r'\textcompwordmark{}', # ZERO WIDTH NON-JOINER
        0x2013: r'\textendash{}',
        0x2014: r'\textemdash{}',
        0x2018: r'\textquoteleft{}',
        0x2019: r'\textquoteright{}',
        0x201A: r'\quotesinglbase{}', # SINGLE LOW-9 QUOTATION MARK
        0x201C: r'\textquotedblleft{}',
        0x201D: r'\textquotedblright{}',
        0x201E: r'\quotedblbase{}', # DOUBLE LOW-9 QUOTATION MARK
        0x2030: r'\textperthousand{}',   # PER MILLE SIGN
        0x2031: r'\textpertenthousand{}', # PER TEN THOUSAND SIGN
        0x2039: r'\guilsinglleft{}',
        0x203A: r'\guilsinglright{}',
        0x2423: r'\textvisiblespace{}',  # OPEN BOX
        0x2020: r'\dag{}',
        0x2021: r'\ddag{}',
        0x2026: r'\dots{}',
        0x2122: r'\texttrademark{}',
    }
    # recognized with 'utf8', if textcomp is loaded
    textcomp = {
        # Latin-1 Supplement
        0x00a2: r'\textcent{}',          # ¢ CENT SIGN
        0x00a4: r'\textcurrency{}',      # ¤ CURRENCY SYMBOL
        0x00a5: r'\textyen{}',           # ¥ YEN SIGN
        0x00a6: r'\textbrokenbar{}',     # ¦ BROKEN BAR
        0x00a7: r'\textsection{}',       # § SECTION SIGN
        0x00a8: r'\textasciidieresis{}', # ¨ DIAERESIS
        0x00a9: r'\textcopyright{}',     # © COPYRIGHT SIGN
        0x00aa: r'\textordfeminine{}',   # ª FEMININE ORDINAL INDICATOR
        0x00ac: r'\textlnot{}',          # ¬ NOT SIGN
        0x00ae: r'\textregistered{}',    # ® REGISTERED SIGN
        0x00af: r'\textasciimacron{}',   # ¯ MACRON
        0x00b0: r'\textdegree{}',        # ° DEGREE SIGN
        0x00b1: r'\textpm{}',            # ± PLUS-MINUS SIGN
        0x00b2: r'\texttwosuperior{}',   # ² SUPERSCRIPT TWO
        0x00b3: r'\textthreesuperior{}', # ³ SUPERSCRIPT THREE
        0x00b4: r'\textasciiacute{}',    # ´ ACUTE ACCENT
        0x00b5: r'\textmu{}',            # µ MICRO SIGN
        0x00b6: r'\textparagraph{}',     # ¶ PILCROW SIGN # != \textpilcrow
        0x00b9: r'\textonesuperior{}',   # ¹ SUPERSCRIPT ONE
        0x00ba: r'\textordmasculine{}',  # º MASCULINE ORDINAL INDICATOR
        0x00bc: r'\textonequarter{}',    # 1/4 FRACTION
        0x00bd: r'\textonehalf{}',       # 1/2 FRACTION
        0x00be: r'\textthreequarters{}', # 3/4 FRACTION
        0x00d7: r'\texttimes{}',         # × MULTIPLICATION SIGN
        0x00f7: r'\textdiv{}',           # ÷ DIVISION SIGN
        # others
        0x0192: r'\textflorin{}',        # LATIN SMALL LETTER F WITH HOOK
        0x02b9: r'\textasciiacute{}',    # MODIFIER LETTER PRIME
        0x02ba: r'\textacutedbl{}',      # MODIFIER LETTER DOUBLE PRIME
        0x2016: r'\textbardbl{}',        # DOUBLE VERTICAL LINE
        0x2022: r'\textbullet{}',        # BULLET
        0x2032: r'\textasciiacute{}',    # PRIME
        0x2033: r'\textacutedbl{}',      # DOUBLE PRIME
        0x2035: r'\textasciigrave{}',    # REVERSED PRIME
        0x2036: r'\textgravedbl{}',      # REVERSED DOUBLE PRIME
        0x203b: r'\textreferencemark{}', # REFERENCE MARK
        0x203d: r'\textinterrobang{}',   # INTERROBANG
        0x2044: r'\textfractionsolidus{}', # FRACTION SLASH
        0x2045: r'\textlquill{}',        # LEFT SQUARE BRACKET WITH QUILL
        0x2046: r'\textrquill{}',        # RIGHT SQUARE BRACKET WITH QUILL
        0x2052: r'\textdiscount{}',      # COMMERCIAL MINUS SIGN
        0x20a1: r'\textcolonmonetary{}', # COLON SIGN
        0x20a3: r'\textfrenchfranc{}',   # FRENCH FRANC SIGN
        0x20a4: r'\textlira{}',          # LIRA SIGN
        0x20a6: r'\textnaira{}',         # NAIRA SIGN
        0x20a9: r'\textwon{}',           # WON SIGN
        0x20ab: r'\textdong{}',          # DONG SIGN
        0x20ac: r'\texteuro{}',          # EURO SIGN
        0x20b1: r'\textpeso{}',          # PESO SIGN
        0x20b2: r'\textguarani{}',       # GUARANI SIGN
        0x2103: r'\textcelsius{}',       # DEGREE CELSIUS
        0x2116: r'\textnumero{}',        # NUMERO SIGN
        0x2117: r'\textcircledP{}',      # SOUND RECORDING COYRIGHT
        0x211e: r'\textrecipe{}',        # PRESCRIPTION TAKE
        0x2120: r'\textservicemark{}',   # SERVICE MARK
        0x2122: r'\texttrademark{}',     # TRADE MARK SIGN
        0x2126: r'\textohm{}',           # OHM SIGN
        0x2127: r'\textmho{}',           # INVERTED OHM SIGN
        0x212e: r'\textestimated{}',     # ESTIMATED SYMBOL
        0x2190: r'\textleftarrow{}',     # LEFTWARDS ARROW
        0x2191: r'\textuparrow{}',       # UPWARDS ARROW
        0x2192: r'\textrightarrow{}',    # RIGHTWARDS ARROW
        0x2193: r'\textdownarrow{}',     # DOWNWARDS ARROW
        0x2212: r'\textminus{}',         # MINUS SIGN
        0x2217: r'\textasteriskcentered{}', # ASTERISK OPERATOR
        0x221a: r'\textsurd{}',          # SQUARE ROOT
        0x2422: r'\textblank{}',         # BLANK SYMBOL
        0x25e6: r'\textopenbullet{}',    # WHITE BULLET
        0x25ef: r'\textbigcircle{}',     # LARGE CIRCLE
        0x266a: r'\textmusicalnote{}',   # EIGHTH NOTE
        0x26ad: r'\textmarried{}',       # MARRIAGE SYMBOL
        0x26ae: r'\textdivorced{}',      # DIVORCE SYMBOL
        0x27e8: r'\textlangle{}',        # MATHEMATICAL LEFT ANGLE BRACKET
        0x27e9: r'\textrangle{}',        # MATHEMATICAL RIGHT ANGLE BRACKET
    }
    # Unicode chars that require a feature/package to render
    pifont = {
        0x2665: r'\ding{170}',     # black heartsuit
        0x2666: r'\ding{169}',     # black diamondsuit
        0x2713: r'\ding{51}',      # check mark
        0x2717: r'\ding{55}',      # check mark
    }
    # TODO: greek alphabet ... ?
    # see also LaTeX codec
    # http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/252124
    # and unimap.py from TeXML


class DocumentClass(object):
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
        else:  # unsupported levels
            return 'DUtitle[section%s]' % roman.toRoman(level)

class Table(object):
    """Manage a table while traversing.

    Maybe change to a mixin defining the visit/departs, but then
    class Table internal variables are in the Translator.

    Table style might be

    :standard:   horizontal and vertical lines
    :booktabs:   only horizontal lines (requires "booktabs" LaTeX package)
    :borderless: no borders around table cells
    :nolines:    alias for borderless

    :colwidths-auto:  column widths determined by LaTeX
    :colwidths-given: use colum widths from rST source
    """
    def __init__(self, translator, latex_type):
        self._translator = translator
        self._latex_type = latex_type
        self._open = False
        # miscellaneous attributes
        self._attrs = {}
        self._col_width = []
        self._rowspan = []
        self.stubs = []
        self.colwidths_auto = False
        self._in_thead = 0

    def open(self):
        self._open = True
        self._col_specs = []
        self.caption = []
        self._attrs = {}
        self._in_head = False # maybe context with search
    def close(self):
        self._open = False
        self._col_specs = None
        self.caption = []
        self._attrs = {}
        self.stubs = []
        self.colwidths_auto = False

    def is_open(self):
        return self._open

    def set_table_style(self, table_style, classes):
        borders = [cls.replace('nolines', 'borderless')
                   for cls in table_style+classes
                   if cls in ('standard','booktabs','borderless', 'nolines')]
        try:
            self.borders = borders[-1]
        except IndexError:
            self.borders = 'standard'
        self.colwidths_auto = (('colwidths-auto' in classes
                                and 'colwidths-given' not in table_style)
                               or ('colwidths-auto' in table_style
                                   and ('colwidths-given' not in classes)))

    def get_latex_type(self):
        if self._latex_type == 'longtable' and not self.caption:
            # do not advance the "table" counter (requires "ltcaption" package)
            return('longtable*')
        return self._latex_type

    def set(self,attr,value):
        self._attrs[attr] = value
    def get(self,attr):
        if attr in self._attrs:
            return self._attrs[attr]
        return None

    def get_vertical_bar(self):
        if self.borders == 'standard':
            return '|'
        return ''

    # horizontal lines are drawn below a row,
    def get_opening(self):
        align_map = {'left': 'l',
                     'center': 'c',
                     'right': 'r'}
        align = align_map.get(self.get('align') or 'center')
        opening = [r'\begin{%s}[%s]' % (self.get_latex_type(), align)]
        if not self.colwidths_auto:
            opening.insert(0, r'\setlength{\DUtablewidth}{\linewidth}')
        return '\n'.join(opening)

    def get_closing(self):
        closing = []
        if self.borders == 'booktabs':
            closing.append(r'\bottomrule')
        # elif self.borders == 'standard':
        #     closing.append(r'\hline')
        closing.append(r'\end{%s}' % self.get_latex_type())
        return '\n'.join(closing)

    def visit_colspec(self, node):
        self._col_specs.append(node)
        # "stubs" list is an attribute of the tgroup element:
        self.stubs.append(node.attributes.get('stub'))

    def get_colspecs(self, node):
        """Return column specification for longtable.

        Assumes reST line length being 80 characters.
        Table width is hairy.

        === ===
        ABC DEF
        === ===

        usually gets to narrow, therefore we add 1 (fiddlefactor).
        """
        bar = self.get_vertical_bar()
        self._rowspan= [0] * len(self._col_specs)
        self._col_width = []
        if self.colwidths_auto:
            latex_table_spec = (bar+'l')*len(self._col_specs)
            return latex_table_spec+bar
        width = 80
        total_width = 0.0
        # first see if we get too wide.
        for node in self._col_specs:
            colwidth = float(node['colwidth']+1) / width
            total_width += colwidth
        # donot make it full linewidth
        factor = 0.93
        if total_width > 1.0:
            factor /= total_width
        latex_table_spec = ''
        for node in self._col_specs:
            colwidth = factor * float(node['colwidth']+1) / width
            self._col_width.append(colwidth+0.005)
            latex_table_spec += '%sp{%.3f\\DUtablewidth}' % (bar, colwidth+0.005)
        return latex_table_spec+bar

    def get_column_width(self):
        """Return columnwidth for current cell (not multicell)."""
        try:
            return '%.2f\\DUtablewidth' % self._col_width[self._cell_in_row]
        except IndexError:
            return '*'

    def get_multicolumn_width(self, start, len_):
        """Return sum of columnwidths for multicell."""
        try:
            mc_width = sum([width
                            for width in ([self._col_width[start + co]
                                           for co in range (len_)])])
            return 'p{%.2f\\DUtablewidth}' % mc_width
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
        #if self.borders == 'standard':
        #    a.append('\\hline\n')
        if self.borders == 'booktabs':
            a.append('\\midrule\n')
        if self._latex_type == 'longtable':
            if 1 == self._translator.thead_depth():
                a.append('\\endfirsthead\n')
            else:
                a.append('\\endhead\n')
                a.append(r'\multicolumn{%d}{c}' % len(self._col_specs) +
                         r'{\hfill ... continued on next page} \\')
                a.append('\n\\endfoot\n\\endlastfoot\n')
        # for longtable one could add firsthead, foot and lastfoot
        self._in_thead -= 1
        return a

    def visit_row(self):
        self._cell_in_row = 0

    def depart_row(self):
        res = [' \\\\\n']
        self._cell_in_row = None  # remove cell counter
        for i in range(len(self._rowspan)):
            if (self._rowspan[i]>0):
                self._rowspan[i] -= 1

        if self.borders == 'standard':
            rowspans = [i+1 for i in range(len(self._rowspan))
                        if (self._rowspan[i]<=0)]
            if len(rowspans)==len(self._rowspan):
                res.append('\\hline\n')
            else:
                cline = ''
                rowspans.reverse()
                # TODO merge clines
                while True:
                    try:
                        c_start = rowspans.pop()
                    except:
                        break
                    cline += '\\cline{%d-%d}\n' % (c_start,c_start)
                res.append(cline)
        return res

    def set_rowspan(self,cell,value):
        try:
            self._rowspan[cell] = value
        except:
            pass

    def get_rowspan(self,cell):
        try:
            return self._rowspan[cell]
        except:
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

    has_latex_toc = False # is there a toc in the doc? (needed by minitoc)
    is_toc_list = False   # is the current bullet_list a ToC?
    section_level = 0

    # Flags to encode():
    # inside citation reference labels underscores dont need to be escaped
    inside_citation_reference_label = False
    verbatim = False                   # do not encode
    insert_non_breaking_blanks = False # replace blanks by "~"
    insert_newline = False             # add latex newline commands
    literal = False                    # literal text (block or inline)
    alltt = False                      # inside `alltt` environment

    def __init__(self, document, babel_class=Babel):
        nodes.NodeVisitor.__init__(self, document)
        # Reporter
        # ~~~~~~~~
        self.warn = self.document.reporter.warning
        self.error = self.document.reporter.error

        # Settings
        # ~~~~~~~~
        self.settings = settings = document.settings
        self.latex_encoding = self.to_latex_encoding(settings.output_encoding)
        self.use_latex_toc = settings.use_latex_toc
        self.use_latex_docinfo = settings.use_latex_docinfo
        self._use_latex_citations = settings.use_latex_citations
        self._reference_label = settings.reference_label
        self.hyperlink_color = settings.hyperlink_color
        self.compound_enumerators = settings.compound_enumerators
        self.font_encoding = getattr(settings, 'font_encoding', '')
        self.section_prefix_for_enumerators = (
            settings.section_prefix_for_enumerators)
        self.section_enumerator_separator = (
            settings.section_enumerator_separator.replace('_', r'\_'))
        # literal blocks:
        self.literal_block_env = 'alltt'
        self.literal_block_options = ''
        if settings.literal_block_env != '':
            (none,
             self.literal_block_env,
             self.literal_block_options,
             none ) = re.split(r'(\w+)(.*)', settings.literal_block_env)
        elif settings.use_verbatim_when_possible:
            self.literal_block_env = 'verbatim'
        #
        if self.settings.use_bibtex:
            self.bibtex = self.settings.use_bibtex.split(',',1)
            # TODO avoid errors on not declared citations.
        else:
            self.bibtex = None
        # language module for Docutils-generated text
        # (labels, bibliographic_fields, and author_separators)
        self.language_module = languages.get_language(settings.language_code,
                                              document.reporter)
        self.babel = babel_class(settings.language_code, document.reporter)
        self.author_separator = self.language_module.author_separators[0]
        d_options = [self.settings.documentoptions]
        if self.babel.language not in ('english', ''):
            d_options.append(self.babel.language)
        self.documentoptions = ','.join([_f for _f in d_options if _f])
        self.d_class = DocumentClass(settings.documentclass,
                                     settings.use_part_section)
        # graphic package options:
        if self.settings.graphicx_option == '':
            self.graphicx_package = r'\usepackage{graphicx}'
        elif self.settings.graphicx_option.lower() == 'auto':
            self.graphicx_package = PreambleCmds.graphicx_auto
        else:
            self.graphicx_package = (r'\usepackage[%s]{graphicx}' %
                                     self.settings.graphicx_option)
        # footnotes:
        self.docutils_footnotes = settings.docutils_footnotes
        # @@ table_style: list of values from fixed set: warn?
        # for s in self.settings.table_style:
        #     if s not in Writer.table_style_values:
        #         self.warn('Ignoring value "%s" in "table-style" setting.' %s)

        # Output collection stacks
        # ~~~~~~~~~~~~~~~~~~~~~~~~

        # Document parts
        self.head_prefix = [r'\documentclass[%s]{%s}' %
            (self.documentoptions, self.settings.documentclass)]
        self.requirements = SortableDict() # made a list in depart_document()
        self.requirements['__static'] = r'\usepackage{ifthen}'
        self.latex_preamble = [settings.latex_preamble]
        self.fallbacks = SortableDict() # made a list in depart_document()
        self.pdfsetup = [] # PDF properties (hyperref package)
        self.title = []
        self.subtitle = []
        self.titledata = [] # \title, \author, \date
        ## self.body_prefix = ['\\begin{document}\n']
        self.body_pre_docinfo = [] # \maketitle
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
        # TODO?: pdfcreator, pdfproducer, pdfsubject, pdfkeywords
        self.pdfinfo = []
        self.pdfauthor = []

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

        # object for a table while proccessing.
        self.table_stack = []
        self.active_table = Table(self, 'longtable')

        # Where to collect the output of visitor methods (default: body)
        self.out = self.body
        self.out_stack = []  # stack of output collectors

        # Process settings
        # ~~~~~~~~~~~~~~~~
        # Encodings:
        # Docutils' output-encoding => TeX input encoding
        if self.latex_encoding != 'ascii':
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
        if (settings.documentclass.find('scr') == -1 and
            (self.documentoptions.find('DIV') != -1 or
             self.documentoptions.find('BCOR') != -1)):
            self.requirements['typearea'] = r'\usepackage{typearea}'

        # Stylesheets
        # (the name `self.stylesheet` is singular because only one
        # stylesheet was supported before Docutils 0.6).
        self.stylesheet = [self.stylesheet_call(path)
                           for path in utils.get_stylesheet_list(settings)]

        # PDF setup
        if self.hyperlink_color in ('0', 'false', 'False', ''):
            self.hyperref_options = ''
        else:
            self.hyperref_options = 'colorlinks=true,linkcolor=%s,urlcolor=%s' % (
                                      self.hyperlink_color, self.hyperlink_color)
        if settings.hyperref_options:
            self.hyperref_options += ',' + settings.hyperref_options

        # LaTeX Toc
        # include all supported sections in toc and PDF bookmarks
        # (or use documentclass-default (as currently))?
        ## if self.use_latex_toc:
        ##    self.requirements['tocdepth'] = (r'\setcounter{tocdepth}{%d}' %
        ##                                     len(self.d_class.sections))

        # Section numbering
        if settings.sectnum_xform: # section numbering by Docutils
            PreambleCmds.secnumdepth = r'\setcounter{secnumdepth}{0}'
        else: # section numbering by LaTeX:
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
                # limit to supported levels
                secnumdepth = min(secnumdepth, len(self.d_class.sections))
                # adjust to document class and use_part_section settings
                if 'chapter' in  self.d_class.sections:
                    secnumdepth -= 1
                if self.d_class.sections[0] == 'part':
                    secnumdepth -= 1
                PreambleCmds.secnumdepth = \
                    r'\setcounter{secnumdepth}{%d}' % secnumdepth

            # start with specified number:
            if (hasattr(settings, 'sectnum_start') and
                settings.sectnum_start != 1):
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
        # is it a package (no extension or *.sty) or "normal" tex code:
        (base, ext) = os.path.splitext(path)
        is_package = ext in ['.sty', '']
        # Embed content of style file:
        if self.settings.embed_stylesheet:
            if is_package:
                path = base + '.sty' # ensure extension
            try:
                content = io.FileInput(source_path=path,
                                       encoding='utf-8').read()
                self.settings.record_dependencies.add(path)
            except IOError as err:
                msg = "Cannot embed stylesheet '%s':\n  %s." % (
                                path, SafeString(err.strerror))
                self.document.reporter.error(msg)
                return '% ' + msg.replace('\n', '\n% ')
            if is_package:
                content = '\n'.join([r'\makeatletter',
                                     content,
                                     r'\makeatother'])
            return '%% embedded stylesheet: %s\n%s' % (path, content)
        # Link to style file:
        if is_package:
            path = base # drop extension
            cmd = r'\usepackage{%s}'
        else:
            cmd = r'\input{%s}'
        if self.settings.stylesheet_path:
            # adapt path relative to output (cf. config.html#stylesheet-path)
            path = utils.relative_path(self.settings._destination, path)
        return cmd % path

    def to_latex_encoding(self,docutils_encoding):
        """Translate docutils encoding name into LaTeX's.

        Default method is remove "-" and "_" chars from docutils_encoding.
        """
        tr = {  'iso-8859-1': 'latin1',     # west european
                'iso-8859-2': 'latin2',     # east european
                'iso-8859-3': 'latin3',     # esperanto, maltese
                'iso-8859-4': 'latin4',     # north european, scandinavian, baltic
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
                #'': 'applemac',
                #'': 'ansinew',  # windows 3.1 ansi
                #'': 'ascii',    # ASCII encoding for the range 32--127.
                #'': 'cp437',    # dos latin us
                #'': 'cp850',    # dos latin 1
                #'': 'cp852',    # dos latin 2
                #'': 'decmulti',
                #'': 'latin10',
                #'iso-8859-6': ''   # arabic
                #'iso-8859-7': ''   # greek
                #'iso-8859-8': ''   # hebrew
                #'iso-8859-10': ''   # latin6, more complete iso-8859-4
             }
        encoding = docutils_encoding.lower()
        if encoding in tr:
            return tr[encoding]
        # drop hyphen or low-line from "latin-1", "latin_1", "utf-8" and similar
        encoding = encoding.replace('_', '').replace('-', '')
        # strip the error handler
        return encoding.split(':')[0]

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
        if self.inside_citation_reference_label:
            del(table[ord('_')])
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
                table[ord('\\')] = r'\reflectbox{/}'
            # * ``< | >`` come out as different chars (except for cmtt):
            else:
                table[ord('|')] = r'\textbar{}'
                table[ord('<')] = r'\textless{}'
                table[ord('>')] = r'\textgreater{}'
        if self.insert_non_breaking_blanks:
            table[ord(' ')] = r'~'
        # Unicode replacements for 8-bit tex engines (not required with XeTeX/LuaTeX):
        if not self.is_xetex:
            if not self.latex_encoding.startswith('utf8'):
                table.update(CharMaps.unsupported_unicode)
                table.update(CharMaps.utf8_supported_unicode)
                table.update(CharMaps.textcomp)
            table.update(CharMaps.pifont)
            # Characters that require a feature/package to render
            for ch in text:
                cp = ord(ch)
                if cp in CharMaps.textcomp:
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
        if not self.is_xetex: # Not required with xetex/luatex
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
        # so we raise it explicitely
        self.out.append('%\n'.join(['\\raisebox{1em}{\\hypertarget{%s}{}}' %
                                    id for id in node['ids']]))

    def ids_to_labels(self, node, set_anchor=True):
        """Return list of label definitions for all ids of `node`

        If `set_anchor` is True, an anchor is set with \\phantomsection.
        """
        labels = ['\\label{%s}' % id for id in node.get('ids', [])]
        if set_anchor and labels:
            labels.insert(0, '\\phantomsection')
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
            else:
                self.fallbacks['DUclass'] = PreambleCmds.duclass
                self.out.append('\\begin{DUclass}{%s}\n' % cls)

    def duclass_close(self, node):
        """Close a group of class declarations."""
        for cls in reversed(node['classes']):
            if cls.startswith('language-'):
                language = self.babel.language_name(cls[9:])
                if language:
                    self.babel.otherlanguages[language] = True
                    self.out.append('\\end{selectlanguage}\n')
            else:
                self.fallbacks['DUclass'] = PreambleCmds.duclass
                self.out.append('\\end{DUclass}\n')

    def push_output_collector(self, new_out):
        self.out_stack.append(self.out)
        self.out = new_out

    def pop_output_collector(self):
        self.out = self.out_stack.pop()

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
        self.fallbacks['admonition'] = PreambleCmds.admonition
        if 'error' in node['classes']:
            self.fallbacks['error'] = PreambleCmds.error
        # strip the generic 'admonition' from the list of classes
        node['classes'] = [cls for cls in node['classes']
                           if cls != 'admonition']
        self.out.append('\n\\DUadmonition[%s]{' % ','.join(node['classes']))

    def depart_admonition(self, node=None):
        self.out.append('}\n')

    def visit_author(self, node):
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
        self.out.append( '\\begin{quote}')

    def depart_block_quote(self, node):
        self.out.append( '\\end{quote}\n')
        self.duclass_close(node)

    def visit_bullet_list(self, node):
        self.duclass_open(node)
        if self.is_toc_list:
            self.out.append( '\\begin{list}{}{}' )
        else:
            self.out.append( '\\begin{itemize}' )

    def depart_bullet_list(self, node):
        if self.is_toc_list:
            self.out.append( '\\end{list}\n' )
        else:
            self.out.append( '\\end{itemize}\n' )
        self.duclass_close(node)

    def visit_superscript(self, node):
        self.out.append(r'\textsuperscript{')
        if node['classes']:
            self.visit_inline(node)

    def depart_superscript(self, node):
        if node['classes']:
            self.depart_inline(node)
        self.out.append('}')

    def visit_subscript(self, node):
        self.fallbacks['textsubscript'] = PreambleCmds.textsubscript
        self.out.append(r'\textsubscript{')
        if node['classes']:
            self.visit_inline(node)

    def depart_subscript(self, node):
        if node['classes']:
            self.depart_inline(node)
        self.out.append('}')

    def visit_caption(self, node):
        self.out.append('\n\\caption{')

    def depart_caption(self, node):
        self.out.append('}\n')

    def visit_title_reference(self, node):
        self.fallbacks['titlereference'] = PreambleCmds.titlereference
        self.out.append(r'\DUroletitlereference{')
        if node['classes']:
            self.visit_inline(node)

    def depart_title_reference(self, node):
        if node['classes']:
            self.depart_inline(node)
        self.out.append( '}' )

    def visit_citation(self, node):
        # TODO maybe use cite bibitems
        if self._use_latex_citations:
            self.push_output_collector([])
        else:
            # TODO: do we need these?
            ## self.requirements['~fnt_floats'] = PreambleCmds.footnote_floats
            self.out.append(r'\begin{figure}[b]')
            self.append_hypertargets(node)

    def depart_citation(self, node):
        if self._use_latex_citations:
            label = self.out[0]
            text = ''.join(self.out[1:])
            self._bibitems.append([label, text])
            self.pop_output_collector()
        else:
            self.out.append('\\end{figure}\n')

    def visit_citation_reference(self, node):
        if self._use_latex_citations:
            if not self.inside_citation_reference_label:
                self.out.append(r'\cite{')
                self.inside_citation_reference_label = 1
            else:
                assert self.body[-1] in (' ', '\n'),\
                        'unexpected non-whitespace while in reference label'
                del self.body[-1]
        else:
            href = ''
            if 'refid' in node:
                href = node['refid']
            elif 'refname' in node:
                href = self.document.nameids[node['refname']]
            self.out.append('\\hyperlink{%s}{[' % href)

    def depart_citation_reference(self, node):
        if self._use_latex_citations:
            followup_citation = False
            # check for a following citation separated by a space or newline
            next_siblings = node.traverse(descend=False, siblings=True,
                                          include_self=False)
            if len(next_siblings) > 1:
                next = next_siblings[0]
                if (isinstance(next, nodes.Text) and
                    next.astext() in (' ', '\n')):
                    if next_siblings[1].__class__ == node.__class__:
                        followup_citation = True
            if followup_citation:
                self.out.append(',')
            else:
                self.out.append('}')
                self.inside_citation_reference_label = False
        else:
            self.out.append(']}')

    def visit_classifier(self, node):
        self.out.append( '(\\textbf{' )

    def depart_classifier(self, node):
        self.out.append( '})' )

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
        self.out.append( '\\begin{description}\n' )

    def depart_definition_list(self, node):
        self.out.append( '\\end{description}\n' )
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
            self.fallbacks['_providelength'] = PreambleCmds.providelength
            self.fallbacks['docinfo'] = PreambleCmds.docinfo
            #
            self.docinfo.insert(0, '\n% Docinfo\n'
                                '\\begin{center}\n'
                                '\\begin{tabularx}{\\DUdocinfowidth}{lX}\n')
            self.docinfo.append('\\end{tabularx}\n'
                                '\\end{center}\n')

    def visit_docinfo_item(self, node, name):
        if name == 'author':
            self.pdfauthor.append(self.attval(node.astext()))
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
        if (self.use_latex_docinfo or len(node) and
            isinstance(node[0], nodes.title)):
            self.title_labels += self.ids_to_labels(node, set_anchor=False)

    def depart_document(self, node):
        # Complete header with information gained from walkabout
        # * language setup
        if (self.babel.otherlanguages or
            self.babel.language not in ('', 'english')):
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
        # Complete body
        # * document title (with "use_latex_docinfo" also
        #   'author', 'organization', 'contact', 'address' and 'date')
        if self.title or (
           self.use_latex_docinfo and (self.author_stack or self.date)):
            # with the default template, titledata is written to the preamble
            self.titledata.append('%%% Title Data')
            # \title (empty \title prevents error with \maketitle)
            if self.title:
                self.title.insert(0, '\\phantomsection%\n  ')
            title = [''.join(self.title)] + self.title_labels
            if self.subtitle:
                title += [r'\\ % subtitle',
                          r'\DUdocumentsubtitle{%s}' % ''.join(self.subtitle)
                         ] + self.subtitle_labels
            self.titledata.append(r'\title{%s}' % '%\n  '.join(title))
            # \author (empty \author prevents warning with \maketitle)
            authors = ['\\\\\n'.join(author_entry)
                        for author_entry in self.author_stack]
            self.titledata.append(r'\author{%s}' %
                                      ' \\and\n'.join(authors))
            # \date (empty \date prevents defaulting to \today)
            self.titledata.append(r'\date{%s}' % ', '.join(self.date))
            # \maketitle in the body formats title with LaTeX
            self.body_pre_docinfo.append('\\maketitle\n')

        # * bibliography
        #   TODO insertion point of bibliography should be configurable.
        if self._use_latex_citations and len(self._bibitems)>0:
            if not self.bibtex:
                widest_label = ''
                for bi in self._bibitems:
                    if len(widest_label)<len(bi[0]):
                        widest_label = bi[0]
                self.out.append('\n\\begin{thebibliography}{%s}\n' %
                                 widest_label)
                for bi in self._bibitems:
                    # cite_key: underscores must not be escaped
                    cite_key = bi[0].replace(r'\_','_')
                    self.out.append('\\bibitem[%s]{%s}{%s}\n' %
                                     (bi[0], cite_key, bi[1]))
                self.out.append('\\end{thebibliography}\n')
            else:
                self.out.append('\n\\bibliographystyle{%s}\n' %
                                self.bibtex[0])
                self.out.append('\\bibliography{%s}\n' % self.bibtex[1])
        # * make sure to generate a toc file if needed for local contents:
        if 'minitoc' in self.requirements and not self.has_latex_toc:
            self.out.append('\n\\faketableofcontents % for local ToCs\n')

    def visit_emphasis(self, node):
        self.out.append('\\emph{')
        if node['classes']:
            self.visit_inline(node)

    def depart_emphasis(self, node):
        if node['classes']:
            self.depart_inline(node)
        self.out.append('}')

    # Append column delimiters and advance column counter,
    # if the current cell is a multi-row continuation."""
    def insert_additional_table_colum_delimiters(self):
        while self.active_table.get_rowspan(
                                self.active_table.get_entry_number()):
            self.out.append(' & ')
            self.active_table.visit_entry() # increment cell count

    def visit_entry(self, node):
        # cell separation
        if self.active_table.get_entry_number() == 0:
            self.insert_additional_table_colum_delimiters()
        else:
            self.out.append(' & ')

        # multirow, multicolumn
        if 'morerows' in node and 'morecols' in node:
            raise NotImplementedError('Cells that '
            'span multiple rows *and* columns currently not supported, sorry.')
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
                    (mcols, bar1,
                     self.active_table.get_multicolumn_width(
                        self.active_table.get_entry_number(),
                        mcols),
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

        # if line ends with '{', mask line break to prevent spurious whitespace
        if not self.active_table.colwidths_auto and self.out[-1].endswith("{"):
                self.out.append("%")

        self.active_table.visit_entry() # increment cell count

    def depart_entry(self, node):
        self.out.append(self.context.pop()) # header / not header
        self.out.append(self.context.pop()) # multirow/column
        # insert extra "&"s, if following rows are spanned from above:
        self.insert_additional_table_colum_delimiters()

    def visit_row(self, node):
        self.active_table.visit_row()

    def depart_row(self, node):
        self.out.extend(self.active_table.depart_row())

    def visit_enumerated_list(self, node):
        # enumeration styles:
        types = {'': '',
                  'arabic':'arabic',
                  'loweralpha':'alph',
                  'upperalpha':'Alph',
                  'lowerroman':'roman',
                  'upperroman':'Roman'}
        # the 4 default LaTeX enumeration labels: präfix, enumtype, suffix,
        labels = [('',  'arabic', '.'), #  1.
                  ('(', 'alph',   ')'), # (a)
                  ('',  'roman',  '.'), #  i.
                  ('',  'Alph',   '.')] #  A.

        prefix = ''
        if self.compound_enumerators:
            if (self.section_prefix_for_enumerators and self.section_level
                and not self._enumeration_counters):
                prefix = '.'.join([str(n) for n in
                                   self._section_number[:self.section_level]]
                                 ) + self.section_enumerator_separator
            if self._enumeration_counters:
                prefix += self._enumeration_counters[-1]
        # TODO: use LaTeX default for unspecified label-type?
        #       (needs change of parser)
        prefix += node.get('prefix', '')
        enumtype = types[node.get('enumtype' '')]
        suffix = node.get('suffix', '')

        enumeration_level = len(self._enumeration_counters)+1
        counter_name = 'enum' + roman.toRoman(enumeration_level).lower()
        label = r'%s\%s{%s}%s' % (prefix, enumtype, counter_name, suffix)
        self._enumeration_counters.append(label)

        self.duclass_open(node)
        if enumeration_level <= 4:
            self.out.append('\\begin{enumerate}')
            if (prefix, enumtype, suffix
               ) != labels[enumeration_level-1]:
                self.out.append('\n\\renewcommand{\\label%s}{%s}' %
                                (counter_name, label))
        else:
            self.fallbacks[counter_name] = '\\newcounter{%s}' % counter_name
            self.out.append('\\begin{list}')
            self.out.append('{%s}' % label)
            self.out.append('{\\usecounter{%s}}' % counter_name)
        if 'start' in node:
            self.out.append('\n\\setcounter{%s}{%d}' %
                            (counter_name,node['start']-1))


    def depart_enumerated_list(self, node):
        if len(self._enumeration_counters) <= 4:
            self.out.append('\\end{enumerate}\n')
        else:
            self.out.append('\\end{list}\n')
        self.duclass_close(node)
        self._enumeration_counters.pop()

    def visit_field(self, node):
        # real output is done in siblings: _argument, _body, _name
        pass

    def depart_field(self, node):
        pass
        ##self.out.append('%[depart_field]\n')

    def visit_field_argument(self, node):
        self.out.append('%[visit_field_argument]\n')

    def depart_field_argument(self, node):
        self.out.append('%[depart_field_argument]\n')

    def visit_field_body(self, node):
        pass

    def depart_field_body(self, node):
        if self.out is self.docinfo:
            self.out.append(r'\\'+'\n')

    def visit_field_list(self, node):
        self.duclass_open(node)
        if self.out is not self.docinfo:
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
        self.requirements['float_settings'] = PreambleCmds.float_settings
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
        if node.get('ids'):
            self.out += self.ids_to_labels(node) + ['\n']

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
            backref = node['ids'][0] # no backref, use self-ref instead
        if self.docutils_footnotes:
            self.fallbacks['footnotes'] = PreambleCmds.footnotes
            num = node[0].astext()
            if self.settings.footnote_references == 'brackets':
                num = '[%s]' % num
            self.out.append('%%\n\\DUfootnotetext{%s}{%s}{%s}{' %
                            (node['ids'][0], backref, self.encode(num)))
            if node['ids'] == node['names']:
                self.out += self.ids_to_labels(node)
            # mask newline to prevent spurious whitespace if paragraph follows:
            if node[1:] and isinstance(node[1], nodes.paragraph):
                self.out.append('%')
        ## else:  # TODO: "real" LaTeX \footnote{}s

    def depart_footnote(self, node):
        self.out.append('}\n')

    def visit_footnote_reference(self, node):
        href = ''
        if 'refid' in node:
            href = node['refid']
        elif 'refname' in node:
            href = self.document.nameids[node['refname']]
        # if not self.docutils_footnotes:
            # TODO: insert footnote content at (or near) this place
            # print "footnote-ref to", node['refid']
            # footnotes = (self.document.footnotes +
            #              self.document.autofootnotes +
            #              self.document.symbol_footnotes)
            # for footnote in footnotes:
            #     # print footnote['ids']
            #     if node.get('refid', '') in footnote['ids']:
            #         print 'matches', footnote['ids']
        format = self.settings.footnote_references
        if format == 'brackets':
            self.append_hypertargets(node)
            self.out.append('\\hyperlink{%s}{[' % href)
            self.context.append(']}')
        else:
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
            if not self._use_latex_citations:
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
        """Convert `length_str` with rst lenght to LaTeX length
        """
        if pxunit is not None:
            sys.stderr.write('deprecation warning: LaTeXTranslator.to_latex_length()'
                             ' option `pxunit` will be removed.')
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
            self.fallbacks['_providelength'] = PreambleCmds.providelength
            self.fallbacks['px'] = '\n\\DUprovidelength{\\pdfpxdimen}{1bp}\n'
            length_str = r'%s\pdfpxdimen' % value
        return length_str

    def visit_image(self, node):
        self.requirements['graphicx'] = self.graphicx_package
        attrs = node.attributes
        # Convert image URI to a local file path
        imagepath = urllib.request.url2pathname(attrs['uri']).replace('\\', '/')
        # alignment defaults:
        if not 'align' in attrs:
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
            'right':  (r'\noindent{\hfill', '}'),}
        if 'align' in attrs:
            # TODO: warn or ignore non-applicable alignment settings?
            try:
                align_code = align_codes[attrs['align']]
                pre.append(align_code[0])
                post.append(align_code[1])
            except KeyError:
                pass                    # TODO: warn?
        if 'height' in attrs:
            include_graphics_options.append('height=%s' %
                            self.to_latex_length(attrs['height']))
        if 'scale' in attrs:
            include_graphics_options.append('scale=%f' %
                                            (attrs['scale'] / 100.0))
        if 'width' in attrs:
            include_graphics_options.append('width=%s' %
                            self.to_latex_length(attrs['width']))
        if not (self.is_inline(node) or
                isinstance(node.parent, (nodes.figure, nodes.compound))):
            pre.append('\n')
        if not (self.is_inline(node) or
                isinstance(node.parent, nodes.figure)):
            post.append('\n')
        pre.reverse()
        self.out.extend(pre)
        options = ''
        if include_graphics_options:
            options = '[%s]' % (','.join(include_graphics_options))
        self.out.append('\\includegraphics%s{%s}' % (options, imagepath))
        self.out.extend(post)

    def depart_image(self, node):
        if node.get('ids'):
            self.out += self.ids_to_labels(node) + ['\n']

    def visit_inline(self, node): # <span>, i.e. custom roles
        for cls in node['classes']:
            if cls.startswith('language-'):
                language = self.babel.language_name(cls[9:])
                if language:
                    self.babel.otherlanguages[language] = True
                    self.out.append(r'\foreignlanguage{%s}{' % language)
            else:
                self.fallbacks['inline'] = PreambleCmds.inline
                self.out.append(r'\DUrole{%s}{' % cls)

    def depart_inline(self, node):
        self.out.append('}' * len(node['classes']))

    def visit_interpreted(self, node):
        # @@@ Incomplete, pending a proper implementation on the
        # Parser/Reader end.
        self.visit_literal(node)

    def depart_interpreted(self, node):
        self.depart_literal(node)

    def visit_legend(self, node):
        self.fallbacks['legend'] = PreambleCmds.legend
        self.out.append('\\begin{DUlegend}')

    def depart_legend(self, node):
        self.out.append('\\end{DUlegend}\n')

    def visit_line(self, node):
        self.out.append(r'\item[] ')

    def depart_line(self, node):
        self.out.append('\n')

    def visit_line_block(self, node):
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
        if 'code' in node['classes'] and (
                    self.settings.syntax_highlight != 'none'):
            self.requirements['color'] = PreambleCmds.color
            self.fallbacks['code'] = PreambleCmds.highlight_rules
        self.out.append('\\texttt{')
        if node['classes']:
            self.visit_inline(node)

    def depart_literal(self, node):
        self.literal = False
        if node['classes']:
            self.depart_inline(node)
        self.out.append('}')

    # Literal blocks are used for '::'-prefixed literal-indented
    # blocks of text, where the inline markup is not recognized,
    # but are also the product of the "parsed-literal" directive,
    # where the markup is respected.
    #
    # In both cases, we want to use a typewriter/monospaced typeface.
    # For "real" literal-blocks, we can use \verbatim, while for all
    # the others we must use \mbox or \alltt.
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
        """Render a literal block."""
        # environments and packages to typeset literal blocks
        packages = {'alltt': r'\usepackage{alltt}',
                    'listing': r'\usepackage{moreverb}',
                    'lstlisting': r'\usepackage{listings}',
                    'Verbatim': r'\usepackage{fancyvrb}',
                    # 'verbatim': '',
                    'verbatimtab': r'\usepackage{moreverb}'}

        if node.get('ids'):
            self.out += ['\n'] + self.ids_to_labels(node)

        self.duclass_open(node)
        if not self.active_table.is_open():
            # no quote inside tables, to avoid vertical space between
            # table border and literal block.
            # TODO: fails if normal text precedes the literal block.
            # check parent node instead?
            self.out.append('\\begin{quote}\n')
            self.context.append('\n\\end{quote}\n')
        else:
            self.context.append('\n')

        if self.is_plaintext(node):
            environment = self.literal_block_env
            self.requirements['literal_block'] = packages.get(environment, '')
            if environment == 'alltt':
                self.alltt = True
            else:
                self.verbatim = True
            self.out.append('\\begin{%s}%s\n' %
                            (environment, self.literal_block_options))
            self.context.append('\n\\end{%s}' % environment)
        else:
            self.literal = True
            self.insert_newline = True
            self.insert_non_breaking_blanks = True
            if 'code' in node['classes'] and (
                    self.settings.syntax_highlight != 'none'):
                self.requirements['color'] = PreambleCmds.color
                self.fallbacks['code'] = PreambleCmds.highlight_rules
            self.out.append('{\\ttfamily \\raggedright \\noindent\n')
            self.context.append('\n}')

    def depart_literal_block(self, node):
        self.insert_non_breaking_blanks = False
        self.insert_newline = False
        self.literal = False
        self.verbatim = False
        self.alltt = False
        self.out.append(self.context.pop())
        self.out.append(self.context.pop())
        self.duclass_close(node)

    ## def visit_meta(self, node):
    ##     self.out.append('[visit_meta]\n')
        # TODO: set keywords for pdf?
        # But:
        #  The reStructuredText "meta" directive creates a "pending" node,
        #  which contains knowledge that the embedded "meta" node can only
        #  be handled by HTML-compatible writers. The "pending" node is
        #  resolved by the docutils.transforms.components.Filter transform,
        #  which checks that the calling writer supports HTML; if it doesn't,
        #  the "pending" node (and enclosed "meta" node) is removed from the
        #  document.
        #  --- docutils/docs/peps/pep-0258.html#transformer

    ## def depart_meta(self, node):
    ##     self.out.append('[depart_meta]\n')

    def visit_math(self, node, math_env='$'):
        """math role"""
        if node['classes']:
            self.visit_inline(node)
        self.requirements['amsmath'] = r'\usepackage{amsmath}'
        math_code = node.astext().translate(unichar2tex.uni2tex_table)
        if node.get('ids'):
            math_code = '\n'.join([math_code] + self.ids_to_labels(node))
        if math_env == '$':
            if self.alltt:
                wrapper = r'\(%s\)'
            else:
                wrapper = '$%s$'
        else:
            wrapper = '\n'.join(['%%',
                                 r'\begin{%s}' % math_env,
                                 '%s',
                                 r'\end{%s}' % math_env])
        # print repr(wrapper), repr(math_code)
        self.out.append(wrapper % math_code)
        if node['classes']:
            self.depart_inline(node)
        # Content already processed:
        raise nodes.SkipNode

    def depart_math(self, node):
        pass # never reached

    def visit_math_block(self, node):
        math_env = pick_math_environment(node.astext())
        self.visit_math(node, math_env=math_env)

    def depart_math_block(self, node):
        pass # never reached

    def visit_option(self, node):
        if self.context[-1]:
            # this is not the first option
            self.out.append(', ')

    def depart_option(self, node):
        # flag that the first option is done.
        self.context[-1] += 1

    def visit_option_argument(self, node):
        """Append the delimiter betweeen an option and its argument to body."""
        self.out.append(node.get('delimiter', ' '))

    def depart_option_argument(self, node):
        pass

    def visit_option_group(self, node):
        self.out.append('\n\\item[')
        # flag for first option
        self.context.append(0)

    def depart_option_group(self, node):
        self.context.pop() # the flag
        self.out.append('] ')

    def visit_option_list(self, node):
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
        ##self.out.append(self.starttag(node, 'span', '', CLASS='option'))
        pass

    def depart_option_string(self, node):
        ##self.out.append('</span>')
        pass

    def visit_organization(self, node):
        self.visit_docinfo_item(node, 'organization')

    def depart_organization(self, node):
        self.depart_docinfo_item(node)

    def visit_paragraph(self, node):
        # insert blank line, unless
        # * the paragraph is first in a list item or compound,
        # * follows a non-paragraph node in a compound,
        # * is in a table with auto-width columns
        index = node.parent.index(node)
        if index == 0 and isinstance(node.parent,
                (nodes.list_item, nodes.description, nodes.compound)):
            pass
        elif (index > 0 and isinstance(node.parent, nodes.compound) and
              not isinstance(node.parent[index - 1], nodes.paragraph) and
              not isinstance(node.parent[index - 1], nodes.compound)):
            pass
        elif self.active_table.colwidths_auto:
            if index == 1: # second paragraph
                self.warn('LaTeX merges paragraphs in tables '
                          'with auto-sized columns!', base_node=node)
            if index > 0:
                self.out.append('\n')
        else:
            self.out.append('\n')
        if node.get('ids'):
            self.out += self.ids_to_labels(node) + ['\n']
        if node['classes']:
            self.visit_inline(node)

    def depart_paragraph(self, node):
        if node['classes']:
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
        if not 'latex' in node.get('format', '').split():
            raise nodes.SkipNode
        if not self.is_inline(node):
            self.out.append('\n')
        if node['classes']:
            self.visit_inline(node)
        # append "as-is" skipping any LaTeX-encoding
        self.verbatim = True

    def depart_raw(self, node):
        self.verbatim = False
        if node['classes']:
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
        special_chars = {ord('#'): r'\#',
                         ord('%'): r'\%',
                         ord('\\'): r'\\',
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
        self.fallbacks['rubric'] = PreambleCmds.rubric
        self.duclass_open(node)
        self.out.append('\\DUrubric{')

    def depart_rubric(self, node):
        self.out.append('}\n')
        self.duclass_close(node)

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
        self.fallbacks['sidebar'] = PreambleCmds.sidebar
        self.out.append('\\DUsidebar{')

    def depart_sidebar(self, node):
        self.out.append('}\n')
        self.duclass_close(node)

    attribution_formats = {'dash': ('—', ''), # EM DASH
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
        if node['classes']:
            self.visit_inline(node)

    def depart_strong(self, node):
        if node['classes']:
            self.depart_inline(node)
        self.out.append('}')

    def visit_substitution_definition(self, node):
        raise nodes.SkipNode

    def visit_substitution_reference(self, node):
        self.unimplemented_visit(node)

    def visit_subtitle(self, node):
        if isinstance(node.parent, nodes.document):
            self.push_output_collector(self.subtitle)
            self.fallbacks['documentsubtitle'] = PreambleCmds.documentsubtitle
            self.subtitle_labels += self.ids_to_labels(node, set_anchor=False)
        # section subtitle: "starred" (no number, not in ToC)
        elif isinstance(node.parent, nodes.section):
            self.out.append(r'\%s*{' %
                             self.d_class.section(self.section_level + 1))
        else:
            self.fallbacks['subtitle'] = PreambleCmds.subtitle
            self.out.append('\n\\DUsubtitle[%s]{' % node.parent.tagname)

    def depart_subtitle(self, node):
        if isinstance(node.parent, nodes.document):
            self.pop_output_collector()
        else:
            self.out.append('}\n')

    def visit_system_message(self, node):
        self.requirements['color'] = PreambleCmds.color
        self.fallbacks['title'] = PreambleCmds.title
        node['classes'] = ['system-message']
        self.visit_admonition(node)
        self.out.append('\n\\DUtitle[system-message]{system-message}\n')
        self.append_hypertargets(node)
        try:
            line = ', line~%s' % node['line']
        except KeyError:
            line = ''
        self.out.append('\n\n{\\color{red}%s/%s} in \\texttt{%s}%s\n' %
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
        self.depart_admonition()

    def visit_table(self, node):
        self.requirements['table'] = PreambleCmds.table
        if self.active_table.is_open():
            self.table_stack.append(self.active_table)
            # nesting longtable does not work (e.g. 2007-04-18)
            self.active_table = Table(self,'tabular')
        # A longtable moves before \paragraph and \subparagraph
        # section titles if it immediately follows them:
        if (self.active_table._latex_type == 'longtable' and
            isinstance(node.parent, nodes.section) and
            node.parent.index(node) == 1 and
            self.d_class.section(self.section_level).find('paragraph') != -1):
            self.out.append('\\leavevmode')
        self.active_table.open()
        self.active_table.set_table_style(self.settings.table_style,
                                          node['classes'])
        if 'align' in node:
            self.active_table.set('align', node['align'])
        if self.active_table.borders == 'booktabs':
            self.requirements['booktabs'] = r'\usepackage{booktabs}'
        self.push_output_collector([])

    def depart_table(self, node):
        # wrap content in the right environment:
        content = self.out
        self.pop_output_collector()
        self.out.append('\n' + self.active_table.get_opening())
        self.out += content
        self.out.append(self.active_table.get_closing() + '\n')
        self.active_table.close()
        if len(self.table_stack)>0:
            self.active_table = self.table_stack.pop()
        # Insert hyperlabel after (long)table, as
        # other places (beginning, caption) result in LaTeX errors.
        if node.get('ids'):
            self.out += self.ids_to_labels(node, set_anchor=False) + ['\n']

    def visit_target(self, node):
        # Skip indirect targets:
        if ('refuri' in node       # external hyperlink
            or 'refid' in node     # resolved internal link
            or 'refname' in node): # unresolved internal link
            ## self.out.append('%% %s\n' % node)   # for debugging
            return
        self.out.append('%\n')
        # do we need an anchor (\phantomsection)?
        set_anchor = not(isinstance(node.parent, nodes.caption) or
                         isinstance(node.parent, nodes.title))
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
        # \leavevmode results in a line break if the
        # term is followed by an item list.
        self.out.append('}] \leavevmode ')

    def visit_tgroup(self, node):
        #self.out.append(self.starttag(node, 'colgroup'))
        #self.context.append('</colgroup>\n')
        pass

    def depart_tgroup(self, node):
        pass

    _thead_depth = 0
    def thead_depth (self):
        return self._thead_depth

    def visit_thead(self, node):
        self._thead_depth += 1
        if 1 == self.thead_depth():
            self.out.append('{%s}\n' % self.active_table.get_colspecs(node))
            self.active_table.set('preamble written',1)
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
        if node.parent.tagname == 'document':
            self.push_output_collector(self.title)
            self.context.append('')
            self.pdfinfo.append('  pdftitle={%s},' %
                                self.encode(node.astext()))
        # Topic titles (topic, admonition, sidebar)
        elif (isinstance(node.parent, nodes.topic) or
              isinstance(node.parent, nodes.admonition) or
              isinstance(node.parent, nodes.sidebar)):
            self.fallbacks['title'] = PreambleCmds.title
            classes = ','.join(node.parent['classes'])
            if not classes:
                classes = node.tagname
            self.out.append('\n\\DUtitle[%s]{' % classes)
            self.context.append('}\n')
        # Table caption
        elif isinstance(node.parent, nodes.table):
            self.push_output_collector(self.active_table.caption)
            self.context.append('')
        # Section title
        else:
            if hasattr(PreambleCmds, 'secnumdepth'):
                self.requirements['secnumdepth'] = PreambleCmds.secnumdepth
            section_name = self.d_class.section(self.section_level)
            self.out.append('\n\n')
            # System messages heading in red:
            if ('system-messages' in node.parent['classes']):
                self.requirements['color'] = PreambleCmds.color
                section_title = self.encode(node.astext())
                self.out.append(r'\%s[%s]{\color{red}' % (
                                section_name,section_title))
            else:
                self.out.append(r'\%s{' % section_name)
            if self.section_level > len(self.d_class.sections):
                # section level not supported by LaTeX
                self.fallbacks['title'] = PreambleCmds.title
                # self.out.append('\\phantomsection%\n  ')
            # label and ToC entry:
            bookmark = ['']
            # add sections with unsupported level to toc and pdfbookmarks?
            ## if self.section_level > len(self.d_class.sections):
            ##     section_title = self.encode(node.astext())
            ##     bookmark.append(r'\addcontentsline{toc}{%s}{%s}' %
            ##               (section_name, section_title))
            bookmark += self.ids_to_labels(node.parent, set_anchor=False)
            self.context.append('%\n  '.join(bookmark) + '%\n}\n')

            # MAYBE postfix paragraph and subparagraph with \leavemode to
            # ensure floats stay in the section and text starts on a new line.

    def depart_title(self, node):
        self.out.append(self.context.pop())
        if (isinstance(node.parent, nodes.table) or
            node.parent.tagname == 'document'):
            self.pop_output_collector()

    def minitoc(self, node, title, depth):
        """Generate a local table of contents with LaTeX package minitoc"""
        section_name = self.d_class.section(self.section_level)
        # name-prefix for current section level
        minitoc_names = {'part': 'part', 'chapter': 'mini'}
        if 'chapter' not in self.d_class.sections:
            minitoc_names['section'] = 'sect'
        try:
            minitoc_name = minitoc_names[section_name]
        except KeyError: # minitoc only supports part- and toplevel
            self.warn('Skipping local ToC at %s level.\n' % section_name +
                      '  Feature not supported with option "use-latex-toc"',
                      base_node=node)
            return
        # Requirements/Setup
        self.requirements['minitoc'] = PreambleCmds.minitoc
        self.requirements['minitoc-'+minitoc_name] = (r'\do%stoc' %
                                                      minitoc_name)
        # depth: (Docutils defaults to unlimited depth)
        maxdepth = len(self.d_class.sections)
        self.requirements['minitoc-%s-depth' % minitoc_name] = (
            r'\mtcsetdepth{%stoc}{%d}' % (minitoc_name, maxdepth))
        # Process 'depth' argument (!Docutils stores a relative depth while
        # minitoc  expects an absolute depth!):
        offset = {'sect': 1, 'mini': 0, 'part': 0}
        if 'chapter' in self.d_class.sections:
            offset['part'] = -1
        if depth:
            self.out.append('\\setcounter{%stocdepth}{%d}' %
                             (minitoc_name, depth + offset[minitoc_name]))
        # title:
        self.out.append('\\mtcsettitle{%stoc}{%s}\n' % (minitoc_name, title))
        # the toc-generating command:
        self.out.append('\\%stoc\n' % minitoc_name)

    def visit_topic(self, node):
        # Topic nodes can be generic topic, abstract, dedication, or ToC.
        # table of contents:
        if 'contents' in node['classes']:
            self.out.append('\n')
            self.out += self.ids_to_labels(node)
            # add contents to PDF bookmarks sidebar
            if isinstance(node.next_node(), nodes.title):
                self.out.append('\n\\pdfbookmark[%d]{%s}{%s}' %
                                (self.section_level+1,
                                 node.next_node().astext(),
                                 node.get('ids', ['contents'])[0]
                                ))
            if self.use_latex_toc:
                title = ''
                if isinstance(node.next_node(), nodes.title):
                    title = self.encode(node.pop(0).astext())
                depth = node.get('depth', 0)
                if 'local' in node['classes']:
                    self.minitoc(node, title, depth)
                    return
                if depth:
                    self.out.append('\\setcounter{tocdepth}{%d}\n' % depth)
                if title != 'Contents':
                    self.out.append('\n\\renewcommand{\\contentsname}{%s}' %
                                    title)
                self.out.append('\n\\tableofcontents\n')
                self.has_latex_toc = True
            else: # Docutils generated contents list
                # set flag for visit_bullet_list() and visit_title()
                self.is_toc_list = True
        elif ('abstract' in node['classes'] and
              self.settings.use_latex_abstract):
            self.push_output_collector(self.abstract)
            self.out.append('\\begin{abstract}')
            if isinstance(node.next_node(), nodes.title):
                node.pop(0) # LaTeX provides its own title
        else:
            # special topics:
            if 'abstract' in node['classes']:
                self.fallbacks['abstract'] = PreambleCmds.abstract
                self.push_output_collector(self.abstract)
            elif 'dedication' in node['classes']:
                self.fallbacks['dedication'] = PreambleCmds.dedication
                self.push_output_collector(self.dedication)
            else:
                node['classes'].insert(0, 'topic')
            self.visit_block_quote(node)

    def depart_topic(self, node):
        self.is_toc_list = False
        if ('abstract' in node['classes']
          and self.settings.use_latex_abstract):
            self.out.append('\\end{abstract}\n')
        elif not 'contents' in node['classes']:
            self.depart_block_quote(node)
        if ('abstract' in node['classes'] or
            'dedication' in node['classes']):
            self.pop_output_collector()

    def visit_transition(self, node):
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
