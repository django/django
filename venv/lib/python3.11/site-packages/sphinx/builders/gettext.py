"""The MessageCatalogBuilder class."""

from __future__ import annotations

import time
from codecs import open
from collections import defaultdict
from os import getenv, path, walk
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from docutils import nodes

from sphinx import addnodes, package_dir
from sphinx.builders import Builder
from sphinx.errors import ThemeError
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.console import bold  # type: ignore[attr-defined]
from sphinx.util.display import status_iterator
from sphinx.util.i18n import CatalogInfo, docname_to_domain
from sphinx.util.index_entries import split_index_msg
from sphinx.util.nodes import extract_messages, traverse_translatable_index
from sphinx.util.osutil import canon_path, ensuredir, relpath
from sphinx.util.tags import Tags
from sphinx.util.template import SphinxRenderer

if TYPE_CHECKING:
    import os
    from collections.abc import Generator, Iterable

    from docutils.nodes import Element

    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)


class Message:
    """An entry of translatable message."""
    def __init__(self, text: str, locations: list[tuple[str, int]], uuids: list[str]):
        self.text = text
        self.locations = locations
        self.uuids = uuids


class Catalog:
    """Catalog of translatable messages."""

    def __init__(self) -> None:
        self.messages: list[str] = []  # retain insertion order

        # msgid -> file, line, uid
        self.metadata: dict[str, list[tuple[str, int, str]]] = {}

    def add(self, msg: str, origin: Element | MsgOrigin) -> None:
        if not hasattr(origin, 'uid'):
            # Nodes that are replicated like todo don't have a uid,
            # however i18n is also unnecessary.
            return
        if msg not in self.metadata:  # faster lookup in hash
            self.messages.append(msg)
            self.metadata[msg] = []
        line = origin.line
        if line is None:
            line = -1
        self.metadata[msg].append((origin.source, line, origin.uid))

    def __iter__(self) -> Generator[Message, None, None]:
        for message in self.messages:
            positions = sorted({(source, line) for source, line, uuid
                               in self.metadata[message]})
            uuids = [uuid for source, line, uuid in self.metadata[message]]
            yield Message(message, positions, uuids)


class MsgOrigin:
    """
    Origin holder for Catalog message origin.
    """

    def __init__(self, source: str, line: int) -> None:
        self.source = source
        self.line = line
        self.uid = uuid4().hex


class GettextRenderer(SphinxRenderer):
    def __init__(
        self, template_path: list[str | os.PathLike[str]] | None = None,
            outdir: str | os.PathLike[str] | None = None,
    ) -> None:
        self.outdir = outdir
        if template_path is None:
            template_path = [path.join(package_dir, 'templates', 'gettext')]
        super().__init__(template_path)

        def escape(s: str) -> str:
            s = s.replace('\\', r'\\')
            s = s.replace('"', r'\"')
            return s.replace('\n', '\\n"\n"')

        # use texescape as escape filter
        self.env.filters['e'] = escape
        self.env.filters['escape'] = escape

    def render(self, filename: str, context: dict[str, Any]) -> str:
        def _relpath(s: str) -> str:
            return canon_path(relpath(s, self.outdir))

        context['relpath'] = _relpath
        return super().render(filename, context)


class I18nTags(Tags):
    """Dummy tags module for I18nBuilder.

    To translate all text inside of only nodes, this class
    always returns True value even if no tags are defined.
    """
    def eval_condition(self, condition: Any) -> bool:
        return True


class I18nBuilder(Builder):
    """
    General i18n builder.
    """
    name = 'i18n'
    versioning_method = 'text'
    use_message_catalog = False

    def init(self) -> None:
        super().init()
        self.env.set_versioning_method(self.versioning_method,
                                       self.env.config.gettext_uuid)
        self.tags = I18nTags()
        self.catalogs: defaultdict[str, Catalog] = defaultdict(Catalog)

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        return ''

    def get_outdated_docs(self) -> set[str]:
        return self.env.found_docs

    def prepare_writing(self, docnames: set[str]) -> None:
        return

    def compile_catalogs(self, catalogs: set[CatalogInfo], message: str) -> None:
        return

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        catalog = self.catalogs[docname_to_domain(docname, self.config.gettext_compact)]

        for toctree in self.env.tocs[docname].findall(addnodes.toctree):
            for node, msg in extract_messages(toctree):
                node.uid = ''  # type: ignore[attr-defined]  # Hack UUID model
                catalog.add(msg, node)

        for node, msg in extract_messages(doctree):
            # Do not extract messages from within substitution definitions.
            if not _is_node_in_substitution_definition(node):
                catalog.add(msg, node)

        if 'index' in self.env.config.gettext_additional_targets:
            # Extract translatable messages from index entries.
            for node, entries in traverse_translatable_index(doctree):
                for entry_type, value, _target_id, _main, _category_key in entries:
                    for m in split_index_msg(entry_type, value):
                        catalog.add(m, node)


# If set, use the timestamp from SOURCE_DATE_EPOCH
# https://reproducible-builds.org/specs/source-date-epoch/
if (source_date_epoch := getenv('SOURCE_DATE_EPOCH')) is not None:
    timestamp = time.gmtime(float(source_date_epoch))
else:
    # determine timestamp once to remain unaffected by DST changes during build
    timestamp = time.localtime()
ctime = time.strftime('%Y-%m-%d %H:%M%z', timestamp)


def should_write(filepath: str, new_content: str) -> bool:
    if not path.exists(filepath):
        return True
    try:
        with open(filepath, encoding='utf-8') as oldpot:
            old_content = oldpot.read()
            old_header_index = old_content.index('"POT-Creation-Date:')
            new_header_index = new_content.index('"POT-Creation-Date:')
            old_body_index = old_content.index('"PO-Revision-Date:')
            new_body_index = new_content.index('"PO-Revision-Date:')
            return ((old_content[:old_header_index] != new_content[:new_header_index]) or
                    (new_content[new_body_index:] != old_content[old_body_index:]))
    except ValueError:
        pass

    return True


def _is_node_in_substitution_definition(node: nodes.Node) -> bool:
    """Check "node" to test if it is in a substitution definition."""
    while node.parent:
        if isinstance(node, nodes.substitution_definition):
            return True
        node = node.parent
    return False


class MessageCatalogBuilder(I18nBuilder):
    """
    Builds gettext-style message catalogs (.pot files).
    """
    name = 'gettext'
    epilog = __('The message catalogs are in %(outdir)s.')

    def init(self) -> None:
        super().init()
        self.create_template_bridge()
        self.templates.init(self)

    def _collect_templates(self) -> set[str]:
        template_files = set()
        for template_path in self.config.templates_path:
            tmpl_abs_path = path.join(self.app.srcdir, template_path)
            for dirpath, _dirs, files in walk(tmpl_abs_path):
                for fn in files:
                    if fn.endswith('.html'):
                        filename = canon_path(path.join(dirpath, fn))
                        template_files.add(filename)
        return template_files

    def _extract_from_template(self) -> None:
        files = list(self._collect_templates())
        files.sort()
        logger.info(bold(__('building [%s]: ') % self.name), nonl=True)
        logger.info(__('targets for %d template files'), len(files))

        extract_translations = self.templates.environment.extract_translations

        for template in status_iterator(files, __('reading templates... '), "purple",
                                        len(files), self.app.verbosity):
            try:
                with open(template, encoding='utf-8') as f:
                    context = f.read()
                for line, _meth, msg in extract_translations(context):
                    origin = MsgOrigin(template, line)
                    self.catalogs['sphinx'].add(msg, origin)
            except Exception as exc:
                msg = f'{template}: {exc!r}'
                raise ThemeError(msg) from exc

    def build(
        self,
        docnames: Iterable[str] | None,
        summary: str | None = None,
        method: str = 'update',
    ) -> None:
        self._extract_from_template()
        super().build(docnames, summary, method)

    def finish(self) -> None:
        super().finish()
        context = {
            'version': self.config.version,
            'copyright': self.config.copyright,
            'project': self.config.project,
            'last_translator': self.config.gettext_last_translator,
            'language_team': self.config.gettext_language_team,
            'ctime': ctime,
            'display_location': self.config.gettext_location,
            'display_uuid': self.config.gettext_uuid,
        }
        for textdomain, catalog in status_iterator(self.catalogs.items(),
                                                   __("writing message catalogs... "),
                                                   "darkgreen", len(self.catalogs),
                                                   self.app.verbosity,
                                                   lambda textdomain__: textdomain__[0]):
            # noop if config.gettext_compact is set
            ensuredir(path.join(self.outdir, path.dirname(textdomain)))

            context['messages'] = list(catalog)
            content = GettextRenderer(outdir=self.outdir).render('message.pot_t', context)

            pofn = path.join(self.outdir, textdomain + '.pot')
            if should_write(pofn, content):
                with open(pofn, 'w', encoding='utf-8') as pofile:
                    pofile.write(content)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(MessageCatalogBuilder)

    app.add_config_value('gettext_compact', True, 'gettext', {bool, str})
    app.add_config_value('gettext_location', True, 'gettext')
    app.add_config_value('gettext_uuid', False, 'gettext')
    app.add_config_value('gettext_auto_build', True, 'env')
    app.add_config_value('gettext_additional_targets', [], 'env')
    app.add_config_value('gettext_last_translator', 'FULL NAME <EMAIL@ADDRESS>', 'gettext')
    app.add_config_value('gettext_language_team', 'LANGUAGE <LL@li.org>', 'gettext')

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
