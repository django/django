# -*- coding: utf-8 -*-
"""
    sphinx.ext.graphviz
    ~~~~~~~~~~~~~~~~~~~

    Allow graphviz-formatted graphs to be included in Sphinx-generated
    documents inline.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import codecs
import posixpath
import re
from hashlib import sha1
from os import path
from subprocess import Popen, PIPE

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from six import text_type

import sphinx
from sphinx.errors import SphinxError
from sphinx.locale import _, __
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.fileutil import copy_asset
from sphinx.util.i18n import search_image_for_language
from sphinx.util.osutil import ensuredir, ENOENT, EPIPE, EINVAL

if False:
    # For type annotation
    from docutils.parsers.rst import Directive  # NOQA
    from typing import Any, Dict, List, Tuple  # NOQA
    from sphinx.application import Sphinx  # NOQA

logger = logging.getLogger(__name__)


class GraphvizError(SphinxError):
    category = 'Graphviz error'


class ClickableMapDefinition(object):
    """A manipulator for clickable map file of graphviz."""
    maptag_re = re.compile('<map id="(.*?)"')
    href_re = re.compile('href=".*?"')

    def __init__(self, filename, content, dot=''):
        # type: (unicode, unicode, unicode) -> None
        self.id = None  # type: unicode
        self.filename = filename
        self.content = content.splitlines()
        self.clickable = []  # type: List[unicode]

        self.parse(dot=dot)

    def parse(self, dot=None):
        # type: (unicode) -> None
        matched = self.maptag_re.match(self.content[0])
        if not matched:
            raise GraphvizError('Invalid clickable map file found: %s' % self.filename)

        self.id = matched.group(1)
        if self.id == '%3':
            # graphviz generates wrong ID if graph name not specified
            # https://gitlab.com/graphviz/graphviz/issues/1327
            hashed = sha1(dot.encode('utf-8')).hexdigest()
            self.id = 'grapviz%s' % hashed[-10:]
            self.content[0] = self.content[0].replace('%3', self.id)

        for line in self.content:
            if self.href_re.search(line):
                self.clickable.append(line)

    def generate_clickable_map(self):
        # type: () -> unicode
        """Generate clickable map tags if clickable item exists.

        If not exists, this only returns empty string.
        """
        if self.clickable:
            return '\n'.join([self.content[0]] + self.clickable + [self.content[-1]])
        else:
            return ''


class graphviz(nodes.General, nodes.Inline, nodes.Element):
    pass


def figure_wrapper(directive, node, caption):
    # type: (Directive, nodes.Node, unicode) -> nodes.figure
    figure_node = nodes.figure('', node)
    if 'align' in node:
        figure_node['align'] = node.attributes.pop('align')

    parsed = nodes.Element()
    directive.state.nested_parse(ViewList([caption], source=''),
                                 directive.content_offset, parsed)
    caption_node = nodes.caption(parsed[0].rawsource, '',
                                 *parsed[0].children)
    caption_node.source = parsed[0].source
    caption_node.line = parsed[0].line
    figure_node += caption_node
    return figure_node


def align_spec(argument):
    # type: (Any) -> bool
    return directives.choice(argument, ('left', 'center', 'right'))


class Graphviz(SphinxDirective):
    """
    Directive to insert arbitrary dot markup.
    """
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = False
    option_spec = {
        'alt': directives.unchanged,
        'align': align_spec,
        'caption': directives.unchanged,
        'graphviz_dot': directives.unchanged,
        'name': directives.unchanged,
    }

    def run(self):
        # type: () -> List[nodes.Node]
        if self.arguments:
            document = self.state.document
            if self.content:
                return [document.reporter.warning(
                    __('Graphviz directive cannot have both content and '
                       'a filename argument'), line=self.lineno)]
            argument = search_image_for_language(self.arguments[0], self.env)
            rel_filename, filename = self.env.relfn2path(argument)
            self.env.note_dependency(rel_filename)
            try:
                with codecs.open(filename, 'r', 'utf-8') as fp:  # type: ignore
                    dotcode = fp.read()
            except (IOError, OSError):
                return [document.reporter.warning(
                    __('External Graphviz file %r not found or reading '
                       'it failed') % filename, line=self.lineno)]
        else:
            dotcode = '\n'.join(self.content)
            if not dotcode.strip():
                return [self.state_machine.reporter.warning(
                    __('Ignoring "graphviz" directive without content.'),
                    line=self.lineno)]
        node = graphviz()
        node['code'] = dotcode
        node['options'] = {'docname': self.env.docname}

        if 'graphviz_dot' in self.options:
            node['options']['graphviz_dot'] = self.options['graphviz_dot']
        if 'alt' in self.options:
            node['alt'] = self.options['alt']
        if 'align' in self.options:
            node['align'] = self.options['align']

        caption = self.options.get('caption')
        if caption:
            node = figure_wrapper(self, node, caption)

        self.add_name(node)
        return [node]


class GraphvizSimple(SphinxDirective):
    """
    Directive to insert arbitrary dot markup.
    """
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'alt': directives.unchanged,
        'align': align_spec,
        'caption': directives.unchanged,
        'graphviz_dot': directives.unchanged,
        'name': directives.unchanged,
    }

    def run(self):
        # type: () -> List[nodes.Node]
        node = graphviz()
        node['code'] = '%s %s {\n%s\n}\n' % \
                       (self.name, self.arguments[0], '\n'.join(self.content))
        node['options'] = {'docname': self.env.docname}
        if 'graphviz_dot' in self.options:
            node['options']['graphviz_dot'] = self.options['graphviz_dot']
        if 'alt' in self.options:
            node['alt'] = self.options['alt']
        if 'align' in self.options:
            node['align'] = self.options['align']

        caption = self.options.get('caption')
        if caption:
            node = figure_wrapper(self, node, caption)

        self.add_name(node)
        return [node]


def render_dot(self, code, options, format, prefix='graphviz'):
    # type: (nodes.NodeVisitor, unicode, Dict, unicode, unicode) -> Tuple[unicode, unicode]
    """Render graphviz code into a PNG or PDF output file."""
    graphviz_dot = options.get('graphviz_dot', self.builder.config.graphviz_dot)
    hashkey = (code + str(options) + str(graphviz_dot) +
               str(self.builder.config.graphviz_dot_args)).encode('utf-8')

    fname = '%s-%s.%s' % (prefix, sha1(hashkey).hexdigest(), format)
    relfn = posixpath.join(self.builder.imgpath, fname)
    outfn = path.join(self.builder.outdir, self.builder.imagedir, fname)

    if path.isfile(outfn):
        return relfn, outfn

    if (hasattr(self.builder, '_graphviz_warned_dot') and
       self.builder._graphviz_warned_dot.get(graphviz_dot)):
        return None, None

    ensuredir(path.dirname(outfn))

    # graphviz expects UTF-8 by default
    if isinstance(code, text_type):
        code = code.encode('utf-8')

    dot_args = [graphviz_dot]
    dot_args.extend(self.builder.config.graphviz_dot_args)
    dot_args.extend(['-T' + format, '-o' + outfn])

    docname = options.get('docname', 'index')
    cwd = path.dirname(path.join(self.builder.srcdir, docname))

    if format == 'png':
        dot_args.extend(['-Tcmapx', '-o%s.map' % outfn])
    try:
        p = Popen(dot_args, stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=cwd)
    except OSError as err:
        if err.errno != ENOENT:   # No such file or directory
            raise
        logger.warning(__('dot command %r cannot be run (needed for graphviz '
                          'output), check the graphviz_dot setting'), graphviz_dot)
        if not hasattr(self.builder, '_graphviz_warned_dot'):
            self.builder._graphviz_warned_dot = {}
        self.builder._graphviz_warned_dot[graphviz_dot] = True
        return None, None
    try:
        # Graphviz may close standard input when an error occurs,
        # resulting in a broken pipe on communicate()
        stdout, stderr = p.communicate(code)
    except (OSError, IOError) as err:
        if err.errno not in (EPIPE, EINVAL):
            raise
        # in this case, read the standard output and standard error streams
        # directly, to get the error message(s)
        stdout, stderr = p.stdout.read(), p.stderr.read()
        p.wait()
    if p.returncode != 0:
        raise GraphvizError(__('dot exited with error:\n[stderr]\n%s\n'
                               '[stdout]\n%s') % (stderr, stdout))
    if not path.isfile(outfn):
        raise GraphvizError(__('dot did not produce an output file:\n[stderr]\n%s\n'
                               '[stdout]\n%s') % (stderr, stdout))
    return relfn, outfn


def render_dot_html(self, node, code, options, prefix='graphviz',
                    imgcls=None, alt=None):
    # type: (nodes.NodeVisitor, graphviz, unicode, Dict, unicode, unicode, unicode) -> Tuple[unicode, unicode]  # NOQA
    format = self.builder.config.graphviz_output_format
    try:
        if format not in ('png', 'svg'):
            raise GraphvizError(__("graphviz_output_format must be one of 'png', "
                                   "'svg', but is %r") % format)
        fname, outfn = render_dot(self, code, options, format, prefix)
    except GraphvizError as exc:
        logger.warning(__('dot code %r: %s'), code, text_type(exc))
        raise nodes.SkipNode

    if imgcls:
        imgcls += " graphviz"
    else:
        imgcls = "graphviz"

    if fname is None:
        self.body.append(self.encode(code))
    else:
        if alt is None:
            alt = node.get('alt', self.encode(code).strip())
        if 'align' in node:
            self.body.append('<div align="%s" class="align-%s">' %
                             (node['align'], node['align']))
        if format == 'svg':
            self.body.append('<div class="graphviz">')
            self.body.append('<object data="%s" type="image/svg+xml" class="%s">\n' %
                             (fname, imgcls))
            self.body.append('<p class="warning">%s</p>' % alt)
            self.body.append('</object></div>\n')
        else:
            with codecs.open(outfn + '.map', 'r', encoding='utf-8') as mapfile:  # type: ignore
                imgmap = ClickableMapDefinition(outfn + '.map', mapfile.read(), dot=code)
                if imgmap.clickable:
                    # has a map
                    self.body.append('<div class="graphviz">')
                    self.body.append('<img src="%s" alt="%s" usemap="#%s" class="%s" />' %
                                     (fname, alt, imgmap.id, imgcls))
                    self.body.append('</div>\n')
                    self.body.append(imgmap.generate_clickable_map())
                else:
                    # nothing in image map
                    self.body.append('<div class="graphviz">')
                    self.body.append('<img src="%s" alt="%s" class="%s" />' %
                                     (fname, alt, imgcls))
                    self.body.append('</div>\n')
        if 'align' in node:
            self.body.append('</div>\n')

    raise nodes.SkipNode


def html_visit_graphviz(self, node):
    # type: (nodes.NodeVisitor, graphviz) -> None
    render_dot_html(self, node, node['code'], node['options'])


def render_dot_latex(self, node, code, options, prefix='graphviz'):
    # type: (nodes.NodeVisitor, graphviz, unicode, Dict, unicode) -> None
    try:
        fname, outfn = render_dot(self, code, options, 'pdf', prefix)
    except GraphvizError as exc:
        logger.warning(__('dot code %r: %s'), code, text_type(exc))
        raise nodes.SkipNode

    is_inline = self.is_inline(node)

    if not is_inline:
        pre = ''
        post = ''
        if 'align' in node:
            if node['align'] == 'left':
                pre = '{'
                post = r'\hspace*{\fill}}'
            elif node['align'] == 'right':
                pre = r'{\hspace*{\fill}'
                post = '}'
            elif node['align'] == 'center':
                pre = r'{\hfill'
                post = r'\hspace*{\fill}}'
        self.body.append('\n%s' % pre)

    self.body.append(r'\sphinxincludegraphics[]{%s}' % fname)

    if not is_inline:
        self.body.append('%s\n' % post)

    raise nodes.SkipNode


def latex_visit_graphviz(self, node):
    # type: (nodes.NodeVisitor, graphviz) -> None
    render_dot_latex(self, node, node['code'], node['options'])


def render_dot_texinfo(self, node, code, options, prefix='graphviz'):
    # type: (nodes.NodeVisitor, graphviz, unicode, Dict, unicode) -> None
    try:
        fname, outfn = render_dot(self, code, options, 'png', prefix)
    except GraphvizError as exc:
        logger.warning(__('dot code %r: %s'), code, text_type(exc))
        raise nodes.SkipNode
    if fname is not None:
        self.body.append('@image{%s,,,[graphviz],png}\n' % fname[:-4])
    raise nodes.SkipNode


def texinfo_visit_graphviz(self, node):
    # type: (nodes.NodeVisitor, graphviz) -> None
    render_dot_texinfo(self, node, node['code'], node['options'])


def text_visit_graphviz(self, node):
    # type: (nodes.NodeVisitor, graphviz) -> None
    if 'alt' in node.attributes:
        self.add_text(_('[graph: %s]') % node['alt'])
    else:
        self.add_text(_('[graph]'))
    raise nodes.SkipNode


def man_visit_graphviz(self, node):
    # type: (nodes.NodeVisitor, graphviz) -> None
    if 'alt' in node.attributes:
        self.body.append(_('[graph: %s]') % node['alt'])
    else:
        self.body.append(_('[graph]'))
    raise nodes.SkipNode


def on_build_finished(app, exc):
    # type: (Sphinx, Exception) -> None
    if exc is None:
        src = path.join(sphinx.package_dir, 'templates', 'graphviz', 'graphviz.css')
        dst = path.join(app.outdir, '_static')
        copy_asset(src, dst)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_node(graphviz,
                 html=(html_visit_graphviz, None),
                 latex=(latex_visit_graphviz, None),
                 texinfo=(texinfo_visit_graphviz, None),
                 text=(text_visit_graphviz, None),
                 man=(man_visit_graphviz, None))
    app.add_directive('graphviz', Graphviz)
    app.add_directive('graph', GraphvizSimple)
    app.add_directive('digraph', GraphvizSimple)
    app.add_config_value('graphviz_dot', 'dot', 'html')
    app.add_config_value('graphviz_dot_args', [], 'html')
    app.add_config_value('graphviz_output_format', 'png', 'html')
    app.add_css_file('graphviz.css')
    app.connect('build-finished', on_build_finished)
    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
