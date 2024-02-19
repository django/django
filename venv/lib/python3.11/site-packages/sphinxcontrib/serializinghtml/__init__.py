from __future__ import annotations

import os
import pickle
import types
from os import path
from typing import Any

from sphinx.application import ENV_PICKLE_FILENAME, Sphinx
from sphinx.builders.html import BuildInfo, StandaloneHTMLBuilder
from sphinx.locale import get_translation
from sphinx.util.osutil import SEP, copyfile, ensuredir, os_path

from sphinxcontrib.serializinghtml import jsonimpl

__version__ = '1.1.10'
__version_info__ = (1, 1, 10)

package_dir = path.abspath(path.dirname(__file__))

__ = get_translation(__name__, 'console')


#: the filename for the "last build" file (for serializing builders)
LAST_BUILD_FILENAME = 'last_build'


class SerializingHTMLBuilder(StandaloneHTMLBuilder):
    """
    An abstract builder that serializes the generated HTML.
    """
    #: the serializing implementation to use.  Set this to a module that
    #: implements a `dump`, `load`, `dumps` and `loads` functions
    #: (pickle, simplejson etc.)
    implementation: Any = None
    implementation_dumps_unicode = False
    #: additional arguments for dump()
    additional_dump_args: tuple = ()

    #: the filename for the global context file
    globalcontext_filename: str = ''

    supported_image_types = ['image/svg+xml', 'image/png',
                             'image/gif', 'image/jpeg']

    def init(self) -> None:
        self.build_info = BuildInfo(self.config, self.tags)
        self.imagedir = '_images'
        self.current_docname = ''
        self.theme = None  # type: ignore[assignment] # no theme necessary
        self.templates = None  # no template bridge necessary
        self.init_templates()
        self.init_highlighter()
        self.init_css_files()
        self.init_js_files()
        self.use_index = self.get_builder_config('use_index', 'html')

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        if docname == 'index':
            return ''
        if docname.endswith(SEP + 'index'):
            return docname[:-5]  # up to sep
        return docname + SEP

    def dump_context(self, context: dict, filename: str | os.PathLike[str]) -> None:
        context = context.copy()
        if 'css_files' in context:
            context['css_files'] = [css.filename for css in context['css_files']]
        if 'script_files' in context:
            context['script_files'] = [js.filename for js in context['script_files']]
        if self.implementation_dumps_unicode:
            with open(filename, 'w', encoding='utf-8') as ft:
                self.implementation.dump(context, ft, *self.additional_dump_args)
        else:
            with open(filename, 'wb') as fb:
                self.implementation.dump(context, fb, *self.additional_dump_args)

    def handle_page(self, pagename: str, ctx: dict, templatename: str = 'page.html',
                    outfilename: str | None = None, event_arg: Any = None) -> None:
        ctx['current_page_name'] = pagename
        ctx.setdefault('pathto', lambda p: p)
        self.add_sidebars(pagename, ctx)

        if not outfilename:
            outfilename = path.join(self.outdir,
                                    os_path(pagename) + self.out_suffix)

        # we're not taking the return value here, since no template is
        # actually rendered
        self.app.emit('html-page-context', pagename, templatename, ctx, event_arg)

        # make context object serializable
        for key in list(ctx):
            if isinstance(ctx[key], types.FunctionType):
                del ctx[key]

        ensuredir(path.dirname(outfilename))
        self.dump_context(ctx, outfilename)

        # if there is a source file, copy the source file for the
        # "show source" link
        if ctx.get('sourcename'):
            source_name = path.join(self.outdir, '_sources',
                                    os_path(ctx['sourcename']))
            ensuredir(path.dirname(source_name))
            copyfile(self.env.doc2path(pagename), source_name)

    def handle_finish(self) -> None:
        # dump the global context
        outfilename = path.join(self.outdir, self.globalcontext_filename)
        self.dump_context(self.globalcontext, outfilename)

        # super here to dump the search index
        super().handle_finish()

        # copy the environment file from the doctree dir to the output dir
        # as needed by the web app
        copyfile(path.join(self.doctreedir, ENV_PICKLE_FILENAME),
                 path.join(self.outdir, ENV_PICKLE_FILENAME))

        # touch 'last build' file, used by the web application to determine
        # when to reload its environment and clear the cache
        open(path.join(self.outdir, LAST_BUILD_FILENAME), 'w').close()


class PickleHTMLBuilder(SerializingHTMLBuilder):
    """
    A Builder that dumps the generated HTML into pickle files.
    """
    name = 'pickle'
    epilog = __('You can now process the pickle files in %(outdir)s.')

    implementation = pickle
    implementation_dumps_unicode = False
    additional_dump_args = (pickle.HIGHEST_PROTOCOL,)
    indexer_format = pickle
    indexer_dumps_unicode = False
    out_suffix = '.fpickle'
    globalcontext_filename = 'globalcontext.pickle'
    searchindex_filename = 'searchindex.pickle'


class JSONHTMLBuilder(SerializingHTMLBuilder):
    """
    A builder that dumps the generated HTML into JSON files.
    """
    name = 'json'
    epilog = __('You can now process the JSON files in %(outdir)s.')

    implementation = jsonimpl
    implementation_dumps_unicode = True
    indexer_format = jsonimpl
    indexer_dumps_unicode = True
    out_suffix = '.fjson'
    globalcontext_filename = 'globalcontext.json'
    searchindex_filename = 'searchindex.json'


def setup(app: Sphinx) -> dict[str, Any]:
    app.require_sphinx('5.0')
    app.setup_extension('sphinx.builders.html')
    app.add_builder(JSONHTMLBuilder)
    app.add_builder(PickleHTMLBuilder)
    app.add_message_catalog(__name__, path.join(package_dir, 'locales'))

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
