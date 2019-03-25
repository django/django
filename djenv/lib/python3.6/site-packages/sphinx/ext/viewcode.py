# -*- coding: utf-8 -*-
"""
    sphinx.ext.viewcode
    ~~~~~~~~~~~~~~~~~~~

    Add links to module code in Python object descriptions.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import traceback
import warnings

from docutils import nodes
from six import iteritems, text_type

import sphinx
from sphinx import addnodes
from sphinx.deprecation import RemovedInSphinx30Warning
from sphinx.locale import _
from sphinx.pycode import ModuleAnalyzer
from sphinx.util import get_full_modname, logging, status_iterator
from sphinx.util.nodes import make_refnode

if False:
    # For type annotation
    from typing import Any, Dict, Iterable, Iterator, Set, Tuple  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.config import Config  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

logger = logging.getLogger(__name__)


def _get_full_modname(app, modname, attribute):
    # type: (Sphinx, str, unicode) -> unicode
    try:
        return get_full_modname(modname, attribute)
    except AttributeError:
        # sphinx.ext.viewcode can't follow class instance attribute
        # then AttributeError logging output only verbose mode.
        logger.verbose('Didn\'t find %s in %s', attribute, modname)
        return None
    except Exception as e:
        # sphinx.ext.viewcode follow python domain directives.
        # because of that, if there are no real modules exists that specified
        # by py:function or other directives, viewcode emits a lot of warnings.
        # It should be displayed only verbose mode.
        logger.verbose(traceback.format_exc().rstrip())
        logger.verbose('viewcode can\'t import %s, failed with error "%s"', modname, e)
        return None


def doctree_read(app, doctree):
    # type: (Sphinx, nodes.Node) -> None
    env = app.builder.env
    if not hasattr(env, '_viewcode_modules'):
        env._viewcode_modules = {}  # type: ignore
    if app.builder.name == "singlehtml":
        return
    if app.builder.name.startswith("epub") and not env.config.viewcode_enable_epub:
        return

    def has_tag(modname, fullname, docname, refname):
        entry = env._viewcode_modules.get(modname, None)  # type: ignore
        if entry is False:
            return

        code_tags = app.emit_firstresult('viewcode-find-source', modname)
        if code_tags is None:
            try:
                analyzer = ModuleAnalyzer.for_module(modname)
            except Exception:
                env._viewcode_modules[modname] = False  # type: ignore
                return

            if not isinstance(analyzer.code, text_type):
                code = analyzer.code.decode(analyzer.encoding)
            else:
                code = analyzer.code

            analyzer.find_tags()
            tags = analyzer.tags
        else:
            code, tags = code_tags

        if entry is None or entry[0] != code:
            entry = code, tags, {}, refname
            env._viewcode_modules[modname] = entry  # type: ignore
        _, tags, used, _ = entry
        if fullname in tags:
            used[fullname] = docname
            return True

    for objnode in doctree.traverse(addnodes.desc):
        if objnode.get('domain') != 'py':
            continue
        names = set()  # type: Set[unicode]
        for signode in objnode:
            if not isinstance(signode, addnodes.desc_signature):
                continue
            modname = signode.get('module')
            fullname = signode.get('fullname')
            refname = modname
            if env.config.viewcode_follow_imported_members:
                new_modname = app.emit_firstresult(
                    'viewcode-follow-imported', modname, fullname,
                )
                if not new_modname:
                    new_modname = _get_full_modname(app, modname, fullname)
                modname = new_modname
            if not modname:
                continue
            fullname = signode.get('fullname')
            if not has_tag(modname, fullname, env.docname, refname):
                continue
            if fullname in names:
                # only one link per name, please
                continue
            names.add(fullname)
            pagename = '_modules/' + modname.replace('.', '/')
            onlynode = addnodes.only(expr='html')
            onlynode += addnodes.pending_xref(
                '', reftype='viewcode', refdomain='std', refexplicit=False,
                reftarget=pagename, refid=fullname,
                refdoc=env.docname)
            onlynode[0] += nodes.inline('', _('[source]'),
                                        classes=['viewcode-link'])
            signode += onlynode


def env_merge_info(app, env, docnames, other):
    # type: (Sphinx, BuildEnvironment, Iterable[unicode], BuildEnvironment) -> None
    if not hasattr(other, '_viewcode_modules'):
        return
    # create a _viewcode_modules dict on the main environment
    if not hasattr(env, '_viewcode_modules'):
        env._viewcode_modules = {}  # type: ignore
    # now merge in the information from the subprocess
    env._viewcode_modules.update(other._viewcode_modules)  # type: ignore


def missing_reference(app, env, node, contnode):
    # type: (Sphinx, BuildEnvironment, nodes.Node, nodes.Node) -> nodes.Node
    # resolve our "viewcode" reference nodes -- they need special treatment
    if node['reftype'] == 'viewcode':
        return make_refnode(app.builder, node['refdoc'], node['reftarget'],
                            node['refid'], contnode)


def collect_pages(app):
    # type: (Sphinx) -> Iterator[Tuple[unicode, Dict[unicode, Any], unicode]]
    env = app.builder.env
    if not hasattr(env, '_viewcode_modules'):
        return
    highlighter = app.builder.highlighter  # type: ignore
    urito = app.builder.get_relative_uri

    modnames = set(env._viewcode_modules)  # type: ignore

#    app.builder.info(' (%d module code pages)' %
#                     len(env._viewcode_modules), nonl=1)

    for modname, entry in status_iterator(
            sorted(iteritems(env._viewcode_modules)),  # type: ignore
            'highlighting module code... ', "blue",
            len(env._viewcode_modules),  # type: ignore
            app.verbosity, lambda x: x[0]):
        if not entry:
            continue
        code, tags, used, refname = entry
        # construct a page name for the highlighted source
        pagename = '_modules/' + modname.replace('.', '/')
        # highlight the source using the builder's highlighter
        if env.config.highlight_language in ('python3', 'default', 'none'):
            lexer = env.config.highlight_language
        else:
            lexer = 'python'
        highlighted = highlighter.highlight_block(code, lexer, linenos=False)
        # split the code into lines
        lines = highlighted.splitlines()
        # split off wrap markup from the first line of the actual code
        before, after = lines[0].split('<pre>')
        lines[0:1] = [before + '<pre>', after]
        # nothing to do for the last line; it always starts with </pre> anyway
        # now that we have code lines (starting at index 1), insert anchors for
        # the collected tags (HACK: this only works if the tag boundaries are
        # properly nested!)
        maxindex = len(lines) - 1
        for name, docname in iteritems(used):
            type, start, end = tags[name]
            backlink = urito(pagename, docname) + '#' + refname + '.' + name
            lines[start] = (
                '<div class="viewcode-block" id="%s"><a class="viewcode-back" '
                'href="%s">%s</a>' % (name, backlink, _('[docs]')) +
                lines[start])
            lines[min(end, maxindex)] += '</div>'
        # try to find parents (for submodules)
        parents = []
        parent = modname
        while '.' in parent:
            parent = parent.rsplit('.', 1)[0]
            if parent in modnames:
                parents.append({
                    'link': urito(pagename, '_modules/' +
                                  parent.replace('.', '/')),
                    'title': parent})
        parents.append({'link': urito(pagename, '_modules/index'),
                        'title': _('Module code')})
        parents.reverse()
        # putting it all together
        context = {
            'parents': parents,
            'title': modname,
            'body': (_('<h1>Source code for %s</h1>') % modname +
                     '\n'.join(lines)),
        }  # type: Dict[unicode, Any]
        yield (pagename, context, 'page.html')

    if not modnames:
        return

    html = ['\n']
    # the stack logic is needed for using nested lists for submodules
    stack = ['']
    for modname in sorted(modnames):
        if modname.startswith(stack[-1]):
            stack.append(modname + '.')
            html.append('<ul>')
        else:
            stack.pop()
            while not modname.startswith(stack[-1]):
                stack.pop()
                html.append('</ul>')
            stack.append(modname + '.')
        html.append('<li><a href="%s">%s</a></li>\n' % (
            urito('_modules/index', '_modules/' + modname.replace('.', '/')),
            modname))
    html.append('</ul>' * (len(stack) - 1))
    context = {
        'title': _('Overview: module code'),
        'body': (_('<h1>All modules for which code is available</h1>') +
                 ''.join(html)),
    }

    yield ('_modules/index', context, 'page.html')


def migrate_viewcode_import(app, config):
    # type: (Sphinx, Config) -> None
    if config.viewcode_import is not None:
        warnings.warn('viewcode_import was renamed to viewcode_follow_imported_members. '
                      'Please update your configuration.',
                      RemovedInSphinx30Warning, stacklevel=2)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_config_value('viewcode_import', None, False)
    app.add_config_value('viewcode_enable_epub', False, False)
    app.add_config_value('viewcode_follow_imported_members', True, False)
    app.connect('doctree-read', doctree_read)
    app.connect('env-merge-info', env_merge_info)
    app.connect('html-collect-pages', collect_pages)
    app.connect('missing-reference', missing_reference)
    # app.add_config_value('viewcode_include_modules', [], 'env')
    # app.add_config_value('viewcode_exclude_modules', [], 'env')
    app.add_event('viewcode-find-source')
    app.add_event('viewcode-follow-imported')
    return {
        'version': sphinx.__display_version__,
        'env_version': 1,
        'parallel_read_safe': True
    }
