from __future__ import absolute_import

import errno
import logging
import operator
import os
import shutil
from optparse import SUPPRESS_HELP

from pip._vendor import pkg_resources

from pip._internal.cache import WheelCache
from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import RequirementCommand
from pip._internal.cli.cmdoptions import make_target_python
from pip._internal.cli.status_codes import ERROR
from pip._internal.exceptions import (
    CommandError, InstallationError, PreviousBuildDirError,
)
from pip._internal.legacy_resolve import Resolver
from pip._internal.locations import distutils_scheme
from pip._internal.operations.check import check_install_conflicts
from pip._internal.operations.prepare import RequirementPreparer
from pip._internal.req import RequirementSet, install_given_reqs
from pip._internal.req.req_tracker import RequirementTracker
from pip._internal.utils.filesystem import check_path_owner
from pip._internal.utils.misc import (
    ensure_dir, get_installed_version,
    protect_pip_from_modification_on_windows,
)
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.virtualenv import virtualenv_no_global
from pip._internal.wheel import WheelBuilder

logger = logging.getLogger(__name__)


def is_wheel_installed():
    """
    Return whether the wheel package is installed.
    """
    try:
        import wheel  # noqa: F401
    except ImportError:
        return False

    return True


def build_wheels(builder, pep517_requirements, legacy_requirements, session):
    """
    Build wheels for requirements, depending on whether wheel is installed.
    """
    # We don't build wheels for legacy requirements if wheel is not installed.
    should_build_legacy = is_wheel_installed()

    # Always build PEP 517 requirements
    build_failures = builder.build(
        pep517_requirements,
        session=session, autobuilding=True
    )

    if should_build_legacy:
        # We don't care about failures building legacy
        # requirements, as we'll fall through to a direct
        # install for those.
        builder.build(
            legacy_requirements,
            session=session, autobuilding=True
        )

    return build_failures


class InstallCommand(RequirementCommand):
    """
    Install packages from:

    - PyPI (and other indexes) using requirement specifiers.
    - VCS project urls.
    - Local project directories.
    - Local or remote source archives.

    pip also supports installing from "requirements files," which provide
    an easy way to specify a whole environment to be installed.
    """
    name = 'install'

    usage = """
      %prog [options] <requirement specifier> [package-index-options] ...
      %prog [options] -r <requirements file> [package-index-options] ...
      %prog [options] [-e] <vcs project url> ...
      %prog [options] [-e] <local project path> ...
      %prog [options] <archive url/path> ..."""

    summary = 'Install packages.'

    def __init__(self, *args, **kw):
        super(InstallCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts

        cmd_opts.add_option(cmdoptions.requirements())
        cmd_opts.add_option(cmdoptions.constraints())
        cmd_opts.add_option(cmdoptions.no_deps())
        cmd_opts.add_option(cmdoptions.pre())

        cmd_opts.add_option(cmdoptions.editable())
        cmd_opts.add_option(
            '-t', '--target',
            dest='target_dir',
            metavar='dir',
            default=None,
            help='Install packages into <dir>. '
                 'By default this will not replace existing files/folders in '
                 '<dir>. Use --upgrade to replace existing packages in <dir> '
                 'with new versions.'
        )
        cmdoptions.add_target_python_options(cmd_opts)

        cmd_opts.add_option(
            '--user',
            dest='use_user_site',
            action='store_true',
            help="Install to the Python user install directory for your "
                 "platform. Typically ~/.local/, or %APPDATA%\\Python on "
                 "Windows. (See the Python documentation for site.USER_BASE "
                 "for full details.)")
        cmd_opts.add_option(
            '--no-user',
            dest='use_user_site',
            action='store_false',
            help=SUPPRESS_HELP)
        cmd_opts.add_option(
            '--root',
            dest='root_path',
            metavar='dir',
            default=None,
            help="Install everything relative to this alternate root "
                 "directory.")
        cmd_opts.add_option(
            '--prefix',
            dest='prefix_path',
            metavar='dir',
            default=None,
            help="Installation prefix where lib, bin and other top-level "
                 "folders are placed")

        cmd_opts.add_option(cmdoptions.build_dir())

        cmd_opts.add_option(cmdoptions.src())

        cmd_opts.add_option(
            '-U', '--upgrade',
            dest='upgrade',
            action='store_true',
            help='Upgrade all specified packages to the newest available '
                 'version. The handling of dependencies depends on the '
                 'upgrade-strategy used.'
        )

        cmd_opts.add_option(
            '--upgrade-strategy',
            dest='upgrade_strategy',
            default='only-if-needed',
            choices=['only-if-needed', 'eager'],
            help='Determines how dependency upgrading should be handled '
                 '[default: %default]. '
                 '"eager" - dependencies are upgraded regardless of '
                 'whether the currently installed version satisfies the '
                 'requirements of the upgraded package(s). '
                 '"only-if-needed" -  are upgraded only when they do not '
                 'satisfy the requirements of the upgraded package(s).'
        )

        cmd_opts.add_option(
            '--force-reinstall',
            dest='force_reinstall',
            action='store_true',
            help='Reinstall all packages even if they are already '
                 'up-to-date.')

        cmd_opts.add_option(
            '-I', '--ignore-installed',
            dest='ignore_installed',
            action='store_true',
            help='Ignore the installed packages (reinstalling instead).')

        cmd_opts.add_option(cmdoptions.ignore_requires_python())
        cmd_opts.add_option(cmdoptions.no_build_isolation())
        cmd_opts.add_option(cmdoptions.use_pep517())
        cmd_opts.add_option(cmdoptions.no_use_pep517())

        cmd_opts.add_option(cmdoptions.install_options())
        cmd_opts.add_option(cmdoptions.global_options())

        cmd_opts.add_option(
            "--compile",
            action="store_true",
            dest="compile",
            default=True,
            help="Compile Python source files to bytecode",
        )

        cmd_opts.add_option(
            "--no-compile",
            action="store_false",
            dest="compile",
            help="Do not compile Python source files to bytecode",
        )

        cmd_opts.add_option(
            "--no-warn-script-location",
            action="store_false",
            dest="warn_script_location",
            default=True,
            help="Do not warn when installing scripts outside PATH",
        )
        cmd_opts.add_option(
            "--no-warn-conflicts",
            action="store_false",
            dest="warn_about_conflicts",
            default=True,
            help="Do not warn about broken dependencies",
        )

        cmd_opts.add_option(cmdoptions.no_binary())
        cmd_opts.add_option(cmdoptions.only_binary())
        cmd_opts.add_option(cmdoptions.prefer_binary())
        cmd_opts.add_option(cmdoptions.no_clean())
        cmd_opts.add_option(cmdoptions.require_hashes())
        cmd_opts.add_option(cmdoptions.progress_bar())

        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group,
            self.parser,
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, cmd_opts)

    def run(self, options, args):
        cmdoptions.check_install_build_global(options)
        upgrade_strategy = "to-satisfy-only"
        if options.upgrade:
            upgrade_strategy = options.upgrade_strategy

        if options.build_dir:
            options.build_dir = os.path.abspath(options.build_dir)

        cmdoptions.check_dist_restriction(options, check_target=True)

        options.src_dir = os.path.abspath(options.src_dir)
        install_options = options.install_options or []
        if options.use_user_site:
            if options.prefix_path:
                raise CommandError(
                    "Can not combine '--user' and '--prefix' as they imply "
                    "different installation locations"
                )
            if virtualenv_no_global():
                raise InstallationError(
                    "Can not perform a '--user' install. User site-packages "
                    "are not visible in this virtualenv."
                )
            install_options.append('--user')
            install_options.append('--prefix=')

        target_temp_dir = TempDirectory(kind="target")
        if options.target_dir:
            options.ignore_installed = True
            options.target_dir = os.path.abspath(options.target_dir)
            if (os.path.exists(options.target_dir) and not
                    os.path.isdir(options.target_dir)):
                raise CommandError(
                    "Target path exists but is not a directory, will not "
                    "continue."
                )

            # Create a target directory for using with the target option
            target_temp_dir.create()
            install_options.append('--home=' + target_temp_dir.path)

        global_options = options.global_options or []

        with self._build_session(options) as session:
            target_python = make_target_python(options)
            finder = self._build_package_finder(
                options=options,
                session=session,
                target_python=target_python,
                ignore_requires_python=options.ignore_requires_python,
            )
            build_delete = (not (options.no_clean or options.build_dir))
            wheel_cache = WheelCache(options.cache_dir, options.format_control)

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
                options.build_dir, delete=build_delete, kind="install"
            ) as directory:
                requirement_set = RequirementSet(
                    require_hashes=options.require_hashes,
                    check_supported_wheels=not options.target_dir,
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
                        wheel_download_dir=None,
                        progress_bar=options.progress_bar,
                        build_isolation=options.build_isolation,
                        req_tracker=req_tracker,
                    )

                    resolver = Resolver(
                        preparer=preparer,
                        finder=finder,
                        session=session,
                        wheel_cache=wheel_cache,
                        use_user_site=options.use_user_site,
                        upgrade_strategy=upgrade_strategy,
                        force_reinstall=options.force_reinstall,
                        ignore_dependencies=options.ignore_dependencies,
                        ignore_requires_python=options.ignore_requires_python,
                        ignore_installed=options.ignore_installed,
                        isolated=options.isolated_mode,
                        use_pep517=options.use_pep517
                    )
                    resolver.resolve(requirement_set)

                    protect_pip_from_modification_on_windows(
                        modifying_pip=requirement_set.has_requirement("pip")
                    )

                    # Consider legacy and PEP517-using requirements separately
                    legacy_requirements = []
                    pep517_requirements = []
                    for req in requirement_set.requirements.values():
                        if req.use_pep517:
                            pep517_requirements.append(req)
                        else:
                            legacy_requirements.append(req)

                    wheel_builder = WheelBuilder(
                        finder, preparer, wheel_cache,
                        build_options=[], global_options=[],
                    )

                    build_failures = build_wheels(
                        builder=wheel_builder,
                        pep517_requirements=pep517_requirements,
                        legacy_requirements=legacy_requirements,
                        session=session,
                    )

                    # If we're using PEP 517, we cannot do a direct install
                    # so we fail here.
                    if build_failures:
                        raise InstallationError(
                            "Could not build wheels for {} which use"
                            " PEP 517 and cannot be installed directly".format(
                                ", ".join(r.name for r in build_failures)))

                    to_install = resolver.get_installation_order(
                        requirement_set
                    )

                    # Consistency Checking of the package set we're installing.
                    should_warn_about_conflicts = (
                        not options.ignore_dependencies and
                        options.warn_about_conflicts
                    )
                    if should_warn_about_conflicts:
                        self._warn_about_conflicts(to_install)

                    # Don't warn about script install locations if
                    # --target has been specified
                    warn_script_location = options.warn_script_location
                    if options.target_dir:
                        warn_script_location = False

                    installed = install_given_reqs(
                        to_install,
                        install_options,
                        global_options,
                        root=options.root_path,
                        home=target_temp_dir.path,
                        prefix=options.prefix_path,
                        pycompile=options.compile,
                        warn_script_location=warn_script_location,
                        use_user_site=options.use_user_site,
                    )

                    lib_locations = get_lib_location_guesses(
                        user=options.use_user_site,
                        home=target_temp_dir.path,
                        root=options.root_path,
                        prefix=options.prefix_path,
                        isolated=options.isolated_mode,
                    )
                    working_set = pkg_resources.WorkingSet(lib_locations)

                    reqs = sorted(installed, key=operator.attrgetter('name'))
                    items = []
                    for req in reqs:
                        item = req.name
                        try:
                            installed_version = get_installed_version(
                                req.name, working_set=working_set
                            )
                            if installed_version:
                                item += '-' + installed_version
                        except Exception:
                            pass
                        items.append(item)
                    installed = ' '.join(items)
                    if installed:
                        logger.info('Successfully installed %s', installed)
                except EnvironmentError as error:
                    show_traceback = (self.verbosity >= 1)

                    message = create_env_error_message(
                        error, show_traceback, options.use_user_site,
                    )
                    logger.error(message, exc_info=show_traceback)

                    return ERROR
                except PreviousBuildDirError:
                    options.no_clean = True
                    raise
                finally:
                    # Clean up
                    if not options.no_clean:
                        requirement_set.cleanup_files()
                        wheel_cache.cleanup()

        if options.target_dir:
            self._handle_target_dir(
                options.target_dir, target_temp_dir, options.upgrade
            )
        return requirement_set

    def _handle_target_dir(self, target_dir, target_temp_dir, upgrade):
        ensure_dir(target_dir)

        # Checking both purelib and platlib directories for installed
        # packages to be moved to target directory
        lib_dir_list = []

        with target_temp_dir:
            # Checking both purelib and platlib directories for installed
            # packages to be moved to target directory
            scheme = distutils_scheme('', home=target_temp_dir.path)
            purelib_dir = scheme['purelib']
            platlib_dir = scheme['platlib']
            data_dir = scheme['data']

            if os.path.exists(purelib_dir):
                lib_dir_list.append(purelib_dir)
            if os.path.exists(platlib_dir) and platlib_dir != purelib_dir:
                lib_dir_list.append(platlib_dir)
            if os.path.exists(data_dir):
                lib_dir_list.append(data_dir)

            for lib_dir in lib_dir_list:
                for item in os.listdir(lib_dir):
                    if lib_dir == data_dir:
                        ddir = os.path.join(data_dir, item)
                        if any(s.startswith(ddir) for s in lib_dir_list[:-1]):
                            continue
                    target_item_dir = os.path.join(target_dir, item)
                    if os.path.exists(target_item_dir):
                        if not upgrade:
                            logger.warning(
                                'Target directory %s already exists. Specify '
                                '--upgrade to force replacement.',
                                target_item_dir
                            )
                            continue
                        if os.path.islink(target_item_dir):
                            logger.warning(
                                'Target directory %s already exists and is '
                                'a link. Pip will not automatically replace '
                                'links, please remove if replacement is '
                                'desired.',
                                target_item_dir
                            )
                            continue
                        if os.path.isdir(target_item_dir):
                            shutil.rmtree(target_item_dir)
                        else:
                            os.remove(target_item_dir)

                    shutil.move(
                        os.path.join(lib_dir, item),
                        target_item_dir
                    )

    def _warn_about_conflicts(self, to_install):
        try:
            package_set, _dep_info = check_install_conflicts(to_install)
        except Exception:
            logger.error("Error checking for conflicts.", exc_info=True)
            return
        missing, conflicting = _dep_info

        # NOTE: There is some duplication here from pip check
        for project_name in missing:
            version = package_set[project_name][0]
            for dependency in missing[project_name]:
                logger.critical(
                    "%s %s requires %s, which is not installed.",
                    project_name, version, dependency[1],
                )

        for project_name in conflicting:
            version = package_set[project_name][0]
            for dep_name, dep_version, req in conflicting[project_name]:
                logger.critical(
                    "%s %s has requirement %s, but you'll have %s %s which is "
                    "incompatible.",
                    project_name, version, req, dep_name, dep_version,
                )


def get_lib_location_guesses(*args, **kwargs):
    scheme = distutils_scheme('', *args, **kwargs)
    return [scheme['purelib'], scheme['platlib']]


def create_env_error_message(error, show_traceback, using_user_site):
    """Format an error message for an EnvironmentError

    It may occur anytime during the execution of the install command.
    """
    parts = []

    # Mention the error if we are not going to show a traceback
    parts.append("Could not install packages due to an EnvironmentError")
    if not show_traceback:
        parts.append(": ")
        parts.append(str(error))
    else:
        parts.append(".")

    # Spilt the error indication from a helper message (if any)
    parts[-1] += "\n"

    # Suggest useful actions to the user:
    #  (1) using user site-packages or (2) verifying the permissions
    if error.errno == errno.EACCES:
        user_option_part = "Consider using the `--user` option"
        permissions_part = "Check the permissions"

        if not using_user_site:
            parts.extend([
                user_option_part, " or ",
                permissions_part.lower(),
            ])
        else:
            parts.append(permissions_part)
        parts.append(".\n")

    return "".join(parts).strip() + "\n"
