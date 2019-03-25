# -*- coding: utf-8 -*-
"""
    sphinx.builders
    ~~~~~~~~~~~~~~~

    Builder superclass for all builders.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import time
import warnings
from os import path

from docutils import nodes
from six.moves import cPickle as pickle

from sphinx.deprecation import RemovedInSphinx20Warning
from sphinx.environment import CONFIG_OK, CONFIG_CHANGED_REASON
from sphinx.environment.adapters.asset import ImageAdapter
from sphinx.errors import SphinxError
from sphinx.io import read_doc
from sphinx.locale import __
from sphinx.util import i18n, import_object, logging, rst, status_iterator
from sphinx.util.build_phase import BuildPhase
from sphinx.util.console import bold  # type: ignore
from sphinx.util.docutils import sphinx_domains
from sphinx.util.i18n import find_catalog
from sphinx.util.matching import Matcher
from sphinx.util.osutil import SEP, ensuredir, relative_uri, relpath
from sphinx.util.parallel import ParallelTasks, SerialTasks, make_chunks, \
    parallel_available

# side effect: registers roles and directives
from sphinx import roles       # noqa
from sphinx import directives  # noqa

try:
    import multiprocessing
except ImportError:
    multiprocessing = None

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Iterable, List, Sequence, Set, Tuple, Union  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.config import Config  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA
    from sphinx.util.i18n import CatalogInfo  # NOQA
    from sphinx.util.tags import Tags  # NOQA


logger = logging.getLogger(__name__)


class Builder(object):
    """
    Builds target formats from the reST sources.
    """

    #: The builder's name, for the -b command line option.
    name = ''  # type: unicode
    #: The builder's output format, or '' if no document output is produced.
    format = ''  # type: unicode
    #: The message emitted upon successful build completion. This can be a
    #: printf-style template string with the following keys: ``outdir``,
    #: ``project``
    epilog = ''  # type: unicode

    #: default translator class for the builder.  This can be overridden by
    #: :py:meth:`app.set_translator()`.
    default_translator_class = None  # type: nodes.NodeVisitor
    # doctree versioning method
    versioning_method = 'none'  # type: unicode
    versioning_compare = False
    # allow parallel write_doc() calls
    allow_parallel = False
    # support translation
    use_message_catalog = True

    #: The list of MIME types of image formats supported by the builder.
    #: Image files are searched in the order in which they appear here.
    supported_image_types = []  # type: List[unicode]
    #: The builder supports remote images or not.
    supported_remote_images = False
    #: The builder supports data URIs or not.
    supported_data_uri_images = False

    def __init__(self, app):
        # type: (Sphinx) -> None
        self.srcdir = app.srcdir
        self.confdir = app.confdir
        self.outdir = app.outdir
        self.doctreedir = app.doctreedir
        ensuredir(self.doctreedir)

        self.app = app              # type: Sphinx
        self.env = None             # type: BuildEnvironment
        self.warn = app.warn        # type: Callable
        self.info = app.info        # type: Callable
        self.config = app.config    # type: Config
        self.tags = app.tags        # type: Tags
        self.tags.add(self.format)
        self.tags.add(self.name)
        self.tags.add("format_%s" % self.format)
        self.tags.add("builder_%s" % self.name)

        # images that need to be copied over (source -> dest)
        self.images = {}  # type: Dict[unicode, unicode]
        # basename of images directory
        self.imagedir = ""
        # relative path to image directory from current docname (used at writing docs)
        self.imgpath = ""  # type: unicode

        # these get set later
        self.parallel_ok = False
        self.finish_tasks = None  # type: Any

    def set_environment(self, env):
        # type: (BuildEnvironment) -> None
        """Store BuildEnvironment object."""
        self.env = env
        self.env.set_versioning_method(self.versioning_method,
                                       self.versioning_compare)

    def get_translator_class(self, *args):
        # type: (Any) -> nodes.NodeVisitor
        """Return a class of translator."""
        return self.app.registry.get_translator_class(self)

    def create_translator(self, *args):
        # type: (Any) -> nodes.NodeVisitor
        """Return an instance of translator.

        This method returns an instance of ``default_translator_class`` by default.
        Users can replace the translator class with ``app.set_translator()`` API.
        """
        return self.app.registry.create_translator(self, *args)

    @property
    def translator_class(self):
        # type: () -> Callable[[Any], nodes.NodeVisitor]
        """Return a class of translator.

        .. deprecated:: 1.6
        """
        translator_class = self.app.registry.get_translator_class(self)
        if translator_class is None and self.default_translator_class is None:
            warnings.warn('builder.translator_class() is now deprecated. '
                          'Please use builder.create_translator() and '
                          'builder.default_translator_class instead.',
                          RemovedInSphinx20Warning, stacklevel=2)
            return None
        return self.create_translator

    # helper methods
    def init(self):
        # type: () -> None
        """Load necessary templates and perform initialization.  The default
        implementation does nothing.
        """
        pass

    def create_template_bridge(self):
        # type: () -> None
        """Return the template bridge configured."""
        if self.config.template_bridge:
            self.templates = import_object(self.config.template_bridge,
                                           'template_bridge setting')()
        else:
            from sphinx.jinja2glue import BuiltinTemplateLoader
            self.templates = BuiltinTemplateLoader()

    def get_target_uri(self, docname, typ=None):
        # type: (unicode, unicode) -> unicode
        """Return the target URI for a document name.

        *typ* can be used to qualify the link characteristic for individual
        builders.
        """
        raise NotImplementedError

    def get_relative_uri(self, from_, to, typ=None):
        # type: (unicode, unicode, unicode) -> unicode
        """Return a relative URI between two source filenames.

        May raise environment.NoUri if there's no way to return a sensible URI.
        """
        return relative_uri(self.get_target_uri(from_),
                            self.get_target_uri(to, typ))

    def get_outdated_docs(self):
        # type: () -> Union[unicode, Iterable[unicode]]
        """Return an iterable of output files that are outdated, or a string
        describing what an update build will build.

        If the builder does not output individual files corresponding to
        source files, return a string here.  If it does, return an iterable
        of those files that need to be written.
        """
        raise NotImplementedError

    def get_asset_paths(self):
        # type: () -> List[unicode]
        """Return list of paths for assets (ex. templates, CSS, etc.)."""
        return []

    def post_process_images(self, doctree):
        # type: (nodes.Node) -> None
        """Pick the best candidate for all image URIs."""
        images = ImageAdapter(self.env)
        for node in doctree.traverse(nodes.image):
            if '?' in node['candidates']:
                # don't rewrite nonlocal image URIs
                continue
            if '*' not in node['candidates']:
                for imgtype in self.supported_image_types:
                    candidate = node['candidates'].get(imgtype, None)
                    if candidate:
                        break
                else:
                    mimetypes = sorted(node['candidates'])
                    image_uri = images.get_original_image_uri(node['uri'])
                    if mimetypes:
                        logger.warning(__('a suitable image for %s builder not found: '
                                          '%s (%s)'),
                                       self.name, mimetypes, image_uri, location=node)
                    else:
                        logger.warning(__('a suitable image for %s builder not found: %s'),
                                       self.name, image_uri, location=node)
                    continue
                node['uri'] = candidate
            else:
                candidate = node['uri']
            if candidate not in self.env.images:
                # non-existing URI; let it alone
                continue
            self.images[candidate] = self.env.images[candidate][1]

    # compile po methods

    def compile_catalogs(self, catalogs, message):
        # type: (Set[CatalogInfo], unicode) -> None
        if not self.config.gettext_auto_build:
            return

        def cat2relpath(cat):
            # type: (CatalogInfo) -> unicode
            return relpath(cat.mo_path, self.env.srcdir).replace(path.sep, SEP)

        logger.info(bold(__('building [mo]: ')) + message)
        for catalog in status_iterator(catalogs, __('writing output... '), "darkgreen",
                                       len(catalogs), self.app.verbosity,
                                       stringify_func=cat2relpath):
            catalog.write_mo(self.config.language)

    def compile_all_catalogs(self):
        # type: () -> None
        catalogs = i18n.find_catalog_source_files(
            [path.join(self.srcdir, x) for x in self.config.locale_dirs],
            self.config.language,
            charset=self.config.source_encoding,
            force_all=True,
            excluded=Matcher(['**/.?**']))
        message = __('all of %d po files') % len(catalogs)
        self.compile_catalogs(catalogs, message)

    def compile_specific_catalogs(self, specified_files):
        # type: (List[unicode]) -> None
        def to_domain(fpath):
            # type: (unicode) -> unicode
            docname = self.env.path2doc(path.abspath(fpath))
            if docname:
                return find_catalog(docname, self.config.gettext_compact)
            else:
                return None

        specified_domains = set(map(to_domain, specified_files))
        specified_domains.discard(None)
        catalogs = i18n.find_catalog_source_files(
            [path.join(self.srcdir, x) for x in self.config.locale_dirs],
            self.config.language,
            domains=list(specified_domains),
            charset=self.config.source_encoding,
            excluded=Matcher(['**/.?**']))
        message = __('targets for %d po files that are specified') % len(catalogs)
        self.compile_catalogs(catalogs, message)

    def compile_update_catalogs(self):
        # type: () -> None
        catalogs = i18n.find_catalog_source_files(
            [path.join(self.srcdir, x) for x in self.config.locale_dirs],
            self.config.language,
            charset=self.config.source_encoding,
            excluded=Matcher(['**/.?**']))
        message = __('targets for %d po files that are out of date') % len(catalogs)
        self.compile_catalogs(catalogs, message)

    # build methods

    def build_all(self):
        # type: () -> None
        """Build all source files."""
        self.build(None, summary=__('all source files'), method='all')

    def build_specific(self, filenames):
        # type: (List[unicode]) -> None
        """Only rebuild as much as needed for changes in the *filenames*."""
        # bring the filenames to the canonical format, that is,
        # relative to the source directory and without source_suffix.
        dirlen = len(self.srcdir) + 1
        to_write = []
        suffixes = None  # type: Tuple[unicode]
        suffixes = tuple(self.config.source_suffix)  # type: ignore
        for filename in filenames:
            filename = path.normpath(path.abspath(filename))
            if not filename.startswith(self.srcdir):
                logger.warning(__('file %r given on command line is not under the '
                                  'source directory, ignoring'), filename)
                continue
            if not (path.isfile(filename) or
                    any(path.isfile(filename + suffix) for suffix in suffixes)):
                logger.warning(__('file %r given on command line does not exist, '
                                  'ignoring'), filename)
                continue
            filename = filename[dirlen:]
            for suffix in suffixes:
                if filename.endswith(suffix):
                    filename = filename[:-len(suffix)]
                    break
            filename = filename.replace(path.sep, SEP)
            to_write.append(filename)
        self.build(to_write, method='specific',
                   summary=__('%d source files given on command line') % len(to_write))

    def build_update(self):
        # type: () -> None
        """Only rebuild what was changed or added since last build."""
        to_build = self.get_outdated_docs()
        if isinstance(to_build, str):
            self.build(['__all__'], to_build)
        else:
            to_build = list(to_build)
            self.build(to_build,
                       summary=__('targets for %d source files that are out of date') %
                       len(to_build))

    def build(self, docnames, summary=None, method='update'):
        # type: (Iterable[unicode], unicode, unicode) -> None
        """Main build method.

        First updates the environment, and then calls :meth:`write`.
        """
        if summary:
            logger.info(bold(__('building [%s]') % self.name) + ': ' + summary)

        # while reading, collect all warnings from docutils
        with logging.pending_warnings():
            updated_docnames = set(self.read())

        doccount = len(updated_docnames)
        logger.info(bold(__('looking for now-outdated files... ')), nonl=1)
        for docname in self.env.check_dependents(self.app, updated_docnames):
            updated_docnames.add(docname)
        outdated = len(updated_docnames) - doccount
        if outdated:
            logger.info(__('%d found'), outdated)
        else:
            logger.info(__('none found'))

        if updated_docnames:
            # save the environment
            from sphinx.application import ENV_PICKLE_FILENAME
            logger.info(bold(__('pickling environment... ')), nonl=True)
            with open(path.join(self.doctreedir, ENV_PICKLE_FILENAME), 'wb') as f:
                pickle.dump(self.env, f, pickle.HIGHEST_PROTOCOL)
            logger.info(__('done'))

            # global actions
            self.app.phase = BuildPhase.CONSISTENCY_CHECK
            logger.info(bold(__('checking consistency... ')), nonl=True)
            self.env.check_consistency()
            logger.info(__('done'))
        else:
            if method == 'update' and not docnames:
                logger.info(bold(__('no targets are out of date.')))
                return

        self.app.phase = BuildPhase.RESOLVING

        # filter "docnames" (list of outdated files) by the updated
        # found_docs of the environment; this will remove docs that
        # have since been removed
        if docnames and docnames != ['__all__']:
            docnames = set(docnames) & self.env.found_docs

        # determine if we can write in parallel
        if parallel_available and self.app.parallel > 1 and self.allow_parallel:
            self.parallel_ok = self.app.is_parallel_allowed('write')
        else:
            self.parallel_ok = False

        #  create a task executor to use for misc. "finish-up" tasks
        # if self.parallel_ok:
        #     self.finish_tasks = ParallelTasks(self.app.parallel)
        # else:
        # for now, just execute them serially
        self.finish_tasks = SerialTasks()

        # write all "normal" documents (or everything for some builders)
        self.write(docnames, list(updated_docnames), method)

        # finish (write static files etc.)
        self.finish()

        # wait for all tasks
        self.finish_tasks.join()

    def read(self):
        # type: () -> List[unicode]
        """(Re-)read all files new or changed since last update.

        Store all environment docnames in the canonical format (ie using SEP as
        a separator in place of os.path.sep).
        """
        logger.info(bold('updating environment: '), nonl=True)

        self.env.find_files(self.config, self)
        updated = (self.env.config_status != CONFIG_OK)
        added, changed, removed = self.env.get_outdated_files(updated)

        # allow user intervention as well
        for docs in self.app.emit('env-get-outdated', self, added, changed, removed):
            changed.update(set(docs) & self.env.found_docs)

        # if files were added or removed, all documents with globbed toctrees
        # must be reread
        if added or removed:
            # ... but not those that already were removed
            changed.update(self.env.glob_toctrees & self.env.found_docs)

        if changed:
            reason = CONFIG_CHANGED_REASON.get(self.env.config_status, '')
            logger.info('[%s] ', reason, nonl=True)
        logger.info('%s added, %s changed, %s removed',
                    len(added), len(changed), len(removed))

        # clear all files no longer present
        for docname in removed:
            self.app.emit('env-purge-doc', self.env, docname)
            self.env.clear_doc(docname)

        # read all new and changed files
        docnames = sorted(added | changed)
        # allow changing and reordering the list of docs to read
        self.app.emit('env-before-read-docs', self.env, docnames)

        # check if we should do parallel or serial read
        if parallel_available and len(docnames) > 5 and self.app.parallel > 1:
            par_ok = self.app.is_parallel_allowed('read')
        else:
            par_ok = False

        if par_ok:
            self._read_parallel(docnames, nproc=self.app.parallel)
        else:
            self._read_serial(docnames)

        if self.config.master_doc not in self.env.all_docs:
            raise SphinxError('master file %s not found' %
                              self.env.doc2path(self.config.master_doc))

        for retval in self.app.emit('env-updated', self.env):
            if retval is not None:
                docnames.extend(retval)

        # workaround: marked as okay to call builder.read() twice in same process
        self.env.config_status = CONFIG_OK

        return sorted(docnames)

    def _read_serial(self, docnames):
        # type: (List[unicode]) -> None
        for docname in status_iterator(docnames, 'reading sources... ', "purple",
                                       len(docnames), self.app.verbosity):
            # remove all inventory entries for that file
            self.app.emit('env-purge-doc', self.env, docname)
            self.env.clear_doc(docname)
            self.read_doc(docname)

    def _read_parallel(self, docnames, nproc):
        # type: (List[unicode], int) -> None
        # clear all outdated docs at once
        for docname in docnames:
            self.app.emit('env-purge-doc', self.env, docname)
            self.env.clear_doc(docname)

        def read_process(docs):
            # type: (List[unicode]) -> bytes
            self.env.app = self.app
            for docname in docs:
                self.read_doc(docname)
            # allow pickling self to send it back
            return pickle.dumps(self.env, pickle.HIGHEST_PROTOCOL)

        def merge(docs, otherenv):
            # type: (List[unicode], bytes) -> None
            env = pickle.loads(otherenv)
            self.env.merge_info_from(docs, env, self.app)

        tasks = ParallelTasks(nproc)
        chunks = make_chunks(docnames, nproc)

        for chunk in status_iterator(chunks, 'reading sources... ', "purple",
                                     len(chunks), self.app.verbosity):
            tasks.add_task(read_process, chunk, merge)

        # make sure all threads have finished
        logger.info(bold('waiting for workers...'))
        tasks.join()

    def read_doc(self, docname):
        # type: (unicode) -> None
        """Parse a file and add/update inventory entries for the doctree."""
        self.env.prepare_settings(docname)

        # Add confdir/docutils.conf to dependencies list if exists
        docutilsconf = path.join(self.confdir, 'docutils.conf')
        if path.isfile(docutilsconf):
            self.env.note_dependency(docutilsconf)

        with sphinx_domains(self.env), rst.default_role(docname, self.config.default_role):
            doctree = read_doc(self.app, self.env, self.env.doc2path(docname))

        # store time of reading, for outdated files detection
        # (Some filesystems have coarse timestamp resolution;
        # therefore time.time() can be older than filesystem's timestamp.
        # For example, FAT32 has 2sec timestamp resolution.)
        self.env.all_docs[docname] = max(time.time(),
                                         path.getmtime(self.env.doc2path(docname)))

        # cleanup
        self.env.temp_data.clear()
        self.env.ref_context.clear()

        self.write_doctree(docname, doctree)

    def write_doctree(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        """Write the doctree to a file."""
        # make it picklable
        doctree.reporter = None
        doctree.transformer = None
        doctree.settings.warning_stream = None
        doctree.settings.env = None
        doctree.settings.record_dependencies = None

        doctree_filename = self.env.doc2path(docname, self.env.doctreedir, '.doctree')
        ensuredir(path.dirname(doctree_filename))
        with open(doctree_filename, 'wb') as f:
            pickle.dump(doctree, f, pickle.HIGHEST_PROTOCOL)

    def write(self, build_docnames, updated_docnames, method='update'):
        # type: (Iterable[unicode], Sequence[unicode], unicode) -> None
        if build_docnames is None or build_docnames == ['__all__']:
            # build_all
            build_docnames = self.env.found_docs
        if method == 'update':
            # build updated ones as well
            docnames = set(build_docnames) | set(updated_docnames)
        else:
            docnames = set(build_docnames)
        logger.debug(__('docnames to write: %s'), ', '.join(sorted(docnames)))

        # add all toctree-containing files that may have changed
        for docname in list(docnames):
            for tocdocname in self.env.files_to_rebuild.get(docname, set()):
                if tocdocname in self.env.found_docs:
                    docnames.add(tocdocname)
        docnames.add(self.config.master_doc)

        logger.info(bold(__('preparing documents... ')), nonl=True)
        self.prepare_writing(docnames)
        logger.info(__('done'))

        if self.parallel_ok:
            # number of subprocesses is parallel-1 because the main process
            # is busy loading doctrees and doing write_doc_serialized()
            self._write_parallel(sorted(docnames),
                                 nproc=self.app.parallel - 1)
        else:
            self._write_serial(sorted(docnames))

    def _write_serial(self, docnames):
        # type: (Sequence[unicode]) -> None
        with logging.pending_warnings():
            for docname in status_iterator(docnames, __('writing output... '), "darkgreen",
                                           len(docnames), self.app.verbosity):
                self.app.phase = BuildPhase.RESOLVING
                doctree = self.env.get_and_resolve_doctree(docname, self)
                self.app.phase = BuildPhase.WRITING
                self.write_doc_serialized(docname, doctree)
                self.write_doc(docname, doctree)

    def _write_parallel(self, docnames, nproc):
        # type: (Sequence[unicode], int) -> None
        def write_process(docs):
            # type: (List[Tuple[unicode, nodes.Node]]) -> None
            self.app.phase = BuildPhase.WRITING
            for docname, doctree in docs:
                self.write_doc(docname, doctree)

        # warm up caches/compile templates using the first document
        firstname, docnames = docnames[0], docnames[1:]
        self.app.phase = BuildPhase.RESOLVING
        doctree = self.env.get_and_resolve_doctree(firstname, self)
        self.app.phase = BuildPhase.WRITING
        self.write_doc_serialized(firstname, doctree)
        self.write_doc(firstname, doctree)

        tasks = ParallelTasks(nproc)
        chunks = make_chunks(docnames, nproc)

        self.app.phase = BuildPhase.RESOLVING
        for chunk in status_iterator(chunks, __('writing output... '), "darkgreen",
                                     len(chunks), self.app.verbosity):
            arg = []
            for i, docname in enumerate(chunk):
                doctree = self.env.get_and_resolve_doctree(docname, self)
                self.write_doc_serialized(docname, doctree)
                arg.append((docname, doctree))
            tasks.add_task(write_process, arg)

        # make sure all threads have finished
        logger.info(bold(__('waiting for workers...')))
        tasks.join()

    def prepare_writing(self, docnames):
        # type: (Set[unicode]) -> None
        """A place where you can add logic before :meth:`write_doc` is run"""
        raise NotImplementedError

    def write_doc(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        """Where you actually write something to the filesystem."""
        raise NotImplementedError

    def write_doc_serialized(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        """Handle parts of write_doc that must be called in the main process
        if parallel build is active.
        """
        pass

    def finish(self):
        # type: () -> None
        """Finish the building process.

        The default implementation does nothing.
        """
        pass

    def cleanup(self):
        # type: () -> None
        """Cleanup any resources.

        The default implementation does nothing.
        """
        pass

    def get_builder_config(self, option, default):
        # type: (unicode, unicode) -> Any
        """Return a builder specific option.

        This method allows customization of common builder settings by
        inserting the name of the current builder in the option key.
        If the key does not exist, use default as builder name.
        """
        # At the moment, only XXX_use_index is looked up this way.
        # Every new builder variant must be registered in Config.config_values.
        try:
            optname = '%s_%s' % (self.name, option)
            return getattr(self.config, optname)
        except AttributeError:
            optname = '%s_%s' % (default, option)
            return getattr(self.config, optname)
