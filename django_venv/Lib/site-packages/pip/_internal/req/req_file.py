"""
Requirements file parsing
"""

from __future__ import absolute_import

import optparse
import os
import re
import shlex
import sys

from pip._vendor.six.moves import filterfalse
from pip._vendor.six.moves.urllib import parse as urllib_parse

from pip._internal.cli import cmdoptions
from pip._internal.download import get_file_content
from pip._internal.exceptions import RequirementsFileParseError
from pip._internal.models.search_scope import SearchScope
from pip._internal.req.constructors import (
    install_req_from_editable, install_req_from_line,
)
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import (
        Any, Callable, Iterator, List, NoReturn, Optional, Text, Tuple,
    )
    from pip._internal.req import InstallRequirement
    from pip._internal.cache import WheelCache
    from pip._internal.index import PackageFinder
    from pip._internal.download import PipSession

    ReqFileLines = Iterator[Tuple[int, Text]]

__all__ = ['parse_requirements']

SCHEME_RE = re.compile(r'^(http|https|file):', re.I)
COMMENT_RE = re.compile(r'(^|\s+)#.*$')

# Matches environment variable-style values in '${MY_VARIABLE_1}' with the
# variable name consisting of only uppercase letters, digits or the '_'
# (underscore). This follows the POSIX standard defined in IEEE Std 1003.1,
# 2013 Edition.
ENV_VAR_RE = re.compile(r'(?P<var>\$\{(?P<name>[A-Z0-9_]+)\})')

SUPPORTED_OPTIONS = [
    cmdoptions.constraints,
    cmdoptions.editable,
    cmdoptions.requirements,
    cmdoptions.no_index,
    cmdoptions.index_url,
    cmdoptions.find_links,
    cmdoptions.extra_index_url,
    cmdoptions.always_unzip,
    cmdoptions.no_binary,
    cmdoptions.only_binary,
    cmdoptions.pre,
    cmdoptions.trusted_host,
    cmdoptions.require_hashes,
]  # type: List[Callable[..., optparse.Option]]

# options to be passed to requirements
SUPPORTED_OPTIONS_REQ = [
    cmdoptions.install_options,
    cmdoptions.global_options,
    cmdoptions.hash,
]  # type: List[Callable[..., optparse.Option]]

# the 'dest' string values
SUPPORTED_OPTIONS_REQ_DEST = [str(o().dest) for o in SUPPORTED_OPTIONS_REQ]


def parse_requirements(
    filename,  # type: str
    finder=None,  # type: Optional[PackageFinder]
    comes_from=None,  # type: Optional[str]
    options=None,  # type: Optional[optparse.Values]
    session=None,  # type: Optional[PipSession]
    constraint=False,  # type: bool
    wheel_cache=None,  # type: Optional[WheelCache]
    use_pep517=None  # type: Optional[bool]
):
    # type: (...) -> Iterator[InstallRequirement]
    """Parse a requirements file and yield InstallRequirement instances.

    :param filename:    Path or url of requirements file.
    :param finder:      Instance of pip.index.PackageFinder.
    :param comes_from:  Origin description of requirements.
    :param options:     cli options.
    :param session:     Instance of pip.download.PipSession.
    :param constraint:  If true, parsing a constraint file rather than
        requirements file.
    :param wheel_cache: Instance of pip.wheel.WheelCache
    :param use_pep517:  Value of the --use-pep517 option.
    """
    if session is None:
        raise TypeError(
            "parse_requirements() missing 1 required keyword argument: "
            "'session'"
        )

    _, content = get_file_content(
        filename, comes_from=comes_from, session=session
    )

    lines_enum = preprocess(content, options)

    for line_number, line in lines_enum:
        req_iter = process_line(line, filename, line_number, finder,
                                comes_from, options, session, wheel_cache,
                                use_pep517=use_pep517, constraint=constraint)
        for req in req_iter:
            yield req


def preprocess(content, options):
    # type: (Text, Optional[optparse.Values]) -> ReqFileLines
    """Split, filter, and join lines, and return a line iterator

    :param content: the content of the requirements file
    :param options: cli options
    """
    lines_enum = enumerate(content.splitlines(), start=1)  # type: ReqFileLines
    lines_enum = join_lines(lines_enum)
    lines_enum = ignore_comments(lines_enum)
    lines_enum = skip_regex(lines_enum, options)
    lines_enum = expand_env_variables(lines_enum)
    return lines_enum


def process_line(
    line,  # type: Text
    filename,  # type: str
    line_number,  # type: int
    finder=None,  # type: Optional[PackageFinder]
    comes_from=None,  # type: Optional[str]
    options=None,  # type: Optional[optparse.Values]
    session=None,  # type: Optional[PipSession]
    wheel_cache=None,  # type: Optional[WheelCache]
    use_pep517=None,  # type: Optional[bool]
    constraint=False,  # type: bool
):
    # type: (...) -> Iterator[InstallRequirement]
    """Process a single requirements line; This can result in creating/yielding
    requirements, or updating the finder.

    For lines that contain requirements, the only options that have an effect
    are from SUPPORTED_OPTIONS_REQ, and they are scoped to the
    requirement. Other options from SUPPORTED_OPTIONS may be present, but are
    ignored.

    For lines that do not contain requirements, the only options that have an
    effect are from SUPPORTED_OPTIONS. Options from SUPPORTED_OPTIONS_REQ may
    be present, but are ignored. These lines may contain multiple options
    (although our docs imply only one is supported), and all our parsed and
    affect the finder.

    :param constraint: If True, parsing a constraints file.
    :param options: OptionParser options that we may update
    """
    parser = build_parser(line)
    defaults = parser.get_default_values()
    defaults.index_url = None
    if finder:
        defaults.format_control = finder.format_control
    args_str, options_str = break_args_options(line)
    # Prior to 2.7.3, shlex cannot deal with unicode entries
    if sys.version_info < (2, 7, 3):
        # https://github.com/python/mypy/issues/1174
        options_str = options_str.encode('utf8')  # type: ignore
    # https://github.com/python/mypy/issues/1174
    opts, _ = parser.parse_args(
        shlex.split(options_str), defaults)  # type: ignore

    # preserve for the nested code path
    line_comes_from = '%s %s (line %s)' % (
        '-c' if constraint else '-r', filename, line_number,
    )

    # yield a line requirement
    if args_str:
        isolated = options.isolated_mode if options else False
        if options:
            cmdoptions.check_install_build_global(options, opts)
        # get the options that apply to requirements
        req_options = {}
        for dest in SUPPORTED_OPTIONS_REQ_DEST:
            if dest in opts.__dict__ and opts.__dict__[dest]:
                req_options[dest] = opts.__dict__[dest]
        line_source = 'line {} of {}'.format(line_number, filename)
        yield install_req_from_line(
            args_str,
            comes_from=line_comes_from,
            use_pep517=use_pep517,
            isolated=isolated,
            options=req_options,
            wheel_cache=wheel_cache,
            constraint=constraint,
            line_source=line_source,
        )

    # yield an editable requirement
    elif opts.editables:
        isolated = options.isolated_mode if options else False
        yield install_req_from_editable(
            opts.editables[0], comes_from=line_comes_from,
            use_pep517=use_pep517,
            constraint=constraint, isolated=isolated, wheel_cache=wheel_cache
        )

    # parse a nested requirements file
    elif opts.requirements or opts.constraints:
        if opts.requirements:
            req_path = opts.requirements[0]
            nested_constraint = False
        else:
            req_path = opts.constraints[0]
            nested_constraint = True
        # original file is over http
        if SCHEME_RE.search(filename):
            # do a url join so relative paths work
            req_path = urllib_parse.urljoin(filename, req_path)
        # original file and nested file are paths
        elif not SCHEME_RE.search(req_path):
            # do a join so relative paths work
            req_path = os.path.join(os.path.dirname(filename), req_path)
        # TODO: Why not use `comes_from='-r {} (line {})'` here as well?
        parsed_reqs = parse_requirements(
            req_path, finder, comes_from, options, session,
            constraint=nested_constraint, wheel_cache=wheel_cache
        )
        for req in parsed_reqs:
            yield req

    # percolate hash-checking option upward
    elif opts.require_hashes:
        options.require_hashes = opts.require_hashes

    # set finder options
    elif finder:
        find_links = finder.find_links
        index_urls = finder.index_urls
        if opts.index_url:
            index_urls = [opts.index_url]
        if opts.no_index is True:
            index_urls = []
        if opts.extra_index_urls:
            index_urls.extend(opts.extra_index_urls)
        if opts.find_links:
            # FIXME: it would be nice to keep track of the source
            # of the find_links: support a find-links local path
            # relative to a requirements file.
            value = opts.find_links[0]
            req_dir = os.path.dirname(os.path.abspath(filename))
            relative_to_reqs_file = os.path.join(req_dir, value)
            if os.path.exists(relative_to_reqs_file):
                value = relative_to_reqs_file
            find_links.append(value)

        search_scope = SearchScope(
            find_links=find_links,
            index_urls=index_urls,
        )
        finder.search_scope = search_scope

        if opts.pre:
            finder.set_allow_all_prereleases()
        for host in opts.trusted_hosts or []:
            source = 'line {} of {}'.format(line_number, filename)
            finder.add_trusted_host(host, source=source)


def break_args_options(line):
    # type: (Text) -> Tuple[str, Text]
    """Break up the line into an args and options string.  We only want to shlex
    (and then optparse) the options, not the args.  args can contain markers
    which are corrupted by shlex.
    """
    tokens = line.split(' ')
    args = []
    options = tokens[:]
    for token in tokens:
        if token.startswith('-') or token.startswith('--'):
            break
        else:
            args.append(token)
            options.pop(0)
    return ' '.join(args), ' '.join(options)  # type: ignore


def build_parser(line):
    # type: (Text) -> optparse.OptionParser
    """
    Return a parser for parsing requirement lines
    """
    parser = optparse.OptionParser(add_help_option=False)

    option_factories = SUPPORTED_OPTIONS + SUPPORTED_OPTIONS_REQ
    for option_factory in option_factories:
        option = option_factory()
        parser.add_option(option)

    # By default optparse sys.exits on parsing errors. We want to wrap
    # that in our own exception.
    def parser_exit(self, msg):
        # type: (Any, str) -> NoReturn
        # add offending line
        msg = 'Invalid requirement: %s\n%s' % (line, msg)
        raise RequirementsFileParseError(msg)
    # NOTE: mypy disallows assigning to a method
    #       https://github.com/python/mypy/issues/2427
    parser.exit = parser_exit  # type: ignore

    return parser


def join_lines(lines_enum):
    # type: (ReqFileLines) -> ReqFileLines
    """Joins a line ending in '\' with the previous line (except when following
    comments).  The joined line takes on the index of the first line.
    """
    primary_line_number = None
    new_line = []  # type: List[Text]
    for line_number, line in lines_enum:
        if not line.endswith('\\') or COMMENT_RE.match(line):
            if COMMENT_RE.match(line):
                # this ensures comments are always matched later
                line = ' ' + line
            if new_line:
                new_line.append(line)
                yield primary_line_number, ''.join(new_line)
                new_line = []
            else:
                yield line_number, line
        else:
            if not new_line:
                primary_line_number = line_number
            new_line.append(line.strip('\\'))

    # last line contains \
    if new_line:
        yield primary_line_number, ''.join(new_line)

    # TODO: handle space after '\'.


def ignore_comments(lines_enum):
    # type: (ReqFileLines) -> ReqFileLines
    """
    Strips comments and filter empty lines.
    """
    for line_number, line in lines_enum:
        line = COMMENT_RE.sub('', line)
        line = line.strip()
        if line:
            yield line_number, line


def skip_regex(lines_enum, options):
    # type: (ReqFileLines, Optional[optparse.Values]) -> ReqFileLines
    """
    Skip lines that match '--skip-requirements-regex' pattern

    Note: the regex pattern is only built once
    """
    skip_regex = options.skip_requirements_regex if options else None
    if skip_regex:
        pattern = re.compile(skip_regex)
        lines_enum = filterfalse(lambda e: pattern.search(e[1]), lines_enum)
    return lines_enum


def expand_env_variables(lines_enum):
    # type: (ReqFileLines) -> ReqFileLines
    """Replace all environment variables that can be retrieved via `os.getenv`.

    The only allowed format for environment variables defined in the
    requirement file is `${MY_VARIABLE_1}` to ensure two things:

    1. Strings that contain a `$` aren't accidentally (partially) expanded.
    2. Ensure consistency across platforms for requirement files.

    These points are the result of a discussion on the `github pull
    request #3514 <https://github.com/pypa/pip/pull/3514>`_.

    Valid characters in variable names follow the `POSIX standard
    <http://pubs.opengroup.org/onlinepubs/9699919799/>`_ and are limited
    to uppercase letter, digits and the `_` (underscore).
    """
    for line_number, line in lines_enum:
        for env_var, var_name in ENV_VAR_RE.findall(line):
            value = os.getenv(var_name)
            if not value:
                continue

            line = line.replace(env_var, value)

        yield line_number, line
