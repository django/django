"""Single HTML builders."""

from __future__ import annotations

from os import path
from typing import TYPE_CHECKING, Any

from docutils import nodes

from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment.adapters.toctree import global_toctree_for_doc
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.console import darkgreen  # type: ignore[attr-defined]
from sphinx.util.display import progress_message
from sphinx.util.nodes import inline_all_toctrees

if TYPE_CHECKING:
    from docutils.nodes import Node

    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)


class SingleFileHTMLBuilder(StandaloneHTMLBuilder):
    """
    A StandaloneHTMLBuilder subclass that puts the whole document tree on one
    HTML page.
    """
    name = 'singlehtml'
    epilog = __('The HTML page is in %(outdir)s.')

    copysource = False

    def get_outdated_docs(self) -> str | list[str]:  # type: ignore[override]
        return 'all documents'

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        if docname in self.env.all_docs:
            # all references are on the same page...
            return self.config.root_doc + self.out_suffix + \
                '#document-' + docname
        else:
            # chances are this is a html_additional_page
            return docname + self.out_suffix

    def get_relative_uri(self, from_: str, to: str, typ: str | None = None) -> str:
        # ignore source
        return self.get_target_uri(to, typ)

    def fix_refuris(self, tree: Node) -> None:
        # fix refuris with double anchor
        fname = self.config.root_doc + self.out_suffix
        for refnode in tree.findall(nodes.reference):
            if 'refuri' not in refnode:
                continue
            refuri = refnode['refuri']
            hashindex = refuri.find('#')
            if hashindex < 0:
                continue
            hashindex = refuri.find('#', hashindex + 1)
            if hashindex >= 0:
                refnode['refuri'] = fname + refuri[hashindex:]

    def _get_local_toctree(self, docname: str, collapse: bool = True, **kwargs: Any) -> str:
        if isinstance(includehidden := kwargs.get('includehidden'), str):
            if includehidden.lower() == 'false':
                kwargs['includehidden'] = False
            elif includehidden.lower() == 'true':
                kwargs['includehidden'] = True
        if kwargs.get('maxdepth') == '':
            kwargs.pop('maxdepth')
        toctree = global_toctree_for_doc(self.env, docname, self, collapse=collapse, **kwargs)
        if toctree is not None:
            self.fix_refuris(toctree)
        return self.render_partial(toctree)['fragment']

    def assemble_doctree(self) -> nodes.document:
        master = self.config.root_doc
        tree = self.env.get_doctree(master)
        tree = inline_all_toctrees(self, set(), master, tree, darkgreen, [master])
        tree['docname'] = master
        self.env.resolve_references(tree, master, self)
        self.fix_refuris(tree)
        return tree

    def assemble_toc_secnumbers(self) -> dict[str, dict[str, tuple[int, ...]]]:
        # Assemble toc_secnumbers to resolve section numbers on SingleHTML.
        # Merge all secnumbers to single secnumber.
        #
        # Note: current Sphinx has refid confliction in singlehtml mode.
        #       To avoid the problem, it replaces key of secnumbers to
        #       tuple of docname and refid.
        #
        #       There are related codes in inline_all_toctres() and
        #       HTMLTranslter#add_secnumber().
        new_secnumbers: dict[str, tuple[int, ...]] = {}
        for docname, secnums in self.env.toc_secnumbers.items():
            for id, secnum in secnums.items():
                alias = f"{docname}/{id}"
                new_secnumbers[alias] = secnum

        return {self.config.root_doc: new_secnumbers}

    def assemble_toc_fignumbers(self) -> dict[str, dict[str, dict[str, tuple[int, ...]]]]:
        # Assemble toc_fignumbers to resolve figure numbers on SingleHTML.
        # Merge all fignumbers to single fignumber.
        #
        # Note: current Sphinx has refid confliction in singlehtml mode.
        #       To avoid the problem, it replaces key of secnumbers to
        #       tuple of docname and refid.
        #
        #       There are related codes in inline_all_toctres() and
        #       HTMLTranslter#add_fignumber().
        new_fignumbers: dict[str, dict[str, tuple[int, ...]]] = {}
        # {'foo': {'figure': {'id2': (2,), 'id1': (1,)}}, 'bar': {'figure': {'id1': (3,)}}}
        for docname, fignumlist in self.env.toc_fignumbers.items():
            for figtype, fignums in fignumlist.items():
                alias = f"{docname}/{figtype}"
                new_fignumbers.setdefault(alias, {})
                for id, fignum in fignums.items():
                    new_fignumbers[alias][id] = fignum

        return {self.config.root_doc: new_fignumbers}

    def get_doc_context(self, docname: str, body: str, metatags: str) -> dict[str, Any]:
        # no relation links...
        toctree = global_toctree_for_doc(self.env, self.config.root_doc, self, collapse=False)
        # if there is no toctree, toc is None
        if toctree:
            self.fix_refuris(toctree)
            toc = self.render_partial(toctree)['fragment']
            display_toc = True
        else:
            toc = ''
            display_toc = False
        return {
            'parents': [],
            'prev': None,
            'next': None,
            'docstitle': None,
            'title': self.config.html_title,
            'meta': None,
            'body': body,
            'metatags': metatags,
            'rellinks': [],
            'sourcename': '',
            'toc': toc,
            'display_toc': display_toc,
        }

    def write(self, *ignored: Any) -> None:
        docnames = self.env.all_docs

        with progress_message(__('preparing documents')):
            self.prepare_writing(docnames)  # type: ignore[arg-type]

        with progress_message(__('assembling single document')):
            doctree = self.assemble_doctree()
            self.env.toc_secnumbers = self.assemble_toc_secnumbers()
            self.env.toc_fignumbers = self.assemble_toc_fignumbers()

        with progress_message(__('writing')):
            self.write_doc_serialized(self.config.root_doc, doctree)
            self.write_doc(self.config.root_doc, doctree)

    def finish(self) -> None:
        self.write_additional_files()
        self.copy_image_files()
        self.copy_download_files()
        self.copy_static_files()
        self.copy_extra_files()
        self.write_buildinfo()
        self.dump_inventory()

    @progress_message(__('writing additional files'))
    def write_additional_files(self) -> None:
        # no indices or search pages are supported

        # additional pages from conf.py
        for pagename, template in self.config.html_additional_pages.items():
            logger.info(' ' + pagename, nonl=True)
            self.handle_page(pagename, {}, template)

        if self.config.html_use_opensearch:
            logger.info(' opensearch', nonl=True)
            fn = path.join(self.outdir, '_static', 'opensearch.xml')
            self.handle_page('opensearch', {}, 'opensearch.xml', outfilename=fn)


def setup(app: Sphinx) -> dict[str, Any]:
    app.setup_extension('sphinx.builders.html')

    app.add_builder(SingleFileHTMLBuilder)
    app.add_config_value('singlehtml_sidebars', lambda self: self.html_sidebars, 'html')

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
