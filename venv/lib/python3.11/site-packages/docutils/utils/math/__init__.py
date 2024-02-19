# :Id: $Id: __init__.py 9026 2022-03-04 15:57:13Z milde $
# :Author: Guenter Milde.
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: https://opensource.org/licenses/BSD-2-Clause

"""
This is the Docutils (Python Documentation Utilities) "math" sub-package.

It contains various modules for conversion between different math formats
(LaTeX, MathML, HTML).

:math2html:    LaTeX math -> HTML conversion from eLyXer
:latex2mathml: LaTeX math -> presentational MathML
:unichar2tex:  Unicode character to LaTeX math translation table
:tex2unichar:  LaTeX math to Unicode character translation dictionaries
:tex2mathml_extern: Wrapper for 3rd party TeX -> MathML converters
"""

# helpers for Docutils math support
# =================================


def toplevel_code(code):
    """Return string (LaTeX math) `code` with environments stripped out."""
    chunks = code.split(r'\begin{')
    return r'\begin{'.join(chunk.split(r'\end{')[-1]
                           for chunk in chunks)


def pick_math_environment(code, numbered=False):
    """Return the right math environment to display `code`.

    The test simply looks for line-breaks (``\\``) outside environments.
    Multi-line formulae are set with ``align``, one-liners with
    ``equation``.

    If `numbered` evaluates to ``False``, the "starred" versions are used
    to suppress numbering.
    """
    if toplevel_code(code).find(r'\\') >= 0:
        env = 'align'
    else:
        env = 'equation'
    if not numbered:
        env += '*'
    return env
