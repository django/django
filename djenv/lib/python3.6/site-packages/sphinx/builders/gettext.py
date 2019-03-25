# -*- coding: utf-8 -*-
"""
    sphinx.builders.gettext
    ~~~~~~~~~~~~~~~~~~~~~~~

    The MessageCatalogBuilder class.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from __future__ import unicode_literals

from codecs import open
from collections import defaultdict, OrderedDict
from datetime import datetime, tzinfo, timedelta
from os import path, walk, getenv
from time import time
from uuid import uuid4

from six import iteritems, StringIO

from sphinx.builders import Builder
from sphinx.domains.python import pairindextypes
from sphinx.errors import ThemeError
from sphinx.locale import __
from sphinx.util import split_index_msg, logging, status_iterator
from sphinx.util.console import bold  # type: ignore
from sphinx.util.i18n import find_catalog
from sphinx.util.nodes import extract_messages, traverse_translatable_index
from sphinx.util.osutil import relpath, ensuredir, canon_path
from sphinx.util.tags import Tags

if False:
    # For type annotation
    from typing import Any, DefaultDict, Dict, Iterable, List, Set, Tuple  # NOQA
    from docutils import nodes  # NOQA
    from sphinx.util.i18n import CatalogInfo  # NOQA
    from sphinx.application import Sphinx  # NOQA


logger = logging.getLogger(__name__)

POHEADER = r"""
# SOME DESCRIPTIVE TITLE.
# Copyright (C) %(copyright)s
# This file is distributed under the same license as the %(project)s package.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: %(project)s %(version)s\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: %(ctime)s\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"

"""[1:]


class Catalog(object):
    """Catalog of translatable messages."""

    def __init__(self):
        # type: () -> None
        self.messages = []  # type: List[unicode]
                            # retain insertion order, a la OrderedDict
        self.metadata = OrderedDict()  # type: Dict[unicode, List[Tuple[unicode, int, unicode]]]  # NOQA
                                        # msgid -> file, line, uid

    def add(self, msg, origin):
        # type: (unicode, MsgOrigin) -> None
        if not hasattr(origin, 'uid'):
            # Nodes that are replicated like todo don't have a uid,
            # however i18n is also unnecessary.
            return
        if msg not in self.metadata:  # faster lookup in hash
            self.messages.append(msg)
            self.metadata[msg] = []
        self.metadata[msg].append((origin.source, origin.line, origin.uid))


class MsgOrigin(object):
    """
    Origin holder for Catalog message origin.
    """

    def __init__(self, source, line):
        # type: (unicode, int) -> None
        self.source = source
        self.line = line
        self.uid = uuid4().hex


class I18nTags(Tags):
    """Dummy tags module for I18nBuilder.

    To translate all text inside of only nodes, this class
    always returns True value even if no tags are defined.
    """
    def eval_condition(self, condition):
        # type: (Any) -> bool
        return True


class I18nBuilder(Builder):
    """
    General i18n builder.
    """
    name = 'i18n'
    versioning_method = 'text'
    versioning_compare = None   # type: bool
                                # be set by `gettext_uuid`
    use_message_catalog = False

    def init(self):
        # type: () -> None
        Builder.init(self)
        self.env.set_versioning_method(self.versioning_method,
                                       self.env.config.gettext_uuid)
        self.tags = I18nTags()
        self.catalogs = defaultdict(Catalog)  # type: DefaultDict[unicode, Catalog]

    def get_target_uri(self, docname, typ=None):
        # type: (unicode, unicode) -> unicode
        return ''

    def get_outdated_docs(self):
        # type: () -> Set[unicode]
        return self.env.found_docs

    def prepare_writing(self, docnames):
        # type: (Set[unicode]) -> None
        return

    def compile_catalogs(self, catalogs, message):
        # type: (Set[CatalogInfo], unicode) -> None
        return

    def write_doc(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        catalog = self.catalogs[find_catalog(docname,
                                             self.config.gettext_compact)]

        for node, msg in extract_messages(doctree):
            catalog.add(msg, node)

        if 'index' in self.env.config.gettext_additional_targets:
            # Extract translatable messages from index entries.
            for node, entries in traverse_translatable_index(doctree):
                for typ, msg, tid, main, key_ in entries:
                    for m in split_index_msg(typ, msg):
                        if typ == 'pair' and m in pairindextypes.values():
                            # avoid built-in translated message was incorporated
                            # in 'sphinx.util.nodes.process_index_entry'
                            continue
                        catalog.add(m, node)


# determine tzoffset once to remain unaffected by DST change during build
timestamp = time()
tzdelta = datetime.fromtimestamp(timestamp) - \
    datetime.utcfromtimestamp(timestamp)
# set timestamp from SOURCE_DATE_EPOCH if set
# see https://reproducible-builds.org/specs/source-date-epoch/
source_date_epoch = getenv('SOURCE_DATE_EPOCH')
if source_date_epoch is not None:
    timestamp = float(source_date_epoch)
    tzdelta = timedelta(0)


class LocalTimeZone(tzinfo):

    def __init__(self, *args, **kw):
        # type: (Any, Any) -> None
        super(LocalTimeZone, self).__init__(*args, **kw)  # type: ignore
        self.tzdelta = tzdelta

    def utcoffset(self, dt):
        # type: (datetime) -> timedelta
        return self.tzdelta

    def dst(self, dt):
        # type: (datetime) -> timedelta
        return timedelta(0)


ltz = LocalTimeZone()


def should_write(filepath, new_content):
    # type: (unicode, unicode) -> bool
    if not path.exists(filepath):
        return True
    try:
        with open(filepath, 'r', encoding='utf-8') as oldpot:  # type: ignore
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


class MessageCatalogBuilder(I18nBuilder):
    """
    Builds gettext-style message catalogs (.pot files).
    """
    name = 'gettext'
    epilog = __('The message catalogs are in %(outdir)s.')

    def init(self):
        # type: () -> None
        I18nBuilder.init(self)
        self.create_template_bridge()
        self.templates.init(self)

    def _collect_templates(self):
        # type: () -> Set[unicode]
        template_files = set()
        for template_path in self.config.templates_path:
            tmpl_abs_path = path.join(self.app.srcdir, template_path)
            for dirpath, dirs, files in walk(tmpl_abs_path):
                for fn in files:
                    if fn.endswith('.html'):
                        filename = canon_path(path.join(dirpath, fn))
                        template_files.add(filename)
        return template_files

    def _extract_from_template(self):
        # type: () -> None
        files = list(self._collect_templates())
        files.sort()
        logger.info(bold(__('building [%s]: ') % self.name), nonl=1)
        logger.info(__('targets for %d template files'), len(files))

        extract_translations = self.templates.environment.extract_translations

        for template in status_iterator(files, __('reading templates... '), "purple",  # type: ignore  # NOQA
                                        len(files), self.app.verbosity):
            try:
                with open(template, 'r', encoding='utf-8') as f:  # type: ignore
                    context = f.read()
                for line, meth, msg in extract_translations(context):
                    origin = MsgOrigin(template, line)
                    self.catalogs['sphinx'].add(msg, origin)
            except Exception as exc:
                raise ThemeError('%s: %r' % (template, exc))

    def build(self, docnames, summary=None, method='update'):
        # type: (Iterable[unicode], unicode, unicode) -> None
        self._extract_from_template()
        I18nBuilder.build(self, docnames, summary, method)

    def finish(self):
        # type: () -> None
        I18nBuilder.finish(self)
        data = dict(
            version = self.config.version,
            copyright = self.config.copyright,
            project = self.config.project,
            ctime = datetime.fromtimestamp(
                timestamp, ltz).strftime('%Y-%m-%d %H:%M%z'),
        )
        for textdomain, catalog in status_iterator(iteritems(self.catalogs),  # type: ignore
                                                   __("writing message catalogs... "),
                                                   "darkgreen", len(self.catalogs),
                                                   self.app.verbosity,
                                                   lambda textdomain__: textdomain__[0]):
            # noop if config.gettext_compact is set
            ensuredir(path.join(self.outdir, path.dirname(textdomain)))

            pofn = path.join(self.outdir, textdomain + '.pot')
            output = StringIO()
            output.write(POHEADER % data)  # type: ignore

            for message in catalog.messages:
                positions = catalog.metadata[message]

                if self.config.gettext_location:
                    # generate "#: file1:line1\n#: file2:line2 ..."
                    output.write("#: %s\n" % "\n#: ".join(  # type: ignore
                        "%s:%s" % (canon_path(relpath(source, self.outdir)), line)
                        for source, line, _ in positions))
                if self.config.gettext_uuid:
                    # generate "# uuid1\n# uuid2\n ..."
                    output.write("# %s\n" % "\n# ".join(  # type: ignore
                        uid for _, _, uid in positions))

                # message contains *one* line of text ready for translation
                message = message.replace('\\', r'\\'). \
                    replace('"', r'\"'). \
                    replace('\n', '\\n"\n"')
                output.write('msgid "%s"\nmsgstr ""\n\n' % message)  # type: ignore

            content = output.getvalue()

            if should_write(pofn, content):
                with open(pofn, 'w', encoding='utf-8') as pofile:  # type: ignore
                    pofile.write(content)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_builder(MessageCatalogBuilder)

    app.add_config_value('gettext_compact', True, 'gettext')
    app.add_config_value('gettext_location', True, 'gettext')
    app.add_config_value('gettext_uuid', False, 'gettext')
    app.add_config_value('gettext_auto_build', True, 'env')
    app.add_config_value('gettext_additional_targets', [], 'env')

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
