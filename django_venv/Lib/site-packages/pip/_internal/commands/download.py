from __future__ import absolute_import

import logging
import os

from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import RequirementCommand
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.legacy_resolve import Resolver
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req import RequirementSet
from pip._internal.req.req_tracker import RequirementTracker
from pip._internal.utils.filesystem import check_path_owner
from pip._internal.utils.misc import ensure_dir, normalize_path
from pip._internal.utils.temp_dir import TempDirectory

logger = logging.getLogger(__name__)


class DownloadCommand(RequirementCommand):
    """
    Download packages from:

    - PyPI (and other indexes) using requirement specifiers.
    - VCS project urls.
    - Local project directories.
    - Local or remote source archives.

    pip also supports downloading from "requirements files", which provide
    an easy way to specify a whole environment to be downloaded.
    """
    name = 'download'

    usage = """
      %prog [options] <requirement specifier> [package-index-options] ...
      %prog [options] -r <requirements file> [package-index-options] ...
      %prog [options] <vcs project url> ...
      %prog [options] <local project path> ...
      %prog [options] <archive url/path> ..."""

    summary = 'Download packages.'

    def __init__(self, *args, **kw):
        super(DownloadCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts

        cmd_opts.add_option(cmdoptions.constraints())
        cmd_opts.add_option(cmdoptions.requirements())
        cmd_opts.add_option(cmdoptions.build_dir())
        cmd_opts.add_option(cmdoptions.no_deps())
        cmd_opts.add_option(cmdoptions.global_options())
        cmd_opts.add_option(cmdoptions.no_binary())
        cmd_opts.add_option(cmdoptions.only_binary())
        cmd_opts.add_option(cmdoptions.prefer_binary())
        cmd_opts.add_option(cmdoptions.src())
        cmd_opts.add_option(cmdoptions.pre())
        cmd_opts.add_option(cmdoptions.no_clean())
        cmd_opts.add_option(cmdoptions.require_hashes())
        cmd_opts.add_option(cmdoptions.progress_bar())
        cmd_opts.add_option(cmdoptions.no_build_isolation())
        cmd_opts.add_option(cmdoptions.use_pep517())
        cmd_opts.add_option(cmdoptions.no_use_pep517())

        cmd_opts.add_option(
            '-d', '--dest', '--destination-dir', '--destination-directory',
            dest='download_dir',
            metavar='dir',
            default=os.curdir,
            help=("Download packages into <dir>."),
        )

        cmdoptions.add_target_python_options(cmd_opts)

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, cmd_opts)

    def run(self, options, args):
        options.ignore_installed = True
        # editable doesn't really make sense for `pip download`, but the bowels
        # of the RequirementSet code require that property.
        options.editables = []

        cmdoptions.check_dist_restriction(options)

        options.src_dir = os.path.abspath(options.src_dir)
        options.download_dir = normalize_path(options.download_dir)

        ensure_dir(options.download_dir)

        with self._build_session(options) as session:
            target_python = make_target_python(options)
            finder = self._build_package_finder(
                options=options,
                session=session,
                target_python=target_python,
            )
            build_delete = (not (options.no_clean or options.build_dir))
            if options.cache_dir and not check_path_owner(options.cache_dir):
                logger.warning(
                    "The directory '%s' or its parent directory is not owned "
                    "by the current user and caching wheels has been "
                    "disabled. check the permissions and owner of that "
                    "directory. If executing pip with sudo, you may want "
                    "sudo's -H flag.",
                    options.cache_dir,
                )
                options.cache_dir = None

            with RequirementTracker() as req_tracker, TempDirectory(
                options.build_dir, delete=build_delete, kind="download"
            ) as directory:

                requirement_set = RequirementSet(
                    require_hashes=options.require_hashes,
                )
                self.populate_requirement_set(
                    requirement_set,
                    args,
                    options,
                    finder,
                    session,
                    self.name,
                    None
                )

                preparer = RequirementPreparer(
                    build_dir=directory.path,
                    src_dir=options.src_dir,
                    download_dir=options.download_dir,
                    wheel_download_dir=None,
                    progress_bar=options.progress_bar,
                    build_isolation=options.build_isolation,
                    req_tracker=req_tracker,
                )

                resolver = Resolver(
                    preparer=preparer,
                    finder=finder,
                    session=session,
                    wheel_cache=None,
                    use_user_site=False,
                    upgrade_strategy="to-satisfy-only",
                    force_reinstall=False,
                    ignore_dependencies=options.ignore_dependencies,
                    py_version_info=options.python_version,
                    ignore_requires_python=False,
                    ignore_installed=True,
                    isolated=options.isolated_mode,
                )
                resolver.resolve(requirement_set)

                downloaded = ' '.join([
                    req.name for req in requirement_set.successfully_downloaded
                ])
                if downloaded:
                    logger.info('Successfully downloaded %s', downloaded)

                # Clean up
                if not options.no_clean:
                    requirement_set.cleanup_files()

        return requirement_set
