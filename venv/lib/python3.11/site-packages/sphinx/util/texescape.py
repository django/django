"""TeX escaping helper."""

from __future__ import annotations

import re

tex_replacements = [
    # map TeX special chars
    ('$', r'\$'),
    ('%', r'\%'),
    ('&', r'\&'),
    ('#', r'\#'),
    ('_', r'\_'),
    ('{', r'\{'),
    ('}', r'\}'),
    ('\\', r'\textbackslash{}'),
    ('~', r'\textasciitilde{}'),
    ('^', r'\textasciicircum{}'),
    # map chars to avoid mis-interpretation in LaTeX
    ('[', r'{[}'),
    (']', r'{]}'),
    # map special Unicode characters to TeX commands
    ('✓', r'\(\checkmark\)'),
    ('✔', r'\(\pmb{\checkmark}\)'),
    ('✕', r'\(\times\)'),
    ('✖', r'\(\pmb{\times}\)'),
    # used to separate -- in options
    ('﻿', r'{}'),
    # map some special Unicode characters to similar ASCII ones
    # (even for Unicode LaTeX as may not be supported by OpenType font)
    ('⎽', r'\_'),
    ('ℯ', r'e'),
    ('ⅈ', r'i'),
    # Greek alphabet not escaped: pdflatex handles it via textalpha and inputenc
    # OHM SIGN U+2126 is handled by LaTeX textcomp package
]

# A map to avoid TeX ligatures or character replacements in PDF output
# xelatex/lualatex/uplatex are handled differently (#5790, #6888)
ascii_tex_replacements = [
    # Note: the " renders curly in OT1 encoding but straight in T1, T2A, LY1...
    #       escaping it to \textquotedbl would break documents using OT1
    #       Sphinx does \shorthandoff{"} to avoid problems with some languages
    # There is no \text... LaTeX escape for the hyphen character -
    ('-', r'\sphinxhyphen{}'),  # -- and --- are TeX ligatures
    # ,, is a TeX ligature in T1 encoding, but escaping the comma adds
    # complications (whether by {}, or a macro) and is not done
    # the next two require textcomp package
    ("'", r'\textquotesingle{}'),  # else ' renders curly, and '' is a ligature
    ('`', r'\textasciigrave{}'),   # else \` and \`\` render curly
    ('<', r'\textless{}'),     # < is inv. exclam in OT1, << is a T1-ligature
    ('>', r'\textgreater{}'),  # > is inv. quest. mark in 0T1, >> a T1-ligature
]

# A map Unicode characters to LaTeX representation
# (for LaTeX engines which don't support unicode)
unicode_tex_replacements = [
    # map some more common Unicode characters to TeX commands
    ('¶', r'\P{}'),
    ('§', r'\S{}'),
    ('€', r'\texteuro{}'),
    ('∞', r'\(\infty\)'),
    ('±', r'\(\pm\)'),
    ('→', r'\(\rightarrow\)'),
    ('‣', r'\(\rightarrow\)'),
    ('–', r'\textendash{}'),
    # superscript
    ('⁰', r'\(\sp{\text{0}}\)'),
    ('¹', r'\(\sp{\text{1}}\)'),
    ('²', r'\(\sp{\text{2}}\)'),
    ('³', r'\(\sp{\text{3}}\)'),
    ('⁴', r'\(\sp{\text{4}}\)'),
    ('⁵', r'\(\sp{\text{5}}\)'),
    ('⁶', r'\(\sp{\text{6}}\)'),
    ('⁷', r'\(\sp{\text{7}}\)'),
    ('⁸', r'\(\sp{\text{8}}\)'),
    ('⁹', r'\(\sp{\text{9}}\)'),
    # subscript
    ('₀', r'\(\sb{\text{0}}\)'),
    ('₁', r'\(\sb{\text{1}}\)'),
    ('₂', r'\(\sb{\text{2}}\)'),
    ('₃', r'\(\sb{\text{3}}\)'),
    ('₄', r'\(\sb{\text{4}}\)'),
    ('₅', r'\(\sb{\text{5}}\)'),
    ('₆', r'\(\sb{\text{6}}\)'),
    ('₇', r'\(\sb{\text{7}}\)'),
    ('₈', r'\(\sb{\text{8}}\)'),
    ('₉', r'\(\sb{\text{9}}\)'),
]

# TODO: this should be called tex_idescape_map because its only use is in
#       sphinx.writers.latex.LaTeXTranslator.idescape()
# %, {, }, \, #, and ~ are the only ones which must be replaced by _ character
# It would be simpler to define it entirely here rather than in init().
# Unicode replacements are superfluous, as idescape() uses backslashreplace
tex_replace_map: dict[int, str] = {}

_tex_escape_map: dict[int, str] = {}
_tex_escape_map_without_unicode: dict[int, str] = {}
_tex_hlescape_map: dict[int, str] = {}
_tex_hlescape_map_without_unicode: dict[int, str] = {}


def escape(s: str, latex_engine: str | None = None) -> str:
    """Escape text for LaTeX output."""
    if latex_engine in ('lualatex', 'xelatex'):
        # unicode based LaTeX engine
        return s.translate(_tex_escape_map_without_unicode)
    else:
        return s.translate(_tex_escape_map)


def hlescape(s: str, latex_engine: str | None = None) -> str:
    """Escape text for LaTeX highlighter."""
    if latex_engine in ('lualatex', 'xelatex'):
        # unicode based LaTeX engine
        return s.translate(_tex_hlescape_map_without_unicode)
    else:
        return s.translate(_tex_hlescape_map)


def escape_abbr(text: str) -> str:
    """Adjust spacing after abbreviations. Works with @ letter or other."""
    return re.sub(r'\.(?=\s|$)', r'.\@{}', text)


def init() -> None:
    for a, b in tex_replacements:
        _tex_escape_map[ord(a)] = b
        _tex_escape_map_without_unicode[ord(a)] = b
        tex_replace_map[ord(a)] = '_'

    # no reason to do this for _tex_escape_map_without_unicode
    for a, b in ascii_tex_replacements:
        _tex_escape_map[ord(a)] = b

    # but the hyphen has a specific PDF bookmark problem
    # https://github.com/latex3/hyperref/issues/112
    _tex_escape_map_without_unicode[ord('-')] = r'\sphinxhyphen{}'

    for a, b in unicode_tex_replacements:
        _tex_escape_map[ord(a)] = b
        #  This is actually unneeded:
        tex_replace_map[ord(a)] = '_'

    for a, b in tex_replacements:
        if a in '[]{}\\':
            continue
        _tex_hlescape_map[ord(a)] = b
        _tex_hlescape_map_without_unicode[ord(a)] = b

    for a, b in unicode_tex_replacements:
        _tex_hlescape_map[ord(a)] = b
