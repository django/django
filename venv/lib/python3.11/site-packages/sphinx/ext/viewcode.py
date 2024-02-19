"""Add links to module code in Python object descriptions."""

from __future__ import annotations

import posixpath
import traceback
from importlib import import_module
from os import path
from typing import TYPE_CHECKING, Any, cast

from docutils import nodes
from docutils.nodes import Element, Node

import sphinx
from sphinx import addnodes
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.locale import _, __
from sphinx.pycode import ModuleAnalyzer
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util import logging
from sphinx.util.display import status_iterator
from sphinx.util.nodes import make_refnode

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment

logger = logging.getLogger(__name__)


OUTPUT_DIRNAME = '_modules'


class viewcode_anchor(Element):
    """Node for viewcode anchors.

    This node will be processed in the resolving phase.
    For viewcode supported builders, they will be all converted to the anchors.
    For not supported builders, they will be removed.
    """


def _get_full_modname(modname: str, attribute: str) -> str | None:
    try:
        if modname is None:
            # Prevents a TypeError: if the last getattr() call will return None
            # then it's better to return it directly
            return None
        module = import_module(modname)

        # Allow an attribute to have multiple parts and incidentally allow
        # repeated .s in the attribute.
        value = module
        for attr in attribute.split('.'):
            if attr:
                value = getattr(value, attr)

        return getattr(value, '__module__', None)
    except AttributeError:
        # sphinx.ext.viewcode can't follow class instance attribute
        # then AttributeError logging output only verbose mode.
        logger.verbose("Didn't find %s in %s", attribute, modname)
        return None
    except Exception as e:
        # sphinx.ext.viewcode follow python domain directives.
        # because of that, if there are no real modules exists that specified
        # by py:function or other directives, viewcode emits a lot of warnings.
        # It should be displayed only verbose mode.
        logger.verbose(traceback.format_exc().rstrip())
        logger.verbose('viewcode can\'t import %s, failed with error "%s"', modname, e)
        return None


def is_supported_builder(builder: Builder) -> bool:
    if builder.format != 'html':
        return False
    if builder.name == 'singlehtml':
        return False
    if builder.name.startswith('epub') and not builder.config.viewcode_enable_epub:
        return False
    return True


def doctree_read(app: Sphinx, doctree: Node) -> None:
    env = app.builder.env
    if not hasattr(env, '_viewcode_modules'):
        env._viewcode_modules = {}  # type: ignore[attr-defined]

    def has_tag(modname: str, fullname: str, docname: str, refname: str) -> bool:
        entry = env._viewcode_modules.get(modname, None)  # type: ignore[attr-defined]
        if entry is False:
            return False

        code_tags = app.emit_firstresult('viewcode-find-source', modname)
        if code_tags is None:
            try:
                analyzer = ModuleAnalyzer.for_module(modname)
                analyzer.find_tags()
            except Exception:
                env._viewcode_modules[modname] = False  # type: ignore[attr-defined]
                return False

            code = analyzer.code
            tags = analyzer.tags
        else:
            code, tags = code_tags

        if entry is None or entry[0] != code:
            entry = code, tags, {}, refname
            env._viewcode_modules[modname] = entry  # type: ignore[attr-defined]
        _, tags, used, _ = entry
        if fullname in tags:
            used[fullname] = docname
            return True

        return False

    for objnode in list(doctree.findall(addnodes.desc)):
        if objnode.get('domain') != 'py':
            continue
        names: set[str] = set()
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
                    new_modname = _get_full_modname(modname, fullname)
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
            pagename = posixpath.join(OUTPUT_DIRNAME, modname.replace('.', '/'))
            signode += viewcode_anchor(reftarget=pagename, refid=fullname, refdoc=env.docname)


def env_merge_info(app: Sphinx, env: BuildEnvironment, docnames: Iterable[str],
                   other: BuildEnvironment) -> None:
    if not hasattr(other, '_viewcode_modules'):
        return
    # create a _viewcode_modules dict on the main environment
    if not hasattr(env, '_viewcode_modules'):
        env._viewcode_modules = {}  # type: ignore[attr-defined]
    # now merge in the information from the subprocess
    for modname, entry in other._viewcode_modules.items():
        if modname not in env._viewcode_modules:  # type: ignore[attr-defined]
            env._viewcode_modules[modname] = entry  # type: ignore[attr-defined]
        else:
            if env._viewcode_modules[modname]:  # type: ignore[attr-defined]
                used = env._viewcode_modules[modname][2]  # type: ignore[attr-defined]
                for fullname, docname in entry[2].items():
                    if fullname not in used:
                        used[fullname] = docname


def env_purge_doc(app: Sphinx, env: BuildEnvironment, docname: str) -> None:
    modules = getattr(env, '_viewcode_modules', {})

    for modname, entry in list(modules.items()):
        if entry is False:
            continue

        code, tags, used, refname = entry
        for fullname in list(used):
            if used[fullname] == docname:
                used.pop(fullname)

        if len(used) == 0:
            modules.pop(modname)


class ViewcodeAnchorTransform(SphinxPostTransform):
    """Convert or remove viewcode_anchor nodes depends on builder."""
    default_priority = 100

    def run(self, **kwargs: Any) -> None:
        if is_supported_builder(self.app.builder):
            self.convert_viewcode_anchors()
        else:
            self.remove_viewcode_anchors()

    def convert_viewcode_anchors(self) -> None:
        for node in self.document.findall(viewcode_anchor):
            anchor = nodes.inline('', _('[source]'), classes=['viewcode-link'])
            refnode = make_refnode(self.app.builder, node['refdoc'], node['reftarget'],
                                   node['refid'], anchor)
            node.replace_self(refnode)

    def remove_viewcode_anchors(self) -> None:
        for node in list(self.document.findall(viewcode_anchor)):
            node.parent.remove(node)


def get_module_filename(app: Sphinx, modname: str) -> str | None:
    """Get module filename for *modname*."""
    source_info = app.emit_firstresult('viewcode-find-source', modname)
    if source_info:
        return None
    else:
        try:
            filename, source = ModuleAnalyzer.get_module_source(modname)
            return filename
        except Exception:
            return None


def should_generate_module_page(app: Sphinx, modname: str) -> bool:
    """Check generation of module page is needed."""
    module_filename = get_module_filename(app, modname)
    if module_filename is None:
        # Always (re-)generate module page when module filename is not found.
        return True

    builder = cast(StandaloneHTMLBuilder, app.builder)
    basename = modname.replace('.', '/') + builder.out_suffix
    page_filename = path.join(app.outdir, '_modules/', basename)

    try:
        if path.getmtime(module_filename) <= path.getmtime(page_filename):
            # generation is not needed if the HTML page is newer than module file.
            return False
    except OSError:
        pass

    return True


def collect_pages(app: Sphinx) -> Generator[tuple[str, dict[str, Any], str], None, None]:
    env = app.builder.env
    if not hasattr(env, '_viewcode_modules'):
        return
    if not is_supported_builder(app.builder):
        return
    highlighter = app.builder.highlighter  # type: ignore[attr-defined]
    urito = app.builder.get_relative_uri

    modnames = set(env._viewcode_modules)

    for modname, entry in status_iterator(
            sorted(env._viewcode_modules.items()),
            __('highlighting module code... '), "blue",
            len(env._viewcode_modules),
            app.verbosity, lambda x: x[0]):
        if not entry:
            continue
        if not should_generate_module_page(app, modname):
            continue

        code, tags, used, refname = entry
        # construct a page name for the highlighted source
        pagename = posixpath.join(OUTPUT_DIRNAME, modname.replace('.', '/'))
        # highlight the source using the builder's highlighter
        if env.config.highlight_language in {'default', 'none'}:
            lexer = env.config.highlight_language
        else:
            lexer = 'python'
        linenos = 'inline' * env.config.viewcode_line_numbers
        highlighted = highlighter.highlight_block(code, lexer, linenos=linenos)
        # split the code into lines
        lines = highlighted.splitlines()
        # split off wrap markup from the first line of the actual code
        before, after = lines[0].split('<pre>')
        lines[0:1] = [before + '<pre>', after]
        # nothing to do for the last line; it always starts with </pre> anyway
        # now that we have code lines (starting at index 1), insert anchors for
        # the collected tags (HACK: this only works if the tag boundaries are
        # properly nested!)
        max_index = len(lines) - 1
        link_text = _('[docs]')
        for name, docname in used.items():
            type, start, end = tags[name]
            backlink = urito(pagename, docname) + '#' + refname + '.' + name
            lines[start] = (f'<div class="viewcode-block" id="{name}">\n'
                            f'<a class="viewcode-back" href="{backlink}">{link_text}</a>\n'
                            + lines[start])
            lines[min(end, max_index)] += '</div>\n'

        # try to find parents (for submodules)
        parents = []
        parent = modname
        while '.' in parent:
            parent = parent.rsplit('.', 1)[0]
            if parent in modnames:
                parents.append({
                    'link': urito(pagename,
                                  posixpath.join(OUTPUT_DIRNAME, parent.replace('.', '/'))),
                    'title': parent})
        parents.append({'link': urito(pagename, posixpath.join(OUTPUT_DIRNAME, 'index')),
                        'title': _('Module code')})
        parents.reverse()
        # putting it all together
        context = {
            'parents': parents,
            'title': modname,
            'body': (_('<h1>Source code for %s</h1>') % modname +
                     '\n'.join(lines)),
        }
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
        relative_uri = urito(posixpath.join(OUTPUT_DIRNAME, 'index'),
                             posixpath.join(OUTPUT_DIRNAME, modname.replace('.', '/')))
        html.append(f'<li><a href="{relative_uri}">{modname}</a></li>\n')
    html.append('</ul>' * (len(stack) - 1))
    context = {
        'title': _('Overview: module code'),
        'body': (_('<h1>All modules for which code is available</h1>') +
                 ''.join(html)),
    }

    yield (posixpath.join(OUTPUT_DIRNAME, 'index'), context, 'page.html')


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_config_value('viewcode_import', None, False)
    app.add_config_value('viewcode_enable_epub', False, False)
    app.add_config_value('viewcode_follow_imported_members', True, False)
    app.add_config_value('viewcode_line_numbers', False, 'env', (bool,))
    app.connect('doctree-read', doctree_read)
    app.connect('env-merge-info', env_merge_info)
    app.connect('env-purge-doc', env_purge_doc)
    app.connect('html-collect-pages', collect_pages)
    # app.add_config_value('viewcode_include_modules', [], 'env')
    # app.add_config_value('viewcode_exclude_modules', [], 'env')
    app.add_event('viewcode-find-source')
    app.add_event('viewcode-follow-imported')
    app.add_post_transform(ViewcodeAnchorTransform)
    return {
        'version': sphinx.__display_version__,
        'env_version': 1,
        'parallel_read_safe': True,
    }
