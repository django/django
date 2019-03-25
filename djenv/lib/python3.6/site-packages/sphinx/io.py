# -*- coding: utf-8 -*-
"""
    sphinx.io
    ~~~~~~~~~

    Input/Output files

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
import codecs
import re
import warnings

from docutils.core import Publisher
from docutils.io import FileInput, NullOutput
from docutils.parsers.rst import Parser as RSTParser
from docutils.readers import standalone
from docutils.statemachine import StringList, string2lines
from docutils.writers import UnfilteredWriter
from six import text_type, iteritems
from typing import Any, Union  # NOQA

from sphinx.deprecation import RemovedInSphinx30Warning
from sphinx.locale import __
from sphinx.transforms import (
    ApplySourceWorkaround, ExtraTranslatableNodes, CitationReferences,
    DefaultSubstitutions, MoveModuleTargets, HandleCodeBlocks, SortIds,
    AutoNumbering, AutoIndexUpgrader, FilterSystemMessages,
    UnreferencedFootnotesDetector, SphinxSmartQuotes, DoctreeReadEvent, ManpageLink
)
from sphinx.transforms import SphinxTransformer
from sphinx.transforms.compact_bullet_list import RefOnlyBulletListTransform
from sphinx.transforms.i18n import (
    PreserveTranslatableMessages, Locale, RemoveTranslatableInline,
)
from sphinx.transforms.references import SphinxDomains, SubstitutionDefinitionsRemover
from sphinx.util import logging
from sphinx.util.docutils import LoggingReporter
from sphinx.versioning import UIDTransform

if False:
    # For type annotation
    from typing import Any, Dict, List, Tuple, Union  # NOQA
    from docutils import nodes  # NOQA
    from docutils.io import Input  # NOQA
    from docutils.parsers import Parser  # NOQA
    from docutils.transforms import Transform  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

docinfo_re = re.compile(':\\w+:.*?')


logger = logging.getLogger(__name__)


class SphinxBaseReader(standalone.Reader):
    """
    A base class of readers for Sphinx.

    This replaces reporter by Sphinx's on generating document.
    """

    def __init__(self, app, *args, **kwargs):
        # type: (Sphinx, Any, Any) -> None
        self.env = app.env
        standalone.Reader.__init__(self, *args, **kwargs)

    def get_transforms(self):
        # type: () -> List[Transform]
        return standalone.Reader.get_transforms(self) + self.transforms

    def new_document(self):
        # type: () -> nodes.document
        """Creates a new document object which having a special reporter object good
        for logging.
        """
        document = standalone.Reader.new_document(self)

        # substitute transformer
        document.transformer = SphinxTransformer(document)
        document.transformer.set_environment(self.env)

        # substitute reporter
        reporter = document.reporter
        document.reporter = LoggingReporter.from_reporter(reporter)

        return document


class SphinxStandaloneReader(SphinxBaseReader):
    """
    A basic document reader for Sphinx.
    """
    transforms = [ApplySourceWorkaround, ExtraTranslatableNodes, PreserveTranslatableMessages,
                  Locale, CitationReferences, DefaultSubstitutions, MoveModuleTargets,
                  HandleCodeBlocks, AutoNumbering, AutoIndexUpgrader, SortIds,
                  RemoveTranslatableInline, FilterSystemMessages, RefOnlyBulletListTransform,
                  UnreferencedFootnotesDetector, SphinxSmartQuotes, ManpageLink,
                  SphinxDomains, SubstitutionDefinitionsRemover, DoctreeReadEvent,
                  UIDTransform,
                  ]  # type: List[Transform]

    def __init__(self, app, *args, **kwargs):
        # type: (Sphinx, Any, Any) -> None
        self.transforms = self.transforms + app.registry.get_transforms()
        SphinxBaseReader.__init__(self, app, *args, **kwargs)


class SphinxI18nReader(SphinxBaseReader):
    """
    A document reader for i18n.

    This returns the source line number of original text as current source line number
    to let users know where the error happened.
    Because the translated texts are partial and they don't have correct line numbers.
    """

    transforms = [ApplySourceWorkaround, ExtraTranslatableNodes, CitationReferences,
                  DefaultSubstitutions, MoveModuleTargets, HandleCodeBlocks,
                  AutoNumbering, SortIds, RemoveTranslatableInline,
                  FilterSystemMessages, RefOnlyBulletListTransform,
                  UnreferencedFootnotesDetector, SphinxSmartQuotes, ManpageLink,
                  SubstitutionDefinitionsRemover]

    def set_lineno_for_reporter(self, lineno):
        # type: (int) -> None
        """Stores the source line number of original text."""
        warnings.warn('SphinxI18nReader.set_lineno_for_reporter() is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)

    @property
    def line(self):
        # type: () -> int
        warnings.warn('SphinxI18nReader.line is deprecated.',
                      RemovedInSphinx30Warning, stacklevel=2)
        return 0


class SphinxDummyWriter(UnfilteredWriter):
    """Dummy writer module used for generating doctree."""

    supported = ('html',)  # needed to keep "meta" nodes

    def translate(self):
        # type: () -> None
        pass


def SphinxDummySourceClass(source, *args, **kwargs):
    # type: (Any, Any, Any) -> Any
    """Bypass source object as is to cheat Publisher."""
    return source


class SphinxBaseFileInput(FileInput):
    """A base class of SphinxFileInput.

    It supports to replace unknown Unicode characters to '?'. And it also emits
    Sphinx events :event:`source-read` on reading.
    """

    def __init__(self, app, env, *args, **kwds):
        # type: (Sphinx, BuildEnvironment, Any, Any) -> None
        self.app = app
        self.env = env

        # set up error handler
        codecs.register_error('sphinx', self.warn_and_replace)  # type: ignore

        kwds['error_handler'] = 'sphinx'  # py3: handle error on open.
        FileInput.__init__(self, *args, **kwds)

    def decode(self, data):
        # type: (Union[unicode, bytes]) -> unicode
        if isinstance(data, text_type):  # py3: `data` already decoded.
            return data
        return data.decode(self.encoding, 'sphinx')  # py2: decoding

    def read(self):
        # type: () -> unicode
        """Reads the contents from file.

        After reading, it emits Sphinx event ``source-read``.
        """
        data = FileInput.read(self)

        # emit source-read event
        arg = [data]
        self.app.emit('source-read', self.env.docname, arg)
        return arg[0]

    def warn_and_replace(self, error):
        # type: (Any) -> Tuple
        """Custom decoding error handler that warns and replaces."""
        linestart = error.object.rfind(b'\n', 0, error.start)
        lineend = error.object.find(b'\n', error.start)
        if lineend == -1:
            lineend = len(error.object)
        lineno = error.object.count(b'\n', 0, error.start) + 1
        logger.warning(__('undecodable source characters, replacing with "?": %r'),
                       (error.object[linestart + 1:error.start] + b'>>>' +
                        error.object[error.start:error.end] + b'<<<' +
                        error.object[error.end:lineend]),
                       location=(self.env.docname, lineno))
        return (u'?', error.end)


class SphinxFileInput(SphinxBaseFileInput):
    """A basic FileInput for Sphinx."""
    supported = ('*',)  # special source input


class SphinxRSTFileInput(SphinxBaseFileInput):
    """A reST FileInput for Sphinx.

    This FileInput automatically prepends and appends text by :confval:`rst_prolog` and
    :confval:`rst_epilog`.

    .. important::

       This FileInput uses an instance of ``StringList`` as a return value of ``read()``
       method to indicate original source filename and line numbers after prepending and
       appending.
       For that reason, ``sphinx.parsers.RSTParser`` should be used with this to parse
       a content correctly.
    """
    supported = ('restructuredtext',)

    def prepend_prolog(self, text, prolog):
        # type: (StringList, unicode) -> None
        docinfo = self.count_docinfo_lines(text)
        if docinfo:
            # insert a blank line after docinfo
            text.insert(docinfo, '', '<generated>', 0)
            docinfo += 1

        # insert prolog (after docinfo if exists)
        for lineno, line in enumerate(prolog.splitlines()):
            text.insert(docinfo + lineno, line, '<rst_prolog>', lineno)

        text.insert(docinfo + lineno + 1, '', '<generated>', 0)

    def append_epilog(self, text, epilog):
        # type: (StringList, unicode) -> None
        # append a blank line and rst_epilog
        text.append('', '<generated>', 0)
        for lineno, line in enumerate(epilog.splitlines()):
            text.append(line, '<rst_epilog>', lineno)

    def read(self):
        # type: () -> StringList
        inputstring = SphinxBaseFileInput.read(self)
        lines = string2lines(inputstring, convert_whitespace=True)
        content = StringList()
        for lineno, line in enumerate(lines):
            content.append(line, self.source_path, lineno)

        if self.env.config.rst_prolog:
            self.prepend_prolog(content, self.env.config.rst_prolog)
        if self.env.config.rst_epilog:
            self.append_epilog(content, self.env.config.rst_epilog)

        return content

    def count_docinfo_lines(self, content):
        # type: (StringList) -> int
        if len(content) == 0:
            return 0
        else:
            for lineno, line in enumerate(content.data):
                if not docinfo_re.match(line):
                    break
            return lineno


class FiletypeNotFoundError(Exception):
    pass


def get_filetype(source_suffix, filename):
    # type: (Dict[unicode, unicode], unicode) -> unicode
    for suffix, filetype in iteritems(source_suffix):
        if filename.endswith(suffix):
            # If default filetype (None), considered as restructuredtext.
            return filetype or 'restructuredtext'
    else:
        raise FiletypeNotFoundError


def read_doc(app, env, filename):
    # type: (Sphinx, BuildEnvironment, unicode) -> nodes.document
    """Parse a document and convert to doctree."""
    filetype = get_filetype(app.config.source_suffix, filename)
    input_class = app.registry.get_source_input(filetype)
    reader = SphinxStandaloneReader(app)
    source = input_class(app, env, source=None, source_path=filename,
                         encoding=env.config.source_encoding)
    parser = app.registry.create_source_parser(app, filetype)
    if parser.__class__.__name__ == 'CommonMarkParser' and parser.settings_spec == ():
        # a workaround for recommonmark
        #   If recommonmark.AutoStrictify is enabled, the parser invokes reST parser
        #   internally.  But recommonmark-0.4.0 does not provide settings_spec for reST
        #   parser.  As a workaround, this copies settings_spec for RSTParser to the
        #   CommonMarkParser.
        parser.settings_spec = RSTParser.settings_spec

    pub = Publisher(reader=reader,
                    parser=parser,
                    writer=SphinxDummyWriter(),
                    source_class=SphinxDummySourceClass,
                    destination=NullOutput())
    pub.set_components(None, 'restructuredtext', None)
    pub.process_programmatic_settings(None, env.settings, None)
    pub.set_source(source, filename)
    pub.publish()
    return pub.document


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.registry.add_source_input(SphinxFileInput)
    app.registry.add_source_input(SphinxRSTFileInput)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
