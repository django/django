"""Build Apple help books."""

import plistlib
import shlex
import subprocess
from os import environ
from os import path
from subprocess import CalledProcessError, PIPE, STDOUT
from typing import Any

import sphinx
from sphinx.application import Sphinx
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.errors import SphinxError
from sphinx.locale import get_translation
from sphinx.util import logging
from sphinx.util.fileutil import copy_asset, copy_asset_file
from sphinx.util.matching import Matcher
from sphinx.util.osutil import ensuredir, make_filename

if sphinx.version_info[:2] >= (6, 1):
    from sphinx.util.display import SkipProgressMessage, progress_message
else:
    from sphinx.util import (  # type: ignore[attr-defined,no-redef]
        SkipProgressMessage, progress_message
    )

__version__ = '1.0.8'
__version_info__ = (1, 0, 8)

package_dir = path.abspath(path.dirname(__file__))
template_dir = path.join(package_dir, 'templates')

__ = get_translation(__name__, 'console')
logger = logging.getLogger(__name__)


class AppleHelpIndexerFailed(SphinxError):
    category = __('Help indexer failed')


class AppleHelpCodeSigningFailed(SphinxError):
    category = __('Code signing failed')


class AppleHelpBuilder(StandaloneHTMLBuilder):
    """
    Builder that outputs an Apple help book.  Requires Mac OS X as it relies
    on the ``hiutil`` command line tool.
    """
    name = 'applehelp'
    epilog = __('The help book is in %(outdir)s.\n'
                'Note that won\'t be able to view it unless you put it in '
                '~/Library/Documentation/Help or install it in your application '
                'bundle.')

    # don't copy the reST source
    copysource = False
    supported_image_types = ['image/png', 'image/gif', 'image/jpeg',
                             'image/tiff', 'image/jp2', 'image/svg+xml']

    # don't add links
    add_permalinks = False

    # this is an embedded HTML format
    embedded = True

    # don't generate the search index or include the search page
    search = False

    def init(self) -> None:
        super().init()
        # the output files for HTML help must be .html only
        self.out_suffix = '.html'
        self.link_suffix = '.html'

        if self.config.applehelp_bundle_id is None:
            raise SphinxError(__('You must set applehelp_bundle_id before '
                                 'building Apple Help output'))

        self.bundle_path = path.join(self.outdir, self.config.applehelp_bundle_name + '.help')
        self.outdir = path.join(  # type: ignore[assignment]
            self.bundle_path,
            'Contents',
            'Resources',
            self.config.applehelp_locale + '.lproj',
        )

    def handle_finish(self) -> None:
        super().handle_finish()

        self.finish_tasks.add_task(self.copy_localized_files)
        self.finish_tasks.add_task(self.build_helpbook)

    @progress_message(__('copying localized files'))
    def copy_localized_files(self) -> None:
        source_dir = path.join(self.confdir, self.config.applehelp_locale + '.lproj')  # type: ignore  # NOQA
        target_dir = self.outdir

        if path.isdir(source_dir):
            excluded = Matcher(self.config.exclude_patterns + ['**/.*'])
            copy_asset(source_dir, target_dir, excluded,
                       context=self.globalcontext, renderer=self.templates)

    def build_helpbook(self) -> None:
        contents_dir = path.join(self.bundle_path, 'Contents')
        resources_dir = path.join(contents_dir, 'Resources')
        language_dir = path.join(resources_dir,
                                 self.config.applehelp_locale + '.lproj')
        ensuredir(language_dir)

        self.build_info_plist(contents_dir)
        self.copy_applehelp_icon(resources_dir)
        self.build_access_page(language_dir)
        self.build_helpindex(language_dir)

        if self.config.applehelp_codesign_identity:
            self.do_codesign()

    @progress_message(__('writing Info.plist'))
    def build_info_plist(self, contents_dir: str) -> None:
        """Construct the Info.plist file."""
        info_plist = {
            'CFBundleDevelopmentRegion': self.config.applehelp_dev_region,
            'CFBundleIdentifier': self.config.applehelp_bundle_id,
            'CFBundleInfoDictionaryVersion': '6.0',
            'CFBundlePackageType': 'BNDL',
            'CFBundleShortVersionString': self.config.release,
            'CFBundleSignature': 'hbwr',
            'CFBundleVersion': self.config.applehelp_bundle_version,
            'HPDBookAccessPath': '_access.html',
            'HPDBookIndexPath': 'search.helpindex',
            'HPDBookTitle': self.config.applehelp_title,
            'HPDBookType': '3',
            'HPDBookUsesExternalViewer': False,
        }

        if self.config.applehelp_icon is not None:
            info_plist['HPDBookIconPath'] = path.basename(self.config.applehelp_icon)

        if self.config.applehelp_kb_url is not None:
            info_plist['HPDBookKBProduct'] = self.config.applehelp_kb_product
            info_plist['HPDBookKBURL'] = self.config.applehelp_kb_url

        if self.config.applehelp_remote_url is not None:
            info_plist['HPDBookRemoteURL'] = self.config.applehelp_remote_url

        with open(path.join(contents_dir, 'Info.plist'), 'wb') as f:
            plistlib.dump(info_plist, f)

    def copy_applehelp_icon(self, resources_dir: str) -> None:
        """Copy the icon, if one is supplied."""
        if self.config.applehelp_icon:

            try:
                with progress_message(__('copying icon... ')):
                    applehelp_icon = path.join(self.srcdir, self.config.applehelp_icon)
                    copy_asset_file(applehelp_icon, resources_dir)
            except Exception as err:
                logger.warning(__('cannot copy icon file %r: %s'), applehelp_icon, err)

    @progress_message(__('building access page'))
    def build_access_page(self, language_dir: str) -> None:
        """Build the access page."""
        context = {
            'toc': self.config.master_doc + self.out_suffix,
            'title': self.config.applehelp_title,
        }
        copy_asset_file(path.join(template_dir, '_access.html_t'), language_dir, context)

    @progress_message(__('generating help index'))
    def build_helpindex(self, language_dir: str) -> None:
        """Generate the help index."""
        args = [
            self.config.applehelp_indexer_path,
            '-Cf',
            path.join(language_dir, 'search.helpindex'),
            language_dir
        ]

        if self.config.applehelp_index_anchors is not None:
            args.append('-a')

        if self.config.applehelp_min_term_length is not None:
            args += ['-m', '%s' % self.config.applehelp_min_term_length]

        if self.config.applehelp_stopwords is not None:
            args += ['-s', self.config.applehelp_stopwords]

        if self.config.applehelp_locale is not None:
            args += ['-l', self.config.applehelp_locale]

        if self.config.applehelp_disable_external_tools:
            raise SkipProgressMessage(__('you will need to index this help book with:\n  %s'),
                                      ' '.join([shlex.quote(arg) for arg in args]))
        else:
            try:
                subprocess.run(args, stdout=PIPE, stderr=STDOUT, check=True)
            except OSError:
                raise AppleHelpIndexerFailed(__('Command not found: %s') % args[0])
            except CalledProcessError as exc:
                raise AppleHelpIndexerFailed(exc.stdout)

    @progress_message(__('signing help book'))
    def do_codesign(self) -> None:
        """If we've been asked to, sign the bundle."""
        args = [
            self.config.applehelp_codesign_path,
            '-s', self.config.applehelp_codesign_identity,
            '-f'
        ]

        args += self.config.applehelp_codesign_flags

        args.append(self.bundle_path)

        if self.config.applehelp_disable_external_tools:
            raise SkipProgressMessage(__('you will need to sign this help book with:\n  %s'),
                                      ' '.join([shlex.quote(arg) for arg in args]))
        else:
            try:
                subprocess.run(args, stdout=PIPE, stderr=STDOUT, check=True)
            except OSError:
                raise AppleHelpCodeSigningFailed(__('Command not found: %s') % args[0])
            except CalledProcessError as exc:
                raise AppleHelpCodeSigningFailed(exc.stdout)


def setup(app: Sphinx) -> dict[str, Any]:
    app.require_sphinx('5.0')
    app.setup_extension('sphinx.builders.html')
    app.add_builder(AppleHelpBuilder)
    app.add_message_catalog(__name__, path.join(package_dir, 'locales'))

    app.add_config_value('applehelp_bundle_name',
                         lambda self: make_filename(self.project), 'applehelp')
    app.add_config_value('applehelp_bundle_id', None, 'applehelp', [str])
    app.add_config_value('applehelp_dev_region', 'en-us', 'applehelp')
    app.add_config_value('applehelp_bundle_version', '1', 'applehelp')
    app.add_config_value('applehelp_icon', None, 'applehelp', [str])
    app.add_config_value('applehelp_kb_product',
                         lambda self: '%s-%s' % (make_filename(self.project), self.release),
                         'applehelp')
    app.add_config_value('applehelp_kb_url', None, 'applehelp', [str])
    app.add_config_value('applehelp_remote_url', None, 'applehelp', [str])
    app.add_config_value('applehelp_index_anchors', False, 'applehelp', [str])
    app.add_config_value('applehelp_min_term_length', None, 'applehelp', [str])
    app.add_config_value('applehelp_stopwords',
                         lambda self: self.language or 'en', 'applehelp')
    app.add_config_value('applehelp_locale', lambda self: self.language or 'en', 'applehelp')
    app.add_config_value('applehelp_title', lambda self: self.project + ' Help', 'applehelp')
    app.add_config_value('applehelp_codesign_identity',
                         lambda self: environ.get('CODE_SIGN_IDENTITY', None),
                         'applehelp')
    app.add_config_value('applehelp_codesign_flags',
                         lambda self: shlex.split(environ.get('OTHER_CODE_SIGN_FLAGS', '')),
                         'applehelp')
    app.add_config_value('applehelp_indexer_path', '/usr/bin/hiutil', 'applehelp')
    app.add_config_value('applehelp_codesign_path', '/usr/bin/codesign', 'applehelp')
    app.add_config_value('applehelp_disable_external_tools', False, 'applehelp')

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
