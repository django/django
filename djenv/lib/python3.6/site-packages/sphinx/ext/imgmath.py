# -*- coding: utf-8 -*-
"""
    sphinx.ext.imgmath
    ~~~~~~~~~~~~~~~~~~

    Render math in HTML via dvipng or dvisvgm.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import codecs
import posixpath
import re
import shutil
import tempfile
from hashlib import sha1
from os import path
from subprocess import Popen, PIPE

from docutils import nodes
from six import text_type

import sphinx
from sphinx.errors import SphinxError
from sphinx.locale import _, __
from sphinx.util import logging
from sphinx.util.math import get_node_equation_number, wrap_displaymath
from sphinx.util.osutil import ensuredir, ENOENT, cd
from sphinx.util.png import read_png_depth, write_png_depth
from sphinx.util.pycompat import sys_encoding

if False:
    # For type annotation
    from typing import Any, Dict, List, Tuple  # NOQA
    from sphinx.addnodes import displaymath  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.config import Config  # NOQA

logger = logging.getLogger(__name__)


class MathExtError(SphinxError):
    category = 'Math extension error'

    def __init__(self, msg, stderr=None, stdout=None):
        # type: (unicode, unicode, unicode) -> None
        if stderr:
            msg += '\n[stderr]\n' + stderr.decode(sys_encoding, 'replace')
        if stdout:
            msg += '\n[stdout]\n' + stdout.decode(sys_encoding, 'replace')
        SphinxError.__init__(self, msg)


class InvokeError(SphinxError):
    """errors on invoking converters."""


SUPPORT_FORMAT = ('png', 'svg')

DOC_HEAD = r'''
\documentclass[12pt]{article}
\usepackage[utf8x]{inputenc}
\usepackage{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage{anyfontsize}
\usepackage{bm}
\pagestyle{empty}
'''

DOC_BODY = r'''
\begin{document}
\fontsize{%d}{%d}\selectfont %s
\end{document}
'''

DOC_BODY_PREVIEW = r'''
\usepackage[active]{preview}
\begin{document}
\begin{preview}
\fontsize{%s}{%s}\selectfont %s
\end{preview}
\end{document}
'''

depth_re = re.compile(br'\[\d+ depth=(-?\d+)\]')


def generate_latex_macro(math, config):
    # type: (unicode, Config) -> unicode
    """Generate LaTeX macro."""
    fontsize = config.imgmath_font_size
    baselineskip = int(round(fontsize * 1.2))

    latex = DOC_HEAD + config.imgmath_latex_preamble
    if config.imgmath_use_preview:
        latex += DOC_BODY_PREVIEW % (fontsize, baselineskip, math)
    else:
        latex += DOC_BODY % (fontsize, baselineskip, math)

    return latex


def ensure_tempdir(builder):
    # type: (Builder) -> unicode
    """Create temporary directory.

    use only one tempdir per build -- the use of a directory is cleaner
    than using temporary files, since we can clean up everything at once
    just removing the whole directory (see cleanup_tempdir)
    """
    if not hasattr(builder, '_imgmath_tempdir'):
        builder._imgmath_tempdir = tempfile.mkdtemp()  # type: ignore

    return builder._imgmath_tempdir  # type: ignore


def compile_math(latex, builder):
    # type: (unicode, Builder) -> unicode
    """Compile LaTeX macros for math to DVI."""
    tempdir = ensure_tempdir(builder)
    filename = path.join(tempdir, 'math.tex')
    with codecs.open(filename, 'w', 'utf-8') as f:  # type: ignore
        f.write(latex)

    # build latex command; old versions of latex don't have the
    # --output-directory option, so we have to manually chdir to the
    # temp dir to run it.
    command = [builder.config.imgmath_latex, '--interaction=nonstopmode']
    # add custom args from the config file
    command.extend(builder.config.imgmath_latex_args)
    command.append('math.tex')

    with cd(tempdir):
        try:
            p = Popen(command, stdout=PIPE, stderr=PIPE)
        except OSError as err:
            if err.errno != ENOENT:   # No such file or directory
                raise
            logger.warning(__('LaTeX command %r cannot be run (needed for math '
                              'display), check the imgmath_latex setting'),
                           builder.config.imgmath_latex)
            raise InvokeError

    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise MathExtError('latex exited with error', stderr, stdout)

    return path.join(tempdir, 'math.dvi')


def convert_dvi_to_image(command, name):
    # type: (List[unicode], unicode) -> Tuple[unicode, unicode]
    """Convert DVI file to specific image format."""
    try:
        p = Popen(command, stdout=PIPE, stderr=PIPE)
    except OSError as err:
        if err.errno != ENOENT:   # No such file or directory
            raise
        logger.warning(__('%s command %r cannot be run (needed for math '
                          'display), check the imgmath_%s setting'),
                       name, command[0], name)
        raise InvokeError

    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise MathExtError('%s exited with error' % name, stderr, stdout)

    return stdout, stderr


def convert_dvi_to_png(dvipath, builder):
    # type: (unicode, Builder) -> Tuple[unicode, int]
    """Convert DVI file to PNG image."""
    tempdir = ensure_tempdir(builder)
    filename = path.join(tempdir, 'math.png')

    name = 'dvipng'
    command = [builder.config.imgmath_dvipng, '-o', filename, '-T', 'tight', '-z9']
    command.extend(builder.config.imgmath_dvipng_args)
    if builder.config.imgmath_use_preview:
        command.append('--depth')
    command.append(dvipath)

    stdout, stderr = convert_dvi_to_image(command, name)

    depth = None
    if builder.config.imgmath_use_preview:
        for line in stdout.splitlines():
            matched = depth_re.match(line)
            if matched:
                depth = int(matched.group(1))
                write_png_depth(filename, depth)
                break

    return filename, depth


def convert_dvi_to_svg(dvipath, builder):
    # type: (unicode, Builder) -> Tuple[unicode, int]
    """Convert DVI file to SVG image."""
    tempdir = ensure_tempdir(builder)
    filename = path.join(tempdir, 'math.svg')

    name = 'dvisvgm'
    command = [builder.config.imgmath_dvisvgm, '-o', filename]
    command.extend(builder.config.imgmath_dvisvgm_args)
    command.append(dvipath)

    convert_dvi_to_image(command, name)
    return filename, None


def render_math(self, math):
    # type: (nodes.NodeVisitor, unicode) -> Tuple[unicode, int]
    """Render the LaTeX math expression *math* using latex and dvipng or
    dvisvgm.

    Return the filename relative to the built document and the "depth",
    that is, the distance of image bottom and baseline in pixels, if the
    option to use preview_latex is switched on.

    Error handling may seem strange, but follows a pattern: if LaTeX or dvipng
    (dvisvgm) aren't available, only a warning is generated (since that enables
    people on machines without these programs to at least build the rest of the
    docs successfully).  If the programs are there, however, they may not fail
    since that indicates a problem in the math source.
    """
    image_format = self.builder.config.imgmath_image_format.lower()
    if image_format not in SUPPORT_FORMAT:
        raise MathExtError('imgmath_image_format must be either "png" or "svg"')

    latex = generate_latex_macro(math, self.builder.config)

    filename = "%s.%s" % (sha1(latex.encode('utf-8')).hexdigest(), image_format)
    relfn = posixpath.join(self.builder.imgpath, 'math', filename)
    outfn = path.join(self.builder.outdir, self.builder.imagedir, 'math', filename)
    if path.isfile(outfn):
        depth = read_png_depth(outfn)
        return relfn, depth

    # if latex or dvipng (dvisvgm) has failed once, don't bother to try again
    if hasattr(self.builder, '_imgmath_warned_latex') or \
       hasattr(self.builder, '_imgmath_warned_image_translator'):
        return None, None

    # .tex -> .dvi
    try:
        dvipath = compile_math(latex, self.builder)
    except InvokeError:
        self.builder._imgmath_warned_latex = True
        return None, None

    # .dvi -> .png/.svg
    try:
        if image_format == 'png':
            imgpath, depth = convert_dvi_to_png(dvipath, self.builder)
        elif image_format == 'svg':
            imgpath, depth = convert_dvi_to_svg(dvipath, self.builder)
    except InvokeError:
        self.builder._imgmath_warned_image_translator = True
        return None, None

    # Move generated image on tempdir to build dir
    ensuredir(path.dirname(outfn))
    shutil.move(imgpath, outfn)

    return relfn, depth


def cleanup_tempdir(app, exc):
    # type: (Sphinx, Exception) -> None
    if exc:
        return
    if not hasattr(app.builder, '_imgmath_tempdir'):
        return
    try:
        shutil.rmtree(app.builder._mathpng_tempdir)  # type: ignore
    except Exception:
        pass


def get_tooltip(self, node):
    # type: (nodes.NodeVisitor, nodes.math) -> unicode
    if self.builder.config.imgmath_add_tooltips:
        return ' alt="%s"' % self.encode(node.astext()).strip()
    return ''


def html_visit_math(self, node):
    # type: (nodes.NodeVisitor, nodes.math) -> None
    try:
        fname, depth = render_math(self, '$' + node.astext() + '$')
    except MathExtError as exc:
        msg = text_type(exc)
        sm = nodes.system_message(msg, type='WARNING', level=2,
                                  backrefs=[], source=node.astext())
        sm.walkabout(self)
        logger.warning(__('display latex %r: %s'), node.astext(), msg)
        raise nodes.SkipNode
    if fname is None:
        # something failed -- use text-only as a bad substitute
        self.body.append('<span class="math">%s</span>' %
                         self.encode(node.astext()).strip())
    else:
        c = ('<img class="math" src="%s"' % fname) + get_tooltip(self, node)
        if depth is not None:
            c += ' style="vertical-align: %dpx"' % (-depth)
        self.body.append(c + '/>')
    raise nodes.SkipNode


def html_visit_displaymath(self, node):
    # type: (nodes.NodeVisitor, nodes.math_block) -> None
    if node['nowrap']:
        latex = node.astext()
    else:
        latex = wrap_displaymath(node.astext(), None, False)
    try:
        fname, depth = render_math(self, latex)
    except MathExtError as exc:
        msg = text_type(exc)
        sm = nodes.system_message(msg, type='WARNING', level=2,
                                  backrefs=[], source=node.astext())
        sm.walkabout(self)
        logger.warning(__('inline latex %r: %s'), node.astext(), msg)
        raise nodes.SkipNode
    self.body.append(self.starttag(node, 'div', CLASS='math'))
    self.body.append('<p>')
    if node['number']:
        number = get_node_equation_number(self, node)
        self.body.append('<span class="eqno">(%s)' % number)
        self.add_permalink_ref(node, _('Permalink to this equation'))
        self.body.append('</span>')
    if fname is None:
        # something failed -- use text-only as a bad substitute
        self.body.append('<span class="math">%s</span></p>\n</div>' %
                         self.encode(node.astext()).strip())
    else:
        self.body.append(('<img src="%s"' % fname) + get_tooltip(self, node) +
                         '/></p>\n</div>')
    raise nodes.SkipNode


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_html_math_renderer('imgmath',
                               (html_visit_math, None),
                               (html_visit_displaymath, None))

    app.add_config_value('imgmath_image_format', 'png', 'html')
    app.add_config_value('imgmath_dvipng', 'dvipng', 'html')
    app.add_config_value('imgmath_dvisvgm', 'dvisvgm', 'html')
    app.add_config_value('imgmath_latex', 'latex', 'html')
    app.add_config_value('imgmath_use_preview', False, 'html')
    app.add_config_value('imgmath_dvipng_args',
                         ['-gamma', '1.5', '-D', '110', '-bg', 'Transparent'],
                         'html')
    app.add_config_value('imgmath_dvisvgm_args', ['--no-fonts'], 'html')
    app.add_config_value('imgmath_latex_args', [], 'html')
    app.add_config_value('imgmath_latex_preamble', '', 'html')
    app.add_config_value('imgmath_add_tooltips', True, 'html')
    app.add_config_value('imgmath_font_size', 12, 'html')
    app.connect('build-finished', cleanup_tempdir)
    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
