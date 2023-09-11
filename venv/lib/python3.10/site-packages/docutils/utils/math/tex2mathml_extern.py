# :Id: $Id: tex2mathml_extern.py 9250 2022-11-16 14:01:31Z milde $
# :Copyright: © 2015 Günter Milde.
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: https://opensource.org/licenses/BSD-2-Clause

"""Wrappers for TeX->MathML conversion by external tools

This module is provisional:
the API is not settled and may change with any minor Docutils version.
"""

import subprocess

document_template = r"""\documentclass{article}
\usepackage{amsmath}
\begin{document}
%s
\end{document}
"""


def latexml(math_code, reporter=None):
    """Convert LaTeX math code to MathML with LaTeXML_

    .. _LaTeXML: http://dlmf.nist.gov/LaTeXML/
    """
    p = subprocess.Popen(['latexml',
                          '-',  # read from stdin
                          '--preload=amsfonts',
                          '--preload=amsmath',
                          '--inputencoding=utf8',
                          ],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=True)
    p.stdin.write((document_template % math_code).encode('utf-8'))
    p.stdin.close()
    latexml_code = p.stdout.read()
    latexml_err = p.stderr.read().decode('utf-8')
    if reporter and (latexml_err.find('Error') >= 0 or not latexml_code):
        reporter.error(latexml_err)

    post_p = subprocess.Popen(['latexmlpost',
                               '-',
                               '--nonumbersections',
                               '--format=xhtml',
                               # '--linelength=78',  # experimental
                               '--'
                               ],
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              close_fds=True)
    post_p.stdin.write(latexml_code)
    post_p.stdin.close()
    result = post_p.stdout.read().decode('utf-8')
    post_p_err = post_p.stderr.read().decode('utf-8')
    if reporter and (post_p_err.find('Error') >= 0 or not result):
        reporter.error(post_p_err)

    # extract MathML code:
    start, end = result.find('<math'), result.find('</math>')+7
    result = result[start:end]
    if 'class="ltx_ERROR' in result:
        raise SyntaxError(result)
    return result


def ttm(math_code, reporter=None):
    """Convert LaTeX math code to MathML with TtM_

    .. _TtM: http://hutchinson.belmont.ma.us/tth/mml/
    """
    p = subprocess.Popen(['ttm',
                          # '-i',  # italic font for equations. Default roman.
                          '-u',    # unicode encoding. (Default iso-8859-1).
                          '-r',    # output raw MathML (no wrapper)
                          ],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=True)
    p.stdin.write((document_template % math_code).encode('utf-8'))
    p.stdin.close()
    result = p.stdout.read()
    err = p.stderr.read().decode('utf-8')
    if err.find('**** Unknown') >= 0:
        msg = '\n'.join(line for line in err.splitlines()
                        if line.startswith('****'))
        raise SyntaxError('\nMessage from external converter TtM:\n'+msg)
    if reporter and err.find('**** Error') >= 0 or not result:
        reporter.error(err)
    start, end = result.find('<math'), result.find('</math>')+7
    return result[start:end]


def blahtexml(math_code, inline=True, reporter=None):
    """Convert LaTeX math code to MathML with blahtexml_

    .. _blahtexml: http://gva.noekeon.org/blahtexml/
    """
    options = ['--mathml',
               '--indented',
               '--spacing', 'moderate',
               '--mathml-encoding', 'raw',
               '--other-encoding', 'raw',
               '--doctype-xhtml+mathml',
               '--annotate-TeX',
               ]
    if inline:
        mathmode_arg = ''
    else:
        mathmode_arg = ' display="block"'
        options.append('--displaymath')

    p = subprocess.Popen(['blahtexml']+options,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=True)
    p.stdin.write(math_code.encode('utf-8'))
    p.stdin.close()
    result = p.stdout.read().decode('utf-8')
    err = p.stderr.read().decode('utf-8')

    if result.find('<error>') >= 0:
        msg = result[result.find('<message>')+9:result.find('</message>')]
        raise SyntaxError('\nMessage from external converter blahtexml:\n%s'
                          % msg)
    if reporter and (err.find('**** Error') >= 0 or not result):
        reporter.error(err)
    start, end = result.find('<markup>')+9, result.find('</markup>')
    result = ('<math xmlns="http://www.w3.org/1998/Math/MathML"%s>\n'
              '%s</math>\n') % (mathmode_arg, result[start:end])
    return result


def pandoc(math_code, reporter=None):
    """Convert LaTeX math code to MathML with pandoc_

    .. _pandoc: https://pandoc.org/
    """
    p = subprocess.Popen(['pandoc',
                          '--mathml',
                          '--from=latex',
                          ],
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=True)
    p.stdin.write(math_code.encode('utf-8'))
    p.stdin.close()
    result = p.stdout.read().decode('utf-8')
    err = p.stderr.read().decode('utf-8').strip()
    x = p.wait()

    if err:
        if reporter:
            reporter.error(err)
        raise SyntaxError('\nError message from external converter pandoc:\n%s'
                          % err)
    if x != 0:
        raise SyntaxError('\nError code from external converter pandoc:\n%s'
                          % x)

    start, end = result.find('<math'), result.find('</math>')+7
    return result[start:end]


# self-test

if __name__ == "__main__":
    example = ('\\frac{\\partial \\sin^2(\\alpha)}{\\partial \\vec r}'
               '\\varpi \\mathbb{R} \\, \\text{Grüße}')
    # print(latexml('$'+example+'$'))
    # print(ttm('$'+example.replace('\\mathbb{R}', '')+'$'))
    print(blahtexml(example))
    # print(pandoc('$'+example+'$'))
