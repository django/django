"""constants for LaTeX builder."""

from __future__ import annotations

from typing import Any

PDFLATEX_DEFAULT_FONTPKG = r'''
\usepackage{tgtermes}
\usepackage{tgheros}
\renewcommand{\ttdefault}{txtt}
'''

PDFLATEX_DEFAULT_FONTSUBSTITUTION = r'''
\expandafter\ifx\csname T@LGR\endcsname\relax
\else
% LGR was declared as font encoding
  \substitutefont{LGR}{\rmdefault}{cmr}
  \substitutefont{LGR}{\sfdefault}{cmss}
  \substitutefont{LGR}{\ttdefault}{cmtt}
\fi
\expandafter\ifx\csname T@X2\endcsname\relax
  \expandafter\ifx\csname T@T2A\endcsname\relax
  \else
  % T2A was declared as font encoding
    \substitutefont{T2A}{\rmdefault}{cmr}
    \substitutefont{T2A}{\sfdefault}{cmss}
    \substitutefont{T2A}{\ttdefault}{cmtt}
  \fi
\else
% X2 was declared as font encoding
  \substitutefont{X2}{\rmdefault}{cmr}
  \substitutefont{X2}{\sfdefault}{cmss}
  \substitutefont{X2}{\ttdefault}{cmtt}
\fi
'''

XELATEX_DEFAULT_FONTPKG = r'''
\setmainfont{FreeSerif}[
  Extension      = .otf,
  UprightFont    = *,
  ItalicFont     = *Italic,
  BoldFont       = *Bold,
  BoldItalicFont = *BoldItalic
]
\setsansfont{FreeSans}[
  Extension      = .otf,
  UprightFont    = *,
  ItalicFont     = *Oblique,
  BoldFont       = *Bold,
  BoldItalicFont = *BoldOblique,
]
\setmonofont{FreeMono}[
  Extension      = .otf,
  UprightFont    = *,
  ItalicFont     = *Oblique,
  BoldFont       = *Bold,
  BoldItalicFont = *BoldOblique,
]
'''

XELATEX_GREEK_DEFAULT_FONTPKG = (XELATEX_DEFAULT_FONTPKG +
                                 '\n\\newfontfamily\\greekfont{FreeSerif}' +
                                 '\n\\newfontfamily\\greekfontsf{FreeSans}' +
                                 '\n\\newfontfamily\\greekfonttt{FreeMono}')

LUALATEX_DEFAULT_FONTPKG = XELATEX_DEFAULT_FONTPKG

DEFAULT_SETTINGS: dict[str, Any] = {
    'latex_engine':    'pdflatex',
    'papersize':       '',
    'pointsize':       '',
    'pxunit':          '.75bp',
    'classoptions':    '',
    'extraclassoptions': '',
    'maxlistdepth':    '',
    'sphinxpkgoptions':     '',
    'sphinxsetup':     '',
    'fvset':           '\\fvset{fontsize=auto}',
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
    'fontpkg':         PDFLATEX_DEFAULT_FONTPKG,
    'fontsubstitution': PDFLATEX_DEFAULT_FONTSUBSTITUTION,
    'substitutefont':  '',
    'textcyrillic':    '',
    'textgreek':       '\\usepackage{textalpha}',
    'fncychap':        '\\usepackage[Bjarne]{fncychap}',
    'hyperref':        ('% Include hyperref last.\n'
                        '\\usepackage{hyperref}\n'
                        '% Fix anchor placement for figures with captions.\n'
                        '\\usepackage{hypcap}% it must be loaded after hyperref.\n'
                        '% Set up styles of URL: it should be placed after hyperref.\n'
                        '\\urlstyle{same}'),
    'contentsname':    '',
    'extrapackages':   '',
    'preamble':        '',
    'title':           '',
    'release':         '',
    'author':          '',
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
}

ADDITIONAL_SETTINGS: dict[Any, dict[str, Any]] = {
    'pdflatex': {
        'inputenc':     '\\usepackage[utf8]{inputenc}',
        'utf8extra':   ('\\ifdefined\\DeclareUnicodeCharacter\n'
                        '% support both utf8 and utf8x syntaxes\n'
                        '  \\ifdefined\\DeclareUnicodeCharacterAsOptional\n'
                        '    \\def\\sphinxDUC#1{\\DeclareUnicodeCharacter{"#1}}\n'
                        '  \\else\n'
                        '    \\let\\sphinxDUC\\DeclareUnicodeCharacter\n'
                        '  \\fi\n'
                        '  \\sphinxDUC{00A0}{\\nobreakspace}\n'
                        '  \\sphinxDUC{2500}{\\sphinxunichar{2500}}\n'
                        '  \\sphinxDUC{2502}{\\sphinxunichar{2502}}\n'
                        '  \\sphinxDUC{2514}{\\sphinxunichar{2514}}\n'
                        '  \\sphinxDUC{251C}{\\sphinxunichar{251C}}\n'
                        '  \\sphinxDUC{2572}{\\textbackslash}\n'
                        '\\fi'),
    },
    'xelatex': {
        'latex_engine': 'xelatex',
        'polyglossia':  '\\usepackage{polyglossia}',
        'babel':        '',
        'fontenc':     ('\\usepackage{fontspec}\n'
                        '\\defaultfontfeatures[\\rmfamily,\\sffamily,\\ttfamily]{}'),
        'fontpkg':      XELATEX_DEFAULT_FONTPKG,
        'fvset':        '\\fvset{fontsize=\\small}',
        'fontsubstitution': '',
        'textgreek':    '',
        'utf8extra':   ('\\catcode`^^^^00a0\\active\\protected\\def^^^^00a0'
                        '{\\leavevmode\\nobreak\\ }'),
    },
    'lualatex': {
        'latex_engine': 'lualatex',
        'polyglossia':  '\\usepackage{polyglossia}',
        'babel':        '',
        'fontenc':     ('\\usepackage{fontspec}\n'
                        '\\defaultfontfeatures[\\rmfamily,\\sffamily,\\ttfamily]{}'),
        'fontpkg':      LUALATEX_DEFAULT_FONTPKG,
        'fvset':        '\\fvset{fontsize=\\small}',
        'fontsubstitution': '',
        'textgreek':    '',
        'utf8extra':   ('\\catcode`^^^^00a0\\active\\protected\\def^^^^00a0'
                        '{\\leavevmode\\nobreak\\ }'),
    },
    'platex': {
        'latex_engine': 'platex',
        'babel':        '',
        'classoptions': ',dvipdfmx',
        'fontpkg':      PDFLATEX_DEFAULT_FONTPKG,
        'fontsubstitution': '',
        'textgreek':    '',
        'fncychap':     '',
        'geometry':     '\\usepackage[dvipdfm]{geometry}',
    },
    'uplatex': {
        'latex_engine': 'uplatex',
        'babel':        '',
        'classoptions': ',dvipdfmx',
        'fontpkg':      PDFLATEX_DEFAULT_FONTPKG,
        'fontsubstitution': '',
        'textgreek':    '',
        'fncychap':     '',
        'geometry':     '\\usepackage[dvipdfm]{geometry}',
    },

    # special settings for latex_engine + language_code
    ('xelatex', 'fr'): {
        # use babel instead of polyglossia by default
        'polyglossia':  '',
        'babel':        '\\usepackage{babel}',
    },
    ('xelatex', 'zh'): {
        'polyglossia':  '',
        'babel':        '\\usepackage{babel}',
        'fontenc':      '\\usepackage{xeCJK}',
        # set formatcom=\xeCJKVerbAddon to prevent xeCJK from adding extra spaces in
        # fancyvrb Verbatim environment.
        'fvset':        '\\fvset{fontsize=\\small,formatcom=\\xeCJKVerbAddon}',
    },
    ('xelatex', 'el'): {
        'fontpkg':      XELATEX_GREEK_DEFAULT_FONTPKG,
    },
}


SHORTHANDOFF = r'''
\ifdefined\shorthandoff
  \ifnum\catcode`\=\string=\active\shorthandoff{=}\fi
  \ifnum\catcode`\"=\active\shorthandoff{"}\fi
\fi
'''
