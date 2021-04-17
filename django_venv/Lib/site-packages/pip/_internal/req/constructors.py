"""Backing implementation for InstallRequirement's various constructors

The idea here is that these formed a major chunk of InstallRequirement's size
so, moving them and support code dedicated to them outside of that class
helps creates for better understandability for the rest of the code.

These are meant to be used elsewhere within pip to create instances of
InstallRequirement.
"""

import logging
import os
import re

from pip._vendor.packaging.markers import Marker
from pip._vendor.packaging.requirements import InvalidRequirement, Requirement
from pip._vendor.packaging.specifiers import Specifier
from pip._vendor.pkg_resources import RequirementParseError, parse_requirements

from pip._internal.download import is_archive_file, is_url, url_to_path
from pip._internal.exceptions import InstallationError
from pip._internal.models.index import PyPI, TestPyPI
from pip._internal.models.link import Link
from pip._internal.pyproject import make_pyproject_path
from pip._internal.req.req_install import InstallRequirement
from pip._internal.utils.misc import is_installable_dir, path_to_url
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.vcs import vcs
from pip._internal.wheel import Wheel

if MYPY_CHECK_RUNNING:
    from typing import (
        Any, Dict, Optional, Set, Tuple, Union,
    )
    from pip._internal.cache import WheelCache


__all__ = [
    "install_req_from_editable", "install_req_from_line",
    "parse_editable"
]

logger = logging.getLogger(__name__)
operators = Specifier._operators.keys()


def _strip_extras(path):
    # type: (str) -> Tuple[str, Optional[str]]
    m = re.match(r'^(.+)(\[[^\]]+\])$', path)
    extras = None
    if m:
        path_no_extras = m.group(1)
        extras = m.group(2)
    else:
        path_no_extras = path

    return path_no_extras, extras


def parse_editable(editable_req):
    # type: (str) -> Tuple[Optional[str], str, Optional[Set[str]]]
    """Parses an editable requirement into:
        - a requirement name
        - an URL
        - extras
        - editable options
    Accepted requirements:
        svn+http://blahblah@rev#egg=Foobar[baz]&subdirectory=version_subdir
        .[some_extra]
    """

    url = editable_req

    # If a file path is specified with extras, strip off the extras.
    url_no_extras, extras = _strip_extras(url)

    if os.path.isdir(url_no_extras):
        if not os.path.exists(os.path.join(url_no_extras, 'setup.py')):
            msg = (
                'File "setup.py" not found. Directory cannot be installed '
                'in editable mode: {}'.format(os.path.abspath(url_no_extras))
            )
            pyproject_path = make_pyproject_path(url_no_extras)
            if os.path.isfile(pyproject_path):
                msg += (
                    '\n(A "pyproject.toml" file was found, but editable '
                    'mode currently requires a setup.py based build.)'
                )
            raise InstallationError(msg)

        # Treating it as code that has already been checked out
        url_no_extras = path_to_url(url_no_extras)

    if url_no_extras.lower().startswith('file:'):
        package_name = Link(url_no_extras).egg_fragment
        if extras:
            return (
                package_name,
                url_no_extras,
                Requirement("placeholder" + extras.lower()).extras,
            )
        else:
            return package_name, url_no_extras, None

    for version_control in vcs:
        if url.lower().startswith('%s:' % version_control):
            url = '%s+%s' % (version_control, url)
            break

    if '+' not in url:
        raise InstallationError(
            '{} is not a valid editable requirement. '
            'It should either be a path to a local project or a VCS URL '
            '(beginning with svn+, git+, hg+, or bzr+).'.format(editable_req)
        )

    vc_type = url.split('+', 1)[0].lower()

    if not vcs.get_backend(vc_type):
        error_message = 'For --editable=%s only ' % editable_req + \
            ', '.join([backend.name + '+URL' for backend in vcs.backends]) + \
            ' is currently supported'
        raise InstallationError(error_message)

    package_name = Link(url).egg_fragment
    if not package_name:
        raise InstallationError(
            "Could not detect requirement name for '%s', please specify one "
            "with #egg=your_package_name" % editable_req
        )
    return package_name, url, None


def deduce_helpful_msg(req):
    # type: (str) -> str
    """Returns helpful msg in case requirements file does not exist,
    or cannot be parsed.

    :params req: Requirements file path
    """
    msg = ""
    if os.path.exists(req):
        msg = " It does exist."
        # Try to parse and check if it is a requirements file.
        try:
            with open(req, 'r') as fp:
                # parse first line only
                next(parse_requirements(fp.read()))
                msg += " The argument you provided " + \
                    "(%s) appears to be a" % (req) + \
                    " requirements file. If that is the" + \
                    " case, use the '-r' flag to install" + \
                    " the packages specified within it."
        except RequirementParseError:
            logger.debug("Cannot parse '%s' as requirements \
            file" % (req), exc_info=True)
    else:
        msg += " File '%s' does not exist." % (req)
    return msg


# ---- The actual constructors follow ----


def install_req_from_editable(
    editable_req,  # type: str
    comes_from=None,  # type: Optional[str]
    use_pep517=None,  # type: Optional[bool]
    isolated=False,  # type: bool
    options=None,  # type: Optional[Dict[str, Any]]
    wheel_cache=None,  # type: Optional[WheelCache]
    constraint=False  # type: bool
):
    # type: (...) -> InstallRequirement
    name, url, extras_override = parse_editable(editable_req)
    if url.startswith('file:'):
        source_dir = url_to_path(url)
    else:
        source_dir = None

    if name is not None:
        try:
            req = Requirement(name)
        except InvalidRequirement:
            raise InstallationError("Invalid requirement: '%s'" % name)
    else:
        req = None
    return InstallRequirement(
        req, comes_from, source_dir=source_dir,
        editable=True,
        link=Link(url),
        constraint=constraint,
        use_pep517=use_pep517,
        isolated=isolated,
        options=options if options else {},
        wheel_cache=wheel_cache,
        extras=extras_override or (),
    )


def install_req_from_line(
    name,  # type: str
    comes_from=None,  # type: Optional[Union[str, InstallRequirement]]
    use_pep517=None,  # type: Optional[bool]
    isolated=False,  # type: bool
    options=None,  # type: Optional[Dict[str, Any]]
    wheel_cache=None,  # type: Optional[WheelCache]
    constraint=False,  # type: bool
    line_source=None,  # type: Optional[str]
):
    # type: (...) -> InstallRequirement
    """Creates an InstallRequirement from a name, which might be a
    requirement, directory containing 'setup.py', filename, or URL.

    :param line_source: An optional string describing where the line is from,
        for logging purposes in case of an error.
    """
    if is_url(name):
        marker_sep = '; '
    else:
        marker_sep = ';'
    if marker_sep in name:
        name, markers_as_string = name.split(marker_sep, 1)
        markers_as_string = markers_as_string.strip()
        if not markers_as_string:
            markers = None
        else:
            markers = Marker(markers_as_string)
    else:
        markers = None
    name = name.strip()
    req_as_string = None
    path = os.path.normpath(os.path.abspath(name))
    link = None
    extras_as_string = None

    if is_url(name):
        link = Link(name)
    else:
        p, extras_as_string = _strip_extras(path)
        looks_like_dir = os.path.isdir(p) and (
            os.path.sep in name or
            (os.path.altsep is not None and os.path.altsep in name) or
            name.startswith('.')
        )
        if looks_like_dir:
            if not is_installable_dir(p):
                raise InstallationError(
                    "Directory %r is not installable. Neither 'setup.py' "
                    "nor 'pyproject.toml' found." % name
                )
            link = Link(path_to_url(p))
        elif is_archive_file(p):
            if not os.path.isfile(p):
                logger.warning(
                    'Requirement %r looks like a filename, but the '
                    'file does not exist',
                    name
                )
            link = Link(path_to_url(p))

    # it's a local file, dir, or url
    if link:
        # Handle relative file URLs
        if link.scheme == 'file' and re.search(r'\.\./', link.url):
            link = Link(
                path_to_url(os.path.normpath(os.path.abspath(link.path))))
        # wheel file
        if link.is_wheel:
            wheel = Wheel(link.filename)  # can raise InvalidWheelFilename
            req_as_string = "%s==%s" % (wheel.name, wheel.version)
        else:
            # set the req to the egg fragment.  when it's not there, this
            # will become an 'unnamed' requirement
            req_as_string = link.egg_fragment

    # a requirement specifier
    else:
        req_as_string = name

    if extras_as_string:
        extras = Requirement("placeholder" + extras_as_string.lower()).extras
    else:
        extras = ()
    if req_as_string is not None:
        try:
            req = Requirement(req_as_string)
        except InvalidRequirement:
            if os.path.sep in req_as_string:
                add_msg = "It looks like a path."
                add_msg += deduce_helpful_msg(req_as_string)
            elif ('=' in req_as_string and
                  not any(op in req_as_string for op in operators)):
                add_msg = "= is not a valid operator. Did you mean == ?"
            else:
                add_msg = ''
            if line_source is None:
                source = ''
            else:
                source = ' (from {})'.format(line_source)
            msg = (
                'Invalid requirement: {!r}{}'.format(req_as_string, source)
            )
            if add_msg:
                msg += '\nHint: {}'.format(add_msg)
            raise InstallationError(msg)
    else:
        req = None

    return InstallRequirement(
        req, comes_from, link=link, markers=markers,
        use_pep517=use_pep517, isolated=isolated,
        options=options if options else {},
        wheel_cache=wheel_cache,
        constraint=constraint,
        extras=extras,
    )


def install_req_from_req_string(
    req_string,  # type: str
    comes_from=None,  # type: Optional[InstallRequirement]
    isolated=False,  # type: bool
    wheel_cache=None,  # type: Optional[WheelCache]
    use_pep517=None  # type: Optional[bool]
):
    # type: (...) -> InstallRequirement
    try:
        req = Requirement(req_string)
    except InvalidRequirement:
        raise InstallationError("Invalid requirement: '%s'" % req_string)

    domains_not_allowed = [
        PyPI.file_storage_domain,
        TestPyPI.file_storage_domain,
    ]
    if (req.url and comes_from and comes_from.link and
            comes_from.link.netloc in domains_not_allowed):
        # Explicitly disallow pypi packages that depend on external urls
        raise InstallationError(
            "Packages installed from PyPI cannot depend on packages "
            "which are not also hosted on PyPI.\n"
            "%s depends on %s " % (comes_from.name, req)
        )

    return InstallRequirement(
        req, comes_from, isolated=isolated, wheel_cache=wheel_cache,
        use_pep517=use_pep517
    )
