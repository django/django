from __future__ import absolute_import

import contextlib
import errno
import getpass
import io
# we have a submodule named 'logging' which would shadow this if we used the
# regular name:
import logging as std_logging
import os
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile
from collections import deque

from pip._vendor import pkg_resources
# NOTE: retrying is not annotated in typeshed as on 2017-07-17, which is
#       why we ignore the type on this import.
from pip._vendor.retrying import retry  # type: ignore
from pip._vendor.six import PY2, text_type
from pip._vendor.six.moves import input, shlex_quote
from pip._vendor.six.moves.urllib import parse as urllib_parse
from pip._vendor.six.moves.urllib import request as urllib_request
from pip._vendor.six.moves.urllib.parse import unquote as urllib_unquote

from pip import __version__
from pip._internal.exceptions import CommandError, InstallationError
from pip._internal.locations import site_packages, user_site
from pip._internal.utils.compat import (
    WINDOWS, console_to_str, expanduser, stdlib_pkgs, str_to_display,
)
from pip._internal.utils.marker_files import write_delete_marker_file
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.utils.virtualenv import (
    running_under_virtualenv, virtualenv_no_global,
)

if PY2:
    from io import BytesIO as StringIO
else:
    from io import StringIO

if MYPY_CHECK_RUNNING:
    from typing import (
        Any, AnyStr, Container, Iterable, List, Mapping, Match, Optional, Text,
        Tuple, Union, cast,
    )
    from pip._vendor.pkg_resources import Distribution
    from pip._internal.models.link import Link
    from pip._internal.utils.ui import SpinnerInterface

    VersionInfo = Tuple[int, int, int]
else:
    # typing's cast() is needed at runtime, but we don't want to import typing.
    # Thus, we use a dummy no-op version, which we tell mypy to ignore.
    def cast(type_, value):  # type: ignore
        return value


__all__ = ['rmtree', 'display_path', 'backup_dir',
           'ask', 'splitext',
           'format_size', 'is_installable_dir',
           'is_svn_page', 'file_contents',
           'split_leading_dir', 'has_leading_dir',
           'normalize_path',
           'renames', 'get_prog',
           'unzip_file', 'untar_file', 'unpack_file', 'call_subprocess',
           'captured_stdout', 'ensure_dir',
           'ARCHIVE_EXTENSIONS', 'SUPPORTED_EXTENSIONS', 'WHEEL_EXTENSION',
           'get_installed_version', 'remove_auth_from_url']


logger = std_logging.getLogger(__name__)
subprocess_logger = std_logging.getLogger('pip.subprocessor')

LOG_DIVIDER = '----------------------------------------'

WHEEL_EXTENSION = '.whl'
BZ2_EXTENSIONS = ('.tar.bz2', '.tbz')
XZ_EXTENSIONS = ('.tar.xz', '.txz', '.tlz', '.tar.lz', '.tar.lzma')
ZIP_EXTENSIONS = ('.zip', WHEEL_EXTENSION)
TAR_EXTENSIONS = ('.tar.gz', '.tgz', '.tar')
ARCHIVE_EXTENSIONS = (
    ZIP_EXTENSIONS + BZ2_EXTENSIONS + TAR_EXTENSIONS + XZ_EXTENSIONS)
SUPPORTED_EXTENSIONS = ZIP_EXTENSIONS + TAR_EXTENSIONS

try:
    import bz2  # noqa
    SUPPORTED_EXTENSIONS += BZ2_EXTENSIONS
except ImportError:
    logger.debug('bz2 module is not available')

try:
    # Only for Python 3.3+
    import lzma  # noqa
    SUPPORTED_EXTENSIONS += XZ_EXTENSIONS
except ImportError:
    logger.debug('lzma module is not available')


def get_pip_version():
    # type: () -> str
    pip_pkg_dir = os.path.join(os.path.dirname(__file__), "..", "..")
    pip_pkg_dir = os.path.abspath(pip_pkg_dir)

    return (
        'pip {} from {} (python {})'.format(
            __version__, pip_pkg_dir, sys.version[:3],
        )
    )


def normalize_version_info(py_version_info):
    # type: (Tuple[int, ...]) -> Tuple[int, int, int]
    """
    Convert a tuple of ints representing a Python version to one of length
    three.

    :param py_version_info: a tuple of ints representing a Python version,
        or None to specify no version. The tuple can have any length.

    :return: a tuple of length three if `py_version_info` is non-None.
        Otherwise, return `py_version_info` unchanged (i.e. None).
    """
    if len(py_version_info) < 3:
        py_version_info += (3 - len(py_version_info)) * (0,)
    elif len(py_version_info) > 3:
        py_version_info = py_version_info[:3]

    return cast('VersionInfo', py_version_info)


def ensure_dir(path):
    # type: (AnyStr) -> None
    """os.path.makedirs without EEXIST."""
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def get_prog():
    # type: () -> str
    try:
        prog = os.path.basename(sys.argv[0])
        if prog in ('__main__.py', '-c'):
            return "%s -m pip" % sys.executable
        else:
            return prog
    except (AttributeError, TypeError, IndexError):
        pass
    return 'pip'


# Retry every half second for up to 3 seconds
@retry(stop_max_delay=3000, wait_fixed=500)
def rmtree(dir, ignore_errors=False):
    # type: (str, bool) -> None
    shutil.rmtree(dir, ignore_errors=ignore_errors,
                  onerror=rmtree_errorhandler)


def rmtree_errorhandler(func, path, exc_info):
    """On Windows, the files in .svn are read-only, so when rmtree() tries to
    remove them, an exception is thrown.  We catch that here, remove the
    read-only attribute, and hopefully continue without problems."""
    # if file type currently read only
    if os.stat(path).st_mode & stat.S_IREAD:
        # convert to read/write
        os.chmod(path, stat.S_IWRITE)
        # use the original function to repeat the operation
        func(path)
        return
    else:
        raise


def path_to_display(path):
    # type: (Optional[Union[str, Text]]) -> Optional[Text]
    """
    Convert a bytes (or text) path to text (unicode in Python 2) for display
    and logging purposes.

    This function should never error out. Also, this function is mainly needed
    for Python 2 since in Python 3 str paths are already text.
    """
    if path is None:
        return None
    if isinstance(path, text_type):
        return path
    # Otherwise, path is a bytes object (str in Python 2).
    try:
        display_path = path.decode(sys.getfilesystemencoding(), 'strict')
    except UnicodeDecodeError:
        # Include the full bytes to make troubleshooting easier, even though
        # it may not be very human readable.
        if PY2:
            # Convert the bytes to a readable str representation using
            # repr(), and then convert the str to unicode.
            #   Also, we add the prefix "b" to the repr() return value both
            # to make the Python 2 output look like the Python 3 output, and
            # to signal to the user that this is a bytes representation.
            display_path = str_to_display('b{!r}'.format(path))
        else:
            # Silence the "F821 undefined name 'ascii'" flake8 error since
            # in Python 3 ascii() is a built-in.
            display_path = ascii(path)  # noqa: F821

    return display_path


def display_path(path):
    # type: (Union[str, Text]) -> str
    """Gives the display value for a given path, making it relative to cwd
    if possible."""
    path = os.path.normcase(os.path.abspath(path))
    if sys.version_info[0] == 2:
        path = path.decode(sys.getfilesystemencoding(), 'replace')
        path = path.encode(sys.getdefaultencoding(), 'replace')
    if path.startswith(os.getcwd() + os.path.sep):
        path = '.' + path[len(os.getcwd()):]
    return path


def backup_dir(dir, ext='.bak'):
    # type: (str, str) -> str
    """Figure out the name of a directory to back up the given dir to
    (adding .bak, .bak2, etc)"""
    n = 1
    extension = ext
    while os.path.exists(dir + extension):
        n += 1
        extension = ext + str(n)
    return dir + extension


def ask_path_exists(message, options):
    # type: (str, Iterable[str]) -> str
    for action in os.environ.get('PIP_EXISTS_ACTION', '').split():
        if action in options:
            return action
    return ask(message, options)


def _check_no_input(message):
    # type: (str) -> None
    """Raise an error if no input is allowed."""
    if os.environ.get('PIP_NO_INPUT'):
        raise Exception(
            'No input was expected ($PIP_NO_INPUT set); question: %s' %
            message
        )


def ask(message, options):
    # type: (str, Iterable[str]) -> str
    """Ask the message interactively, with the given possible responses"""
    while 1:
        _check_no_input(message)
        response = input(message)
        response = response.strip().lower()
        if response not in options:
            print(
                'Your response (%r) was not one of the expected responses: '
                '%s' % (response, ', '.join(options))
            )
        else:
            return response


def ask_input(message):
    # type: (str) -> str
    """Ask for input interactively."""
    _check_no_input(message)
    return input(message)


def ask_password(message):
    # type: (str) -> str
    """Ask for a password interactively."""
    _check_no_input(message)
    return getpass.getpass(message)


def format_size(bytes):
    # type: (float) -> str
    if bytes > 1000 * 1000:
        return '%.1fMB' % (bytes / 1000.0 / 1000)
    elif bytes > 10 * 1000:
        return '%ikB' % (bytes / 1000)
    elif bytes > 1000:
        return '%.1fkB' % (bytes / 1000.0)
    else:
        return '%ibytes' % bytes


def is_installable_dir(path):
    # type: (str) -> bool
    """Is path is a directory containing setup.py or pyproject.toml?
    """
    if not os.path.isdir(path):
        return False
    setup_py = os.path.join(path, 'setup.py')
    if os.path.isfile(setup_py):
        return True
    pyproject_toml = os.path.join(path, 'pyproject.toml')
    if os.path.isfile(pyproject_toml):
        return True
    return False


def is_svn_page(html):
    # type: (Union[str, Text]) -> Optional[Match[Union[str, Text]]]
    """
    Returns true if the page appears to be the index page of an svn repository
    """
    return (re.search(r'<title>[^<]*Revision \d+:', html) and
            re.search(r'Powered by (?:<a[^>]*?>)?Subversion', html, re.I))


def file_contents(filename):
    # type: (str) -> Text
    with open(filename, 'rb') as fp:
        return fp.read().decode('utf-8')


def read_chunks(file, size=io.DEFAULT_BUFFER_SIZE):
    """Yield pieces of data from a file-like object until EOF."""
    while True:
        chunk = file.read(size)
        if not chunk:
            break
        yield chunk


def split_leading_dir(path):
    # type: (Union[str, Text]) -> List[Union[str, Text]]
    path = path.lstrip('/').lstrip('\\')
    if '/' in path and (('\\' in path and path.find('/') < path.find('\\')) or
                        '\\' not in path):
        return path.split('/', 1)
    elif '\\' in path:
        return path.split('\\', 1)
    else:
        return [path, '']


def has_leading_dir(paths):
    # type: (Iterable[Union[str, Text]]) -> bool
    """Returns true if all the paths have the same leading path name
    (i.e., everything is in one subdirectory in an archive)"""
    common_prefix = None
    for path in paths:
        prefix, rest = split_leading_dir(path)
        if not prefix:
            return False
        elif common_prefix is None:
            common_prefix = prefix
        elif prefix != common_prefix:
            return False
    return True


def normalize_path(path, resolve_symlinks=True):
    # type: (str, bool) -> str
    """
    Convert a path to its canonical, case-normalized, absolute version.

    """
    path = expanduser(path)
    if resolve_symlinks:
        path = os.path.realpath(path)
    else:
        path = os.path.abspath(path)
    return os.path.normcase(path)


def splitext(path):
    # type: (str) -> Tuple[str, str]
    """Like os.path.splitext, but take off .tar too"""
    base, ext = posixpath.splitext(path)
    if base.lower().endswith('.tar'):
        ext = base[-4:] + ext
        base = base[:-4]
    return base, ext


def renames(old, new):
    # type: (str, str) -> None
    """Like os.renames(), but handles renaming across devices."""
    # Implementation borrowed from os.renames().
    head, tail = os.path.split(new)
    if head and tail and not os.path.exists(head):
        os.makedirs(head)

    shutil.move(old, new)

    head, tail = os.path.split(old)
    if head and tail:
        try:
            os.removedirs(head)
        except OSError:
            pass


def is_local(path):
    # type: (str) -> bool
    """
    Return True if path is within sys.prefix, if we're running in a virtualenv.

    If we're not in a virtualenv, all paths are considered "local."

    """
    if not running_under_virtualenv():
        return True
    return normalize_path(path).startswith(normalize_path(sys.prefix))


def dist_is_local(dist):
    # type: (Distribution) -> bool
    """
    Return True if given Distribution object is installed locally
    (i.e. within current virtualenv).

    Always True if we're not in a virtualenv.

    """
    return is_local(dist_location(dist))


def dist_in_usersite(dist):
    # type: (Distribution) -> bool
    """
    Return True if given Distribution is installed in user site.
    """
    norm_path = normalize_path(dist_location(dist))
    return norm_path.startswith(normalize_path(user_site))


def dist_in_site_packages(dist):
    # type: (Distribution) -> bool
    """
    Return True if given Distribution is installed in
    sysconfig.get_python_lib().
    """
    return normalize_path(
        dist_location(dist)
    ).startswith(normalize_path(site_packages))


def dist_is_editable(dist):
    # type: (Distribution) -> bool
    """
    Return True if given Distribution is an editable install.
    """
    for path_item in sys.path:
        egg_link = os.path.join(path_item, dist.project_name + '.egg-link')
        if os.path.isfile(egg_link):
            return True
    return False


def get_installed_distributions(
        local_only=True,  # type: bool
        skip=stdlib_pkgs,  # type: Container[str]
        include_editables=True,  # type: bool
        editables_only=False,  # type: bool
        user_only=False,  # type: bool
        paths=None  # type: Optional[List[str]]
):
    # type: (...) -> List[Distribution]
    """
    Return a list of installed Distribution objects.

    If ``local_only`` is True (default), only return installations
    local to the current virtualenv, if in a virtualenv.

    ``skip`` argument is an iterable of lower-case project names to
    ignore; defaults to stdlib_pkgs

    If ``include_editables`` is False, don't report editables.

    If ``editables_only`` is True , only report editables.

    If ``user_only`` is True , only report installations in the user
    site directory.

    If ``paths`` is set, only report the distributions present at the
    specified list of locations.
    """
    if paths:
        working_set = pkg_resources.WorkingSet(paths)
    else:
        working_set = pkg_resources.working_set

    if local_only:
        local_test = dist_is_local
    else:
        def local_test(d):
            return True

    if include_editables:
        def editable_test(d):
            return True
    else:
        def editable_test(d):
            return not dist_is_editable(d)

    if editables_only:
        def editables_only_test(d):
            return dist_is_editable(d)
    else:
        def editables_only_test(d):
            return True

    if user_only:
        user_test = dist_in_usersite
    else:
        def user_test(d):
            return True

    # because of pkg_resources vendoring, mypy cannot find stub in typeshed
    return [d for d in working_set  # type: ignore
            if local_test(d) and
            d.key not in skip and
            editable_test(d) and
            editables_only_test(d) and
            user_test(d)
            ]


def egg_link_path(dist):
    # type: (Distribution) -> Optional[str]
    """
    Return the path for the .egg-link file if it exists, otherwise, None.

    There's 3 scenarios:
    1) not in a virtualenv
       try to find in site.USER_SITE, then site_packages
    2) in a no-global virtualenv
       try to find in site_packages
    3) in a yes-global virtualenv
       try to find in site_packages, then site.USER_SITE
       (don't look in global location)

    For #1 and #3, there could be odd cases, where there's an egg-link in 2
    locations.

    This method will just return the first one found.
    """
    sites = []
    if running_under_virtualenv():
        if virtualenv_no_global():
            sites.append(site_packages)
        else:
            sites.append(site_packages)
            if user_site:
                sites.append(user_site)
    else:
        if user_site:
            sites.append(user_site)
        sites.append(site_packages)

    for site in sites:
        egglink = os.path.join(site, dist.project_name) + '.egg-link'
        if os.path.isfile(egglink):
            return egglink
    return None


def dist_location(dist):
    # type: (Distribution) -> str
    """
    Get the site-packages location of this distribution. Generally
    this is dist.location, except in the case of develop-installed
    packages, where dist.location is the source code location, and we
    want to know where the egg-link file is.

    """
    egg_link = egg_link_path(dist)
    if egg_link:
        return egg_link
    return dist.location


def current_umask():
    """Get the current umask which involves having to set it temporarily."""
    mask = os.umask(0)
    os.umask(mask)
    return mask


def unzip_file(filename, location, flatten=True):
    # type: (str, str, bool) -> None
    """
    Unzip the file (with path `filename`) to the destination `location`.  All
    files are written based on system defaults and umask (i.e. permissions are
    not preserved), except that regular file members with any execute
    permissions (user, group, or world) have "chmod +x" applied after being
    written. Note that for windows, any execute changes using os.chmod are
    no-ops per the python docs.
    """
    ensure_dir(location)
    zipfp = open(filename, 'rb')
    try:
        zip = zipfile.ZipFile(zipfp, allowZip64=True)
        leading = has_leading_dir(zip.namelist()) and flatten
        for info in zip.infolist():
            name = info.filename
            fn = name
            if leading:
                fn = split_leading_dir(name)[1]
            fn = os.path.join(location, fn)
            dir = os.path.dirname(fn)
            if fn.endswith('/') or fn.endswith('\\'):
                # A directory
                ensure_dir(fn)
            else:
                ensure_dir(dir)
                # Don't use read() to avoid allocating an arbitrarily large
                # chunk of memory for the file's content
                fp = zip.open(name)
                try:
                    with open(fn, 'wb') as destfp:
                        shutil.copyfileobj(fp, destfp)
                finally:
                    fp.close()
                    mode = info.external_attr >> 16
                    # if mode and regular file and any execute permissions for
                    # user/group/world?
                    if mode and stat.S_ISREG(mode) and mode & 0o111:
                        # make dest file have execute for user/group/world
                        # (chmod +x) no-op on windows per python docs
                        os.chmod(fn, (0o777 - current_umask() | 0o111))
    finally:
        zipfp.close()


def untar_file(filename, location):
    # type: (str, str) -> None
    """
    Untar the file (with path `filename`) to the destination `location`.
    All files are written based on system defaults and umask (i.e. permissions
    are not preserved), except that regular file members with any execute
    permissions (user, group, or world) have "chmod +x" applied after being
    written.  Note that for windows, any execute changes using os.chmod are
    no-ops per the python docs.
    """
    ensure_dir(location)
    if filename.lower().endswith('.gz') or filename.lower().endswith('.tgz'):
        mode = 'r:gz'
    elif filename.lower().endswith(BZ2_EXTENSIONS):
        mode = 'r:bz2'
    elif filename.lower().endswith(XZ_EXTENSIONS):
        mode = 'r:xz'
    elif filename.lower().endswith('.tar'):
        mode = 'r'
    else:
        logger.warning(
            'Cannot determine compression type for file %s', filename,
        )
        mode = 'r:*'
    tar = tarfile.open(filename, mode)
    try:
        leading = has_leading_dir([
            member.name for member in tar.getmembers()
        ])
        for member in tar.getmembers():
            fn = member.name
            if leading:
                # https://github.com/python/mypy/issues/1174
                fn = split_leading_dir(fn)[1]  # type: ignore
            path = os.path.join(location, fn)
            if member.isdir():
                ensure_dir(path)
            elif member.issym():
                try:
                    # https://github.com/python/typeshed/issues/2673
                    tar._extract_member(member, path)  # type: ignore
                except Exception as exc:
                    # Some corrupt tar files seem to produce this
                    # (specifically bad symlinks)
                    logger.warning(
                        'In the tar file %s the member %s is invalid: %s',
                        filename, member.name, exc,
                    )
                    continue
            else:
                try:
                    fp = tar.extractfile(member)
                except (KeyError, AttributeError) as exc:
                    # Some corrupt tar files seem to produce this
                    # (specifically bad symlinks)
                    logger.warning(
                        'In the tar file %s the member %s is invalid: %s',
                        filename, member.name, exc,
                    )
                    continue
                ensure_dir(os.path.dirname(path))
                with open(path, 'wb') as destfp:
                    shutil.copyfileobj(fp, destfp)
                fp.close()
                # Update the timestamp (useful for cython compiled files)
                # https://github.com/python/typeshed/issues/2673
                tar.utime(member, path)  # type: ignore
                # member have any execute permissions for user/group/world?
                if member.mode & 0o111:
                    # make dest file have execute for user/group/world
                    # no-op on windows per python docs
                    os.chmod(path, (0o777 - current_umask() | 0o111))
    finally:
        tar.close()


def unpack_file(
    filename,  # type: str
    location,  # type: str
    content_type,  # type: Optional[str]
    link  # type: Optional[Link]
):
    # type: (...) -> None
    filename = os.path.realpath(filename)
    if (content_type == 'application/zip' or
            filename.lower().endswith(ZIP_EXTENSIONS) or
            zipfile.is_zipfile(filename)):
        unzip_file(
            filename,
            location,
            flatten=not filename.endswith('.whl')
        )
    elif (content_type == 'application/x-gzip' or
            tarfile.is_tarfile(filename) or
            filename.lower().endswith(
                TAR_EXTENSIONS + BZ2_EXTENSIONS + XZ_EXTENSIONS)):
        untar_file(filename, location)
    elif (content_type and content_type.startswith('text/html') and
            is_svn_page(file_contents(filename))):
        # We don't really care about this
        from pip._internal.vcs.subversion import Subversion
        url = 'svn+' + link.url
        Subversion().unpack(location, url=url)
    else:
        # FIXME: handle?
        # FIXME: magic signatures?
        logger.critical(
            'Cannot unpack file %s (downloaded from %s, content-type: %s); '
            'cannot detect archive format',
            filename, location, content_type,
        )
        raise InstallationError(
            'Cannot determine archive format of %s' % location
        )


def format_command_args(args):
    # type: (List[str]) -> str
    """
    Format command arguments for display.
    """
    return ' '.join(shlex_quote(arg) for arg in args)


def make_subprocess_output_error(
    cmd_args,     # type: List[str]
    cwd,          # type: Optional[str]
    lines,        # type: List[Text]
    exit_status,  # type: int
):
    # type: (...) -> Text
    """
    Create and return the error message to use to log a subprocess error
    with command output.

    :param lines: A list of lines, each ending with a newline.
    """
    command = format_command_args(cmd_args)
    # Convert `command` and `cwd` to text (unicode in Python 2) so we can use
    # them as arguments in the unicode format string below. This avoids
    # "UnicodeDecodeError: 'ascii' codec can't decode byte ..." in Python 2
    # if either contains a non-ascii character.
    command_display = str_to_display(command, desc='command bytes')
    cwd_display = path_to_display(cwd)

    # We know the joined output value ends in a newline.
    output = ''.join(lines)
    msg = (
        # Use a unicode string to avoid "UnicodeEncodeError: 'ascii'
        # codec can't encode character ..." in Python 2 when a format
        # argument (e.g. `output`) has a non-ascii character.
        u'Command errored out with exit status {exit_status}:\n'
        ' command: {command_display}\n'
        '     cwd: {cwd_display}\n'
        'Complete output ({line_count} lines):\n{output}{divider}'
    ).format(
        exit_status=exit_status,
        command_display=command_display,
        cwd_display=cwd_display,
        line_count=len(lines),
        output=output,
        divider=LOG_DIVIDER,
    )
    return msg


def call_subprocess(
    cmd,  # type: List[str]
    show_stdout=False,  # type: bool
    cwd=None,  # type: Optional[str]
    on_returncode='raise',  # type: str
    extra_ok_returncodes=None,  # type: Optional[Iterable[int]]
    command_desc=None,  # type: Optional[str]
    extra_environ=None,  # type: Optional[Mapping[str, Any]]
    unset_environ=None,  # type: Optional[Iterable[str]]
    spinner=None  # type: Optional[SpinnerInterface]
):
    # type: (...) -> Text
    """
    Args:
      show_stdout: if true, use INFO to log the subprocess's stderr and
        stdout streams.  Otherwise, use DEBUG.  Defaults to False.
      extra_ok_returncodes: an iterable of integer return codes that are
        acceptable, in addition to 0. Defaults to None, which means [].
      unset_environ: an iterable of environment variable names to unset
        prior to calling subprocess.Popen().
    """
    if extra_ok_returncodes is None:
        extra_ok_returncodes = []
    if unset_environ is None:
        unset_environ = []
    # Most places in pip use show_stdout=False. What this means is--
    #
    # - We connect the child's output (combined stderr and stdout) to a
    #   single pipe, which we read.
    # - We log this output to stderr at DEBUG level as it is received.
    # - If DEBUG logging isn't enabled (e.g. if --verbose logging wasn't
    #   requested), then we show a spinner so the user can still see the
    #   subprocess is in progress.
    # - If the subprocess exits with an error, we log the output to stderr
    #   at ERROR level if it hasn't already been displayed to the console
    #   (e.g. if --verbose logging wasn't enabled).  This way we don't log
    #   the output to the console twice.
    #
    # If show_stdout=True, then the above is still done, but with DEBUG
    # replaced by INFO.
    if show_stdout:
        # Then log the subprocess output at INFO level.
        log_subprocess = subprocess_logger.info
        used_level = std_logging.INFO
    else:
        # Then log the subprocess output using DEBUG.  This also ensures
        # it will be logged to the log file (aka user_log), if enabled.
        log_subprocess = subprocess_logger.debug
        used_level = std_logging.DEBUG

    # Whether the subprocess will be visible in the console.
    showing_subprocess = subprocess_logger.getEffectiveLevel() <= used_level

    # Only use the spinner if we're not showing the subprocess output
    # and we have a spinner.
    use_spinner = not showing_subprocess and spinner is not None

    if command_desc is None:
        command_desc = format_command_args(cmd)

    log_subprocess("Running command %s", command_desc)
    env = os.environ.copy()
    if extra_environ:
        env.update(extra_environ)
    for name in unset_environ:
        env.pop(name, None)
    try:
        proc = subprocess.Popen(
            cmd, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, cwd=cwd, env=env,
        )
        proc.stdin.close()
    except Exception as exc:
        subprocess_logger.critical(
            "Error %s while executing command %s", exc, command_desc,
        )
        raise
    all_output = []
    while True:
        # The "line" value is a unicode string in Python 2.
        line = console_to_str(proc.stdout.readline())
        if not line:
            break
        line = line.rstrip()
        all_output.append(line + '\n')

        # Show the line immediately.
        log_subprocess(line)
        # Update the spinner.
        if use_spinner:
            spinner.spin()
    try:
        proc.wait()
    finally:
        if proc.stdout:
            proc.stdout.close()
    proc_had_error = (
        proc.returncode and proc.returncode not in extra_ok_returncodes
    )
    if use_spinner:
        if proc_had_error:
            spinner.finish("error")
        else:
            spinner.finish("done")
    if proc_had_error:
        if on_returncode == 'raise':
            if not showing_subprocess:
                # Then the subprocess streams haven't been logged to the
                # console yet.
                msg = make_subprocess_output_error(
                    cmd_args=cmd,
                    cwd=cwd,
                    lines=all_output,
                    exit_status=proc.returncode,
                )
                subprocess_logger.error(msg)
            exc_msg = (
                'Command errored out with exit status {}: {} '
                'Check the logs for full command output.'
            ).format(proc.returncode, command_desc)
            raise InstallationError(exc_msg)
        elif on_returncode == 'warn':
            subprocess_logger.warning(
                'Command "%s" had error code %s in %s',
                command_desc, proc.returncode, cwd,
            )
        elif on_returncode == 'ignore':
            pass
        else:
            raise ValueError('Invalid value: on_returncode=%s' %
                             repr(on_returncode))
    return ''.join(all_output)


def _make_build_dir(build_dir):
    os.makedirs(build_dir)
    write_delete_marker_file(build_dir)


class FakeFile(object):
    """Wrap a list of lines in an object with readline() to make
    ConfigParser happy."""
    def __init__(self, lines):
        self._gen = (l for l in lines)

    def readline(self):
        try:
            try:
                return next(self._gen)
            except NameError:
                return self._gen.next()
        except StopIteration:
            return ''

    def __iter__(self):
        return self._gen


class StreamWrapper(StringIO):

    @classmethod
    def from_stream(cls, orig_stream):
        cls.orig_stream = orig_stream
        return cls()

    # compileall.compile_dir() needs stdout.encoding to print to stdout
    @property
    def encoding(self):
        return self.orig_stream.encoding


@contextlib.contextmanager
def captured_output(stream_name):
    """Return a context manager used by captured_stdout/stdin/stderr
    that temporarily replaces the sys stream *stream_name* with a StringIO.

    Taken from Lib/support/__init__.py in the CPython repo.
    """
    orig_stdout = getattr(sys, stream_name)
    setattr(sys, stream_name, StreamWrapper.from_stream(orig_stdout))
    try:
        yield getattr(sys, stream_name)
    finally:
        setattr(sys, stream_name, orig_stdout)


def captured_stdout():
    """Capture the output of sys.stdout:

       with captured_stdout() as stdout:
           print('hello')
       self.assertEqual(stdout.getvalue(), 'hello\n')

    Taken from Lib/support/__init__.py in the CPython repo.
    """
    return captured_output('stdout')


def captured_stderr():
    """
    See captured_stdout().
    """
    return captured_output('stderr')


class cached_property(object):
    """A property that is only computed once per instance and then replaces
       itself with an ordinary attribute. Deleting the attribute resets the
       property.

       Source: https://github.com/bottlepy/bottle/blob/0.11.5/bottle.py#L175
    """

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            # We're being accessed from the class itself, not from an object
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


def get_installed_version(dist_name, working_set=None):
    """Get the installed version of dist_name avoiding pkg_resources cache"""
    # Create a requirement that we'll look for inside of setuptools.
    req = pkg_resources.Requirement.parse(dist_name)

    if working_set is None:
        # We want to avoid having this cached, so we need to construct a new
        # working set each time.
        working_set = pkg_resources.WorkingSet()

    # Get the installed distribution from our working set
    dist = working_set.find(req)

    # Check to see if we got an installed distribution or not, if we did
    # we want to return it's version.
    return dist.version if dist else None


def consume(iterator):
    """Consume an iterable at C speed."""
    deque(iterator, maxlen=0)


# Simulates an enum
def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = {value: key for key, value in enums.items()}
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)


def path_to_url(path):
    # type: (Union[str, Text]) -> str
    """
    Convert a path to a file: URL.  The path will be made absolute and have
    quoted path parts.
    """
    path = os.path.normpath(os.path.abspath(path))
    url = urllib_parse.urljoin('file:', urllib_request.pathname2url(path))
    return url


def split_auth_from_netloc(netloc):
    """
    Parse out and remove the auth information from a netloc.

    Returns: (netloc, (username, password)).
    """
    if '@' not in netloc:
        return netloc, (None, None)

    # Split from the right because that's how urllib.parse.urlsplit()
    # behaves if more than one @ is present (which can be checked using
    # the password attribute of urlsplit()'s return value).
    auth, netloc = netloc.rsplit('@', 1)
    if ':' in auth:
        # Split from the left because that's how urllib.parse.urlsplit()
        # behaves if more than one : is present (which again can be checked
        # using the password attribute of the return value)
        user_pass = auth.split(':', 1)
    else:
        user_pass = auth, None

    user_pass = tuple(
        None if x is None else urllib_unquote(x) for x in user_pass
    )

    return netloc, user_pass


def redact_netloc(netloc):
    # type: (str) -> str
    """
    Replace the password in a netloc with "****", if it exists.

    For example, "user:pass@example.com" returns "user:****@example.com".
    """
    netloc, (user, password) = split_auth_from_netloc(netloc)
    if user is None:
        return netloc
    password = '' if password is None else ':****'
    return '{user}{password}@{netloc}'.format(user=urllib_parse.quote(user),
                                              password=password,
                                              netloc=netloc)


def _transform_url(url, transform_netloc):
    """Transform and replace netloc in a url.

    transform_netloc is a function taking the netloc and returning a
    tuple. The first element of this tuple is the new netloc. The
    entire tuple is returned.

    Returns a tuple containing the transformed url as item 0 and the
    original tuple returned by transform_netloc as item 1.
    """
    purl = urllib_parse.urlsplit(url)
    netloc_tuple = transform_netloc(purl.netloc)
    # stripped url
    url_pieces = (
        purl.scheme, netloc_tuple[0], purl.path, purl.query, purl.fragment
    )
    surl = urllib_parse.urlunsplit(url_pieces)
    return surl, netloc_tuple


def _get_netloc(netloc):
    return split_auth_from_netloc(netloc)


def _redact_netloc(netloc):
    return (redact_netloc(netloc),)


def split_auth_netloc_from_url(url):
    # type: (str) -> Tuple[str, str, Tuple[str, str]]
    """
    Parse a url into separate netloc, auth, and url with no auth.

    Returns: (url_without_auth, netloc, (username, password))
    """
    url_without_auth, (netloc, auth) = _transform_url(url, _get_netloc)
    return url_without_auth, netloc, auth


def remove_auth_from_url(url):
    # type: (str) -> str
    """Return a copy of url with 'username:password@' removed."""
    # username/pass params are passed to subversion through flags
    # and are not recognized in the url.
    return _transform_url(url, _get_netloc)[0]


def redact_password_from_url(url):
    # type: (str) -> str
    """Replace the password in a given url with ****."""
    return _transform_url(url, _redact_netloc)[0]


def protect_pip_from_modification_on_windows(modifying_pip):
    """Protection of pip.exe from modification on Windows

    On Windows, any operation modifying pip should be run as:
        python -m pip ...
    """
    pip_names = [
        "pip.exe",
        "pip{}.exe".format(sys.version_info[0]),
        "pip{}.{}.exe".format(*sys.version_info[:2])
    ]

    # See https://github.com/pypa/pip/issues/1299 for more discussion
    should_show_use_python_msg = (
        modifying_pip and
        WINDOWS and
        os.path.basename(sys.argv[0]) in pip_names
    )

    if should_show_use_python_msg:
        new_command = [
            sys.executable, "-m", "pip"
        ] + sys.argv[1:]
        raise CommandError(
            'To modify pip, please run the following command:\n{}'
            .format(" ".join(new_command))
        )
