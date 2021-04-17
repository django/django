# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import os

from pip._internal.cache import WheelCache
from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import RequirementCommand
from pip._internal.exceptions import CommandError, PreviousBuildDirError
from pip._internal.legacy_resolve import Resolver
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req import RequirementSet
from pip._internal.req.req_tracker import RequirementTracker
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.wheel import WheelBuilder

logger = logging.getLogger(__name__)


class WheelCommand(RequirementCommand):
    """
    Build Wheel archives for your requirements and dependencies.

    Wheel is a built-package format, and offers the advantage of not
    recompiling your software during every install. For more details, see the
    wheel docs: https://wheel.readthedocs.io/en/latest/

    Requirements: setuptools>=0.8, and wheel.

    'pip wheel' uses the bdist_wheel setuptools extension from the wheel
    package to build individual wheels.

    """

    name = 'wheel'
    usage = """
      %prog [options] <requirement specifier> ...
      %prog [options] -r <requirements file> ...
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    summary = 'Build wheels from your requirements.'

    def __init__(self, *args, **kw):
        super(WheelCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts

        cmd_opts.add_option(
            '-w', '--wheel-dir',
            dest='wheel_dir',
            metavar='dir',
            default=os.curdir,
            help=("Build wheels into <dir>, where the default is the "
                  "current working directory."),
        )
        cmd_opts.add_option(cmdoptions.no_binary())
        cmd_opts.add_option(cmdoptions.only_binary())
        cmd_opts.add_option(cmdoptions.prefer_binary())
        cmd_opts.add_option(
            '--build-option',
            dest='build_options',
            metavar='options',
            action='append',
            help="Extra arguments to be supplied to 'setup.py bdist_wheel'.",
        )
        cmd_opts.add_option(cmdoptions.no_build_isolation())
        cmd_opts.add_option(cmdoptions.use_pep517())
        cmd_opts.add_option(cmdoptions.no_use_pep517())
        cmd_opts.add_option(cmdoptions.constraints())
        cmd_opts.add_option(cmdoptions.editable())
        cmd_opts.add_option(cmdoptions.requirements())
        cmd_opts.add_option(cmdoptions.src())
        cmd_opts.add_option(cmdoptions.ignore_requires_python())
        cmd_opts.add_option(cmdoptions.no_deps())
        cmd_opts.add_option(cmdoptions.build_dir())
        cmd_opts.add_option(cmdoptions.progress_bar())

        cmd_opts.add_option(
            '--global-option',
            dest='global_options',
            action='append',
            metavar='options',
            help="Extra global options to be supplied to the setup.py "
            "call before the 'bdist_wheel' command.")

        cmd_opts.add_option(
            '--pre',
            action='store_true',
            default=False,
            help=("Include pre-release and development versions. By default, "
                  "pip only finds stable versions."),
        )

        cmd_opts.add_option(cmdoptions.no_clean())
        cmd_opts.add_option(cmdoptions.require_hashes())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, cmd_opts)

    def run(self, options, args):
        cmdoptions.check_install_build_global(options)

        if options.build_dir:
            options.build_dir = os.path.abspath(options.build_dir)

        options.src_dir = os.path.abspath(options.src_dir)

        with self._build_session(options) as session:
            finder = self._build_package_finder(options, session)
            build_delete = (not (options.no_clean or options.build_dir))
            wheel_cache = WheelCache(options.cache_dir, options.format_control)

            with RequirementTracker() as req_tracker, TempDirectory(
                options.build_dir, delete=build_delete, kind="wheel"
            ) as directory:

                requirement_set = RequirementSet(
                    require_hashes=options.require_hashes,
                )

                try:
                    self.populate_requirement_set(
                        requirement_set, args, options, finder, session,
                        self.name, wheel_cache
                    )

                    preparer = RequirementPreparer(
                        build_dir=directory.path,
                        src_dir=options.src_dir,
                        download_dir=None,
                        wheel_download_dir=options.wheel_dir,
                        progress_bar=options.progress_bar,
                        build_isolation=options.build_isolation,
                        req_tracker=req_tracker,
                    )

                    resolver = Resolver(
                        preparer=preparer,
                        finder=finder,
                        session=session,
                        wheel_cache=wheel_cache,
                        use_user_site=False,
                        upgrade_strategy="to-satisfy-only",
                        force_reinstall=False,
                        ignore_dependencies=options.ignore_dependencies,
                        ignore_requires_python=options.ignore_requires_python,
                        ignore_installed=True,
                        isolated=options.isolated_mode,
                        use_pep517=options.use_pep517
                    )
                    resolver.resolve(requirement_set)

                    # build wheels
                    wb = WheelBuilder(
                        finder, preparer, wheel_cache,
                        build_options=options.build_options or [],
                        global_options=options.global_options or [],
                        no_clean=options.no_clean,
                    )
                    build_failures = wb.build(
                        requirement_set.requirements.values(), session=session,
                    )
                    if len(build_failures) != 0:
                        raise CommandError(
                            "Failed to build one or more wheels"
                        )
                except PreviousBuildDirError:
                    options.no_clean = True
                    raise
                finally:
                    if not options.no_clean:
                        requirement_set.cleanup_files()
                        wheel_cache.cleanup()
