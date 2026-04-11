# :Id: $Id: tex2mathml_extern.py 10136 2025-05-20 15:48:27Z milde $
# :Copyright: © 2015 Günter Milde.
# :License: Released under the terms of the `2-Clause BSD license`__, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# __ https://opensource.org/licenses/BSD-2-Clause

"""Wrappers for TeX->MathML conversion by external tools

This module is provisional:
the API is not settled and may change with any minor Docutils version.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

import subprocess

from docutils import nodes
from docutils.utils.math import MathError, wrap_math_code

# `latexml` expects a complete document:
document_template = r"""\documentclass{article}
\begin{document}
%s
\end{document}
"""


def _check_result(result, details=[]):
    # raise MathError if the conversion went wrong
    # :details: list of doctree nodes with additional info
    msg = ''
    if not details and result.stderr:
        details = [nodes.paragraph('', result.stderr, classes=['pre-wrap'])]
    if details:
        msg = f'TeX to MathML converter `{result.args[0]}` failed:'
    elif result.returncode:
        msg = (f'TeX to MathMl converter `{result.args[0]}` '
               f'exited with Errno {result.returncode}.')
    elif not result.stdout:
        msg = f'TeX to MathML converter `{result.args[0]}` returned no MathML.'
    if msg:
        raise MathError(msg, details=details)


def blahtexml(math_code, as_block=False) -> str:
    """Convert LaTeX math code to MathML with blahtexml__.

    __ http://gva.noekeon.org/blahtexml/
    """
    args = ['blahtexml',
            '--mathml',
            '--indented',
            '--spacing', 'moderate',
            '--mathml-encoding', 'raw',
            '--other-encoding', 'raw',
            '--doctype-xhtml+mathml',
            '--annotate-TeX',
            ]
    # "blahtexml" expects LaTeX code without math-mode-switch.
    # We still need to tell it about displayed equation(s).
    mathml_args = ' display="block"' if as_block else ''
    _wrapped = wrap_math_code(math_code, as_block)
    if '{align*}' in _wrapped:
        math_code = _wrapped.replace('{align*}', '{aligned}')

    result = subprocess.run(args, input=math_code,
                            capture_output=True, text=True)

    # blahtexml writes <error> messages to stdout
    if '<error>' in result.stdout:
        result.stderr = result.stdout[result.stdout.find('<message>')+9:
                                      result.stdout.find('</message>')]
    else:
        result.stdout = result.stdout[result.stdout.find('<markup>')+9:
                                      result.stdout.find('</markup>')]
    _check_result(result)
    return (f'<math xmlns="http://www.w3.org/1998/Math/MathML"{mathml_args}>'
            f'\n{result.stdout}</math>')


def latexml(math_code, as_block=False):
    """Convert LaTeX math code to MathML with LaTeXML__.

    Comprehensive macro support but **very** slow.

    __ http://dlmf.nist.gov/LaTeXML/
    """

    # LaTeXML works in 2 stages, expects complete documents.
    #
    # The `latexmlmath`__ convenience wrapper does not support block-level
    # (displayed) equations.
    #
    # __ https://metacpan.org/dist/LaTeXML/view/bin/latexmlmath
    args1 = ['latexml',
             '-',  # read from stdin
             '--preload=amsmath',
             '--preload=amssymb',  # also loads amsfonts
             '--inputencoding=utf8',
             '--',
             ]
    math_code = document_template % wrap_math_code(math_code, as_block)
    error_tags = ('Error:', 'Warning:', 'Fatal:')

    result1 = subprocess.run(args1, input=math_code,
                             capture_output=True, text=True)
    if result1.stderr:
        result1.stderr = '\n'.join(line for line in result1.stderr.splitlines()
                                   if line.startswith(error_tags))
    _check_result(result1)

    args2 = ['latexmlpost',
             '-',
             '--nonumbersections',
             '--format=html5',  # maths included as MathML
             '--omitdoctype',   # Make it simple, we only need the maths.
             '--noscan',        # ...
             '--nocrossref',
             '--nographicimages',
             '--nopictureimages',
             '--nodefaultresources',  # do not copy *.css files to output dir
             '--'
             ]
    result2 = subprocess.run(args2, input=result1.stdout,
                             capture_output=True, text=True)
    # Extract MathML from HTML document:
    # <table> with <math> in cells for "align", <math> element else.
    start = result2.stdout.find('<table class="ltx_equationgroup')
    if start != -1:
        stop = result2.stdout.find('</table>', start)+8
        result2.stdout = result2.stdout[start:stop].replace(
            'ltx_equationgroup', 'borderless align-center')
    else:
        result2.stdout = result2.stdout[result2.stdout.find('<math'):
                                        result2.stdout.find('</math>')+7]
    # Search for error messages
    if result2.stdout:
        _msg_source = result2.stdout  # latexmlpost reports errors in output
    else:
        _msg_source = result2.stderr  # just in case
    result2.stderr = '\n'.join(line for line in _msg_source.splitlines()
                               if line.startswith(error_tags))
    _check_result(result2)
    return result2.stdout


def pandoc(math_code, as_block=False):
    """Convert LaTeX math code to MathML with pandoc__.

    __ https://pandoc.org/
    """
    args = ['pandoc',
            '--mathml',
            '--from=latex',
            ]
    result = subprocess.run(args, input=wrap_math_code(math_code, as_block),
                            capture_output=True, text=True)

    result.stdout = result.stdout[result.stdout.find('<math'):
                                  result.stdout.find('</math>')+7]
    # Pandoc (2.9.2.1) messages are pre-formatted for the terminal:
    #   1. summary
    #   2. math source (part)
    #   3. error spot indicator '^' (works only in a literal block)
    #   4. assumed problem
    #   5. assumed solution (may be wrong or confusing)
    # Construct a "details" list:
    details = []
    if result.stderr:
        lines = result.stderr.splitlines()
        details += [nodes.paragraph('', lines[0]),
                    nodes.literal_block('', '\n'.join(lines[1:3])),
                    nodes.paragraph('', '\n'.join(lines[3:]),
                                    classes=['pre-wrap']),
                    ]
    _check_result(result, details=details)
    return result.stdout


def ttm(math_code, as_block=False):
    """Convert LaTeX math code to MathML with TtM__.

    Aged, limited, but fast.

    __ http://silas.psfc.mit.edu/tth/mml/
    """
    args = ['ttm',
            '-L',  # source is LaTeX snippet
            '-r']  # output MathML snippet
    math_code = wrap_math_code(math_code, as_block)

    # "ttm" does not support UTF-8 input. (Docutils converts most math
    # characters to LaTeX commands before calling this function.)
    try:
        result = subprocess.run(args, input=math_code,
                                capture_output=True, text=True,
                                encoding='ISO-8859-1')
    except UnicodeEncodeError as err:
        raise MathError(err)

    result.stdout = result.stdout[result.stdout.find('<math'):
                                  result.stdout.find('</math>')+7]
    if as_block:
        result.stdout = result.stdout.replace('<math xmlns=',
                                              '<math display="block" xmlns=')
    result.stderr = '\n'.join(line[5:] + '.'
                              for line in result.stderr.splitlines()
                              if line.startswith('**** '))
    _check_result(result)
    return result.stdout


# self-test

if __name__ == "__main__":
    example = (r'\frac{\partial \sin^2(\alpha)}{\partial \vec r}'
               r'\varpi \mathbb{R} \, \text{Grüße}')

    print("""<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<title>test external mathml converters</title>
</head>
<body>
<p>Test external converters</p>
<p>
""")
    print(f'latexml: {latexml(example)},')
    print(f'ttm: {ttm(example.replace("mathbb", "mathbf"))},')
    print(f'blahtexml: {blahtexml(example)},')
    print(f'pandoc: {pandoc(example)}.')
    print('</p>')

    print('<p>latexml:</p>')
    print(latexml(example, as_block=True))
    print('<p>ttm:</p>')
    print(ttm(example.replace('mathbb', 'mathbf'), as_block=True))
    print('<p>blahtexml:</p>')
    print(blahtexml(example, as_block=True))
    print('<p>pandoc:</p>')
    print(pandoc(example, as_block=True))

    print('</main>\n</body>\n</html>')

    buggy = r'\sinc \phy'
    # buggy = '\sqrt[e]'
    try:
        # print(blahtexml(buggy))
        # print(latexml(f'${buggy}$'))
        print(pandoc(f'${buggy}$'))
        # print(ttm(f'${buggy}$'))
    except MathError as err:
        print(err)
        print(err.details)
        for node in err.details:
            print(node.astext())
