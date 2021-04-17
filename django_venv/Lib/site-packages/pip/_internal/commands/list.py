from __future__ import absolute_import

import json
import logging

from pip._vendor import six
from pip._vendor.six.moves import zip_longest

from pip._internal.cli import cmdoptions
from pip._internal.cli.base_command import Command
from pip._internal.cli.cmdoptions import make_search_scope
from pip._internal.exceptions import CommandError
from pip._internal.index import PackageFinder
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.utils.misc import (
    dist_is_editable, get_installed_distributions,
)
from pip._internal.utils.packaging import get_installer

logger = logging.getLogger(__name__)


class ListCommand(Command):
    """
    List installed packages, including editables.

    Packages are listed in a case-insensitive sorted order.
    """
    name = 'list'
    usage = """
      %prog [options]"""
    summary = 'List installed packages.'

    def __init__(self, *args, **kw):
        super(ListCommand, self).__init__(*args, **kw)

        cmd_opts = self.cmd_opts

        cmd_opts.add_option(
            '-o', '--outdated',
            action='store_true',
            default=False,
            help='List outdated packages')
        cmd_opts.add_option(
            '-u', '--uptodate',
            action='store_true',
            default=False,
            help='List uptodate packages')
        cmd_opts.add_option(
            '-e', '--editable',
            action='store_true',
            default=False,
            help='List editable projects.')
        cmd_opts.add_option(
            '-l', '--local',
            action='store_true',
            default=False,
            help=('If in a virtualenv that has global access, do not list '
                  'globally-installed packages.'),
        )
        self.cmd_opts.add_option(
            '--user',
            dest='user',
            action='store_true',
            default=False,
            help='Only output packages installed in user-site.')
        cmd_opts.add_option(cmdoptions.list_path())
        cmd_opts.add_option(
            '--pre',
            action='store_true',
            default=False,
            help=("Include pre-release and development versions. By default, "
                  "pip only finds stable versions."),
        )

        cmd_opts.add_option(
            '--format',
            action='store',
            dest='list_format',
            default="columns",
            choices=('columns', 'freeze', 'json'),
            help="Select the output format among: columns (default), freeze, "
                 "or json",
        )

        cmd_opts.add_option(
            '--not-required',
            action='store_true',
            dest='not_required',
            help="List packages that are not dependencies of "
                 "installed packages.",
        )

        cmd_opts.add_option(
            '--exclude-editable',
            action='store_false',
            dest='include_editable',
            help='Exclude editable package from output.',
        )
        cmd_opts.add_option(
            '--include-editable',
            action='store_true',
            dest='include_editable',
            help='Include editable package from output.',
            default=True,
        )
        index_opts = cmdoptions.make_option_group(
            cmdoptions.index_group, self.parser
        )

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, cmd_opts)

    def _build_package_finder(self, options, session):
        """
        Create a package finder appropriate to this list command.
        """
        search_scope = make_search_scope(options)

        # Pass allow_yanked=False to ignore yanked versions.
        selection_prefs = SelectionPreferences(
            allow_yanked=False,
            allow_all_prereleases=options.pre,
        )

        return PackageFinder.create(
            search_scope=search_scope,
            selection_prefs=selection_prefs,
            trusted_hosts=options.trusted_hosts,
            session=session,
        )

    def run(self, options, args):
        if options.outdated and options.uptodate:
            raise CommandError(
                "Options --outdated and --uptodate cannot be combined.")

        cmdoptions.check_list_path_option(options)

        packages = get_installed_distributions(
            local_only=options.local,
            user_only=options.user,
            editables_only=options.editable,
            include_editables=options.include_editable,
            paths=options.path,
        )

        # get_not_required must be called firstly in order to find and
        # filter out all dependencies correctly. Otherwise a package
        # can't be identified as requirement because some parent packages
        # could be filtered out before.
        if options.not_required:
            packages = self.get_not_required(packages, options)

        if options.outdated:
            packages = self.get_outdated(packages, options)
        elif options.uptodate:
            packages = self.get_uptodate(packages, options)

        self.output_package_listing(packages, options)

    def get_outdated(self, packages, options):
        return [
            dist for dist in self.iter_packages_latest_infos(packages, options)
            if dist.latest_version > dist.parsed_version
        ]

    def get_uptodate(self, packages, options):
        return [
            dist for dist in self.iter_packages_latest_infos(packages, options)
            if dist.latest_version == dist.parsed_version
        ]

    def get_not_required(self, packages, options):
        dep_keys = set()
        for dist in packages:
            dep_keys.update(requirement.key for requirement in dist.requires())
        return {pkg for pkg in packages if pkg.key not in dep_keys}

    def iter_packages_latest_infos(self, packages, options):
        with self._build_session(options) as session:
            finder = self._build_package_finder(options, session)

            for dist in packages:
                typ = 'unknown'
                all_candidates = finder.find_all_candidates(dist.key)
                if not options.pre:
                    # Remove prereleases
                    all_candidates = [candidate for candidate in all_candidates
                                      if not candidate.version.is_prerelease]

                evaluator = finder.make_candidate_evaluator(
                    project_name=dist.project_name,
                )
                best_candidate = evaluator.get_best_candidate(all_candidates)
                if best_candidate is None:
                    continue

                remote_version = best_candidate.version
                if best_candidate.link.is_wheel:
                    typ = 'wheel'
                else:
                    typ = 'sdist'
                # This is dirty but makes the rest of the code much cleaner
                dist.latest_version = remote_version
                dist.latest_filetype = typ
                yield dist

    def output_package_listing(self, packages, options):
        packages = sorted(
            packages,
            key=lambda dist: dist.project_name.lower(),
        )
        if options.list_format == 'columns' and packages:
            data, header = format_for_columns(packages, options)
            self.output_package_listing_columns(data, header)
        elif options.list_format == 'freeze':
            for dist in packages:
                if options.verbose >= 1:
                    logger.info("%s==%s (%s)", dist.project_name,
                                dist.version, dist.location)
                else:
                    logger.info("%s==%s", dist.project_name, dist.version)
        elif options.list_format == 'json':
            logger.info(format_for_json(packages, options))

    def output_package_listing_columns(self, data, header):
        # insert the header first: we need to know the size of column names
        if len(data) > 0:
            data.insert(0, header)

        pkg_strings, sizes = tabulate(data)

        # Create and add a separator.
        if len(data) > 0:
            pkg_strings.insert(1, " ".join(map(lambda x: '-' * x, sizes)))

        for val in pkg_strings:
            logger.info(val)


def tabulate(vals):
    # From pfmoore on GitHub:
    # https://github.com/pypa/pip/issues/3651#issuecomment-216932564
    assert len(vals) > 0

    sizes = [0] * max(len(x) for x in vals)
    for row in vals:
        sizes = [max(s, len(str(c))) for s, c in zip_longest(sizes, row)]

    result = []
    for row in vals:
        display = " ".join([str(c).ljust(s) if c is not None else ''
                            for s, c in zip_longest(sizes, row)])
        result.append(display)

    return result, sizes


def format_for_columns(pkgs, options):
    """
    Convert the package data into something usable
    by output_package_listing_columns.
    """
    running_outdated = options.outdated
    # Adjust the header for the `pip list --outdated` case.
    if running_outdated:
        header = ["Package", "Version", "Latest", "Type"]
    else:
        header = ["Package", "Version"]

    data = []
    if options.verbose >= 1 or any(dist_is_editable(x) for x in pkgs):
        header.append("Location")
    if options.verbose >= 1:
        header.append("Installer")

    for proj in pkgs:
        # if we're working on the 'outdated' list, separate out the
        # latest_version and type
        row = [proj.project_name, proj.version]

        if running_outdated:
            row.append(proj.latest_version)
            row.append(proj.latest_filetype)

        if options.verbose >= 1 or dist_is_editable(proj):
            row.append(proj.location)
        if options.verbose >= 1:
            row.append(get_installer(proj))

        data.append(row)

    return data, header


def format_for_json(packages, options):
    data = []
    for dist in packages:
        info = {
            'name': dist.project_name,
            'version': six.text_type(dist.version),
        }
        if options.verbose >= 1:
            info['location'] = dist.location
            info['installer'] = get_installer(dist)
        if options.outdated:
            info['latest_version'] = six.text_type(dist.latest_version)
            info['latest_filetype'] = dist.latest_filetype
        data.append(info)
    return json.dumps(data)
