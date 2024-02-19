"""Manual pages builder."""

from __future__ import annotations

import warnings
from os import path
from typing import TYPE_CHECKING, Any

from docutils.frontend import OptionParser
from docutils.io import FileOutput

from sphinx import addnodes
from sphinx.builders import Builder
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.console import darkgreen  # type: ignore[attr-defined]
from sphinx.util.display import progress_message
from sphinx.util.nodes import inline_all_toctrees
from sphinx.util.osutil import ensuredir, make_filename_from_project
from sphinx.writers.manpage import ManualPageTranslator, ManualPageWriter

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config

logger = logging.getLogger(__name__)


class ManualPageBuilder(Builder):
    """
    Builds groff output in manual page format.
    """
    name = 'man'
    format = 'man'
    epilog = __('The manual pages are in %(outdir)s.')

    default_translator_class = ManualPageTranslator
    supported_image_types: list[str] = []

    def init(self) -> None:
        if not self.config.man_pages:
            logger.warning(__('no "man_pages" config value found; no manual pages '
                              'will be written'))

    def get_outdated_docs(self) -> str | list[str]:
        return 'all manpages'  # for now

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        return ''

    @progress_message(__('writing'))
    def write(self, *ignored: Any) -> None:
        docwriter = ManualPageWriter(self)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            # DeprecationWarning: The frontend.OptionParser class will be replaced
            # by a subclass of argparse.ArgumentParser in Docutils 0.21 or later.
            docsettings: Any = OptionParser(
                defaults=self.env.settings,
                components=(docwriter,),
                read_config_files=True).get_default_values()

        for info in self.config.man_pages:
            docname, name, description, authors, section = info
            if docname not in self.env.all_docs:
                logger.warning(__('"man_pages" config value references unknown '
                                  'document %s'), docname)
                continue
            if isinstance(authors, str):
                if authors:
                    authors = [authors]
                else:
                    authors = []

            docsettings.title = name
            docsettings.subtitle = description
            docsettings.authors = authors
            docsettings.section = section

            if self.config.man_make_section_directory:
                dirname = 'man%s' % section
                ensuredir(path.join(self.outdir, dirname))
                targetname = f'{dirname}/{name}.{section}'
            else:
                targetname = f'{name}.{section}'

            logger.info(darkgreen(targetname) + ' { ', nonl=True)
            destination = FileOutput(
                destination_path=path.join(self.outdir, targetname),
                encoding='utf-8')

            tree = self.env.get_doctree(docname)
            docnames: set[str] = set()
            largetree = inline_all_toctrees(self, docnames, docname, tree,
                                            darkgreen, [docname])
            largetree.settings = docsettings
            logger.info('} ', nonl=True)
            self.env.resolve_references(largetree, docname, self)
            # remove pending_xref nodes
            for pendingnode in largetree.findall(addnodes.pending_xref):
                pendingnode.replace_self(pendingnode.children)

            docwriter.write(largetree, destination)

    def finish(self) -> None:
        pass


def default_man_pages(config: Config) -> list[tuple[str, str, str, list[str], int]]:
    """ Better default man_pages settings. """
    filename = make_filename_from_project(config.project)
    return [(config.root_doc, filename, f'{config.project} {config.release}',
             [config.author], 1)]


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(ManualPageBuilder)

    app.add_config_value('man_pages', default_man_pages, False)
    app.add_config_value('man_show_urls', False, False)
    app.add_config_value('man_make_section_directory', False, False)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
