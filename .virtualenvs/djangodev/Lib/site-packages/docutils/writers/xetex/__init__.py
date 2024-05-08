#!/usr/bin/env python3
# :Author: Günter Milde <milde@users.sf.net>
# :Revision: $Revision: 9293 $
# :Date: $Date: 2022-12-01 22:13:54 +0100 (Do, 01. Dez 2022) $
# :Copyright: © 2010 Günter Milde.
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: https://opensource.org/licenses/BSD-2-Clause

"""
XeLaTeX document tree Writer.

A variant of Docutils' standard 'latex2e' writer producing LaTeX output
suited for processing with the Unicode-aware TeX engines
LuaTeX and XeTeX.
"""

__docformat__ = 'reStructuredText'

from docutils import frontend
from docutils.writers import latex2e


class Writer(latex2e.Writer):
    """A writer for Unicode-aware LaTeX variants (XeTeX, LuaTeX)"""

    supported = ('latex', 'tex', 'xetex', 'xelatex', 'luatex', 'lualatex')
    """Formats this writer supports."""

    default_template = 'xelatex.tex'
    default_preamble = """\
% Linux Libertine (free, wide coverage, not only for Linux)
\\setmainfont{Linux Libertine O}
\\setsansfont{Linux Biolinum O}
\\setmonofont[HyphenChar=None,Scale=MatchLowercase]{DejaVu Sans Mono}"""

    config_section = 'xetex writer'
    config_section_dependencies = ('writers', 'latex writers')

    # use a copy of the parent spec with some modifications:
    settings_spec = frontend.filter_settings_spec(
        latex2e.Writer.settings_spec,
        # removed settings
        'font_encoding',
        # changed settings:
        template=('Template file. Default: "%s".' % default_template,
                  ['--template'],
                  {'default': default_template, 'metavar': '<file>'}),
        latex_preamble=('Customization by LaTeX code in the preamble. '
                        'Default: select "Linux Libertine" fonts.',
                        ['--latex-preamble'],
                        {'default': default_preamble}),
        )

    def __init__(self):
        latex2e.Writer.__init__(self)
        self.settings_defaults.update({'fontencoding': ''})  # use default (TU)
        self.translator_class = XeLaTeXTranslator


class Babel(latex2e.Babel):
    """Language specifics for XeTeX.

    Use `polyglossia` instead of `babel` and adapt settings.
    """
    language_codes = latex2e.Babel.language_codes.copy()
    # Additionally supported or differently named languages:
    language_codes.update({
        # code        Polyglossia-name  comment
        'cop':        'coptic',
        'de':         'german',         # new spelling (de_1996)
        'de-1901':    'ogerman',        # old spelling
        'dv':         'divehi',         # Maldivian
        'dsb':        'lsorbian',
        'el-polyton': 'polygreek',
        'fa':         'farsi',
        'grc':        'ancientgreek',
        'ko':         'korean',
        'hsb':        'usorbian',
        'sh-Cyrl':    'serbian',        # Serbo-Croatian, Cyrillic script
        'sh-Latn':    'croatian',       # Serbo-Croatian, Latin script
        'sq':         'albanian',
        'sr':         'serbian',        # Cyrillic script (sr-Cyrl)
        'th':         'thai',
        'vi':         'vietnamese',
        # zh-Latn:    ???               # Chinese Pinyin
        })
    # normalize (downcase) keys
    language_codes = {k.lower(): v for k, v in language_codes.items()}

    # Languages without Polyglossia support:
    for key in ('af',           # 'afrikaans',
                'de-AT',        # 'naustrian',
                'de-AT-1901',   # 'austrian',
                # TODO: use variant=... for English variants
                'en-CA',        # 'canadian',
                'en-GB',        # 'british',
                'en-NZ',        # 'newzealand',
                'en-US',        # 'american',
                'fr-CA',        # 'canadien',
                'grc-ibycus',   # 'ibycus', (Greek Ibycus encoding)
                'sr-Latn',      # 'serbian script=latin'
                ):
        del language_codes[key.lower()]

    def __init__(self, language_code, reporter):
        self.language_code = language_code
        self.reporter = reporter
        self.language = self.language_name(language_code)
        self.otherlanguages = {}
        self.warn_msg = 'Language "%s" not supported by Polyglossia.'
        self.quote_index = 0
        self.quotes = ('"', '"')
        # language dependent configuration:
        # double quotes are "active" in some languages (e.g. German).
        self.literal_double_quote = '"'  # TODO: use \textquotedbl ?

    def __call__(self):
        setup = [r'\usepackage{polyglossia}',
                 r'\setdefaultlanguage{%s}' % self.language]
        if self.otherlanguages:
            setup.append(r'\setotherlanguages{%s}' %
                         ','.join(sorted(self.otherlanguages.keys())))
        return '\n'.join(setup)


class XeLaTeXTranslator(latex2e.LaTeXTranslator):
    """
    Generate code for LaTeX using Unicode fonts (XeLaTex or LuaLaTeX).

    See the docstring of docutils.writers._html_base.HTMLTranslator for
    notes on and examples of safe subclassing.
    """

    def __init__(self, document):
        self.is_xetex = True  # typeset with XeTeX or LuaTeX engine
        latex2e.LaTeXTranslator.__init__(self, document, Babel)
        if self.latex_encoding == 'utf8':
            self.requirements.pop('_inputenc', None)
        else:
            self.requirements['_inputenc'] = (r'\XeTeXinputencoding %s '
                                              % self.latex_encoding)
