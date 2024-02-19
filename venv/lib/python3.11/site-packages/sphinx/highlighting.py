"""Highlight code blocks using Pygments."""

from __future__ import annotations

from functools import partial
from importlib import import_module
from typing import TYPE_CHECKING, Any

from pygments import highlight
from pygments.filters import ErrorToken
from pygments.formatters import HtmlFormatter, LatexFormatter
from pygments.lexers import (
    CLexer,
    PythonConsoleLexer,
    PythonLexer,
    RstLexer,
    TextLexer,
    get_lexer_by_name,
    guess_lexer,
)
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound

from sphinx.locale import __
from sphinx.pygments_styles import NoneStyle, SphinxStyle
from sphinx.util import logging, texescape

if TYPE_CHECKING:
    from pygments.formatter import Formatter
    from pygments.lexer import Lexer
    from pygments.style import Style

logger = logging.getLogger(__name__)

lexers: dict[str, Lexer] = {}
lexer_classes: dict[str, type[Lexer] | partial[Lexer]] = {
    'none': partial(TextLexer, stripnl=False),
    'python': partial(PythonLexer, stripnl=False),
    'pycon': partial(PythonConsoleLexer, stripnl=False),
    'rest': partial(RstLexer, stripnl=False),
    'c': partial(CLexer, stripnl=False),
}


escape_hl_chars = {ord('\\'): '\\PYGZbs{}',
                   ord('{'): '\\PYGZob{}',
                   ord('}'): '\\PYGZcb{}'}

# used if Pygments is available
# MEMO: no use of \protected here to avoid having to do hyperref extras,
# (if in future code highlighting in sectioning titles is activated):
# the definitions here use only robust, protected or chardef tokens,
# which are all known to the hyperref re-encoding for bookmarks.
# The " is troublesome because we would like to use \text\textquotedbl
# but \textquotedbl is *defined to raise an error* (!) if the font
# encoding is OT1.  This however could happen from 'fontenc' key.
# MEMO: the Pygments escapes with \char`\<char> syntax, if the document
# uses old OT1 font encoding, work correctly only in monospace font.
# MEMO: the Pygmentize output mark-up is always with a {} after.
_LATEX_ADD_STYLES = r'''
% Sphinx redefinitions
% Originally to obtain a straight single quote via package textcomp, then
% to fix problems for the 5.0.0 inline code highlighting (captions!).
% The \text is from amstext, a dependency of sphinx.sty.  It is here only
% to avoid build errors if for some reason expansion is in math mode.
\def\PYGZbs{\text\textbackslash}
\def\PYGZus{\_}
\def\PYGZob{\{}
\def\PYGZcb{\}}
\def\PYGZca{\text\textasciicircum}
\def\PYGZam{\&}
\def\PYGZlt{\text\textless}
\def\PYGZgt{\text\textgreater}
\def\PYGZsh{\#}
\def\PYGZpc{\%}
\def\PYGZdl{\$}
\def\PYGZhy{\sphinxhyphen}% defined in sphinxlatexstyletext.sty
\def\PYGZsq{\text\textquotesingle}
\def\PYGZdq{"}
\def\PYGZti{\text\textasciitilde}
\makeatletter
% use \protected to allow syntax highlighting in captions
\protected\def\PYG#1#2{\PYG@reset\PYG@toks#1+\relax+{\PYG@do{#2}}}
\makeatother
'''


class PygmentsBridge:
    # Set these attributes if you want to have different Pygments formatters
    # than the default ones.
    html_formatter = HtmlFormatter
    latex_formatter = LatexFormatter

    def __init__(self, dest: str = 'html', stylename: str = 'sphinx',
                 latex_engine: str | None = None) -> None:
        self.dest = dest
        self.latex_engine = latex_engine

        style = self.get_style(stylename)
        self.formatter_args: dict[str, Any] = {'style': style}
        if dest == 'html':
            self.formatter = self.html_formatter
        else:
            self.formatter = self.latex_formatter
            self.formatter_args['commandprefix'] = 'PYG'

    def get_style(self, stylename: str) -> Style:
        if stylename is None or stylename == 'sphinx':
            return SphinxStyle
        elif stylename == 'none':
            return NoneStyle
        elif '.' in stylename:
            module, stylename = stylename.rsplit('.', 1)
            return getattr(import_module(module), stylename)
        else:
            return get_style_by_name(stylename)

    def get_formatter(self, **kwargs: Any) -> Formatter:
        kwargs.update(self.formatter_args)
        return self.formatter(**kwargs)

    def get_lexer(self, source: str, lang: str, opts: dict | None = None,
                  force: bool = False, location: Any = None) -> Lexer:
        if not opts:
            opts = {}

        # find out which lexer to use
        if lang in {'py', 'python', 'py3', 'python3', 'default'}:
            if source.startswith('>>>'):
                # interactive session
                lang = 'pycon'
            else:
                lang = 'python'
        if lang == 'pycon3':
            lang = 'pycon'

        if lang in lexers:
            # just return custom lexers here (without installing raiseonerror filter)
            return lexers[lang]
        elif lang in lexer_classes:
            lexer = lexer_classes[lang](**opts)
        else:
            try:
                if lang == 'guess':
                    lexer = guess_lexer(source, **opts)
                else:
                    lexer = get_lexer_by_name(lang, **opts)
            except ClassNotFound:
                logger.warning(__('Pygments lexer name %r is not known'), lang,
                               location=location)
                lexer = lexer_classes['none'](**opts)

        if not force:
            lexer.add_filter('raiseonerror')

        return lexer

    def highlight_block(self, source: str, lang: str, opts: dict | None = None,
                        force: bool = False, location: Any = None, **kwargs: Any) -> str:
        if not isinstance(source, str):
            source = source.decode()

        lexer = self.get_lexer(source, lang, opts, force, location)

        # highlight via Pygments
        formatter = self.get_formatter(**kwargs)
        try:
            hlsource = highlight(source, lexer, formatter)
        except ErrorToken as err:
            # this is most probably not the selected language,
            # so let it pass un highlighted
            if lang == 'default':
                lang = 'none'  # automatic highlighting failed.
            else:
                logger.warning(
                    __('Lexing literal_block %r as "%s" resulted in an error at token: %r. '
                       'Retrying in relaxed mode.'),
                    source, lang, str(err),
                    type='misc', subtype='highlighting_failure',
                    location=location)
                if force:
                    lang = 'none'
                else:
                    force = True
            lexer = self.get_lexer(source, lang, opts, force, location)
            hlsource = highlight(source, lexer, formatter)

        if self.dest == 'html':
            return hlsource
        else:
            # MEMO: this is done to escape Unicode chars with non-Unicode engines
            return texescape.hlescape(hlsource, self.latex_engine)

    def get_stylesheet(self) -> str:
        formatter = self.get_formatter()
        if self.dest == 'html':
            return formatter.get_style_defs('.highlight')
        else:
            return formatter.get_style_defs() + _LATEX_ADD_STYLES
