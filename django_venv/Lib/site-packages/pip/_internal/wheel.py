"""
Support for installing and building the "wheel" binary package format.
"""
from __future__ import absolute_import

import collections
import compileall
import csv
import hashlib
import logging
import os.path
import re
import shutil
import stat
import sys
import warnings
from base64 import urlsafe_b64encode
from email.parser import Parser

from pip._vendor import pkg_resources
from pip._vendor.distlib.scripts import ScriptMaker
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.six import StringIO

from pip._internal import pep425tags
from pip._internal.download import unpack_url
from pip._internal.exceptions import (
    InstallationError, InvalidWheelFilename, UnsupportedWheel,
)
from pip._internal.locations import distutils_scheme
from pip._internal.models.link import Link
from pip._internal.utils.logging import indent_log
from pip._internal.utils.marker_files import PIP_DELETE_MARKER_FILENAME
from pip._internal.utils.misc import (
    LOG_DIVIDER, call_subprocess, captured_stdout, ensure_dir,
    format_command_args, path_to_url, read_chunks,
)
from pip._internal.utils.setuptools_build import make_setuptools_shim_args
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.utils.ui import open_spinner

if MYPY_CHECK_RUNNING:
    from typing import (
        Dict, List, Optional, Sequence, Mapping, Tuple, IO, Text, Any, Iterable
    )
    from pip._vendor.packaging.requirements import Requirement
    from pip._internal.req.req_install import InstallRequirement
    from pip._internal.download import PipSession
    from pip._internal.index import FormatControl, PackageFinder
    from pip._internal.operations.prepare import (
        RequirementPreparer
    )
    from pip._internal.cache import WheelCache
    from pip._internal.pep425tags import Pep425Tag

    InstalledCSVRow = Tuple[str, ...]


VERSION_COMPATIBLE = (1, 0)


logger = logging.getLogger(__name__)


def normpath(src, p):
    return os.path.relpath(src, p).replace(os.path.sep, '/')


def hash_file(path, blocksize=1 << 20):
    # type: (str, int) -> Tuple[Any, int]
    """Return (hash, length) for path using hashlib.sha256()"""
    h = hashlib.sha256()
    length = 0
    with open(path, 'rb') as f:
        for block in read_chunks(f, size=blocksize):
            length += len(block)
            h.update(block)
    return (h, length)  # type: ignore


def rehash(path, blocksize=1 << 20):
    # type: (str, int) -> Tuple[str, str]
    """Return (encoded_digest, length) for path using hashlib.sha256()"""
    h, length = hash_file(path, blocksize)
    digest = 'sha256=' + urlsafe_b64encode(
        h.digest()
    ).decode('latin1').rstrip('=')
    # unicode/str python2 issues
    return (digest, str(length))  # type: ignore


def open_for_csv(name, mode):
    # type: (str, Text) -> IO
    if sys.version_info[0] < 3:
        nl = {}  # type: Dict[str, Any]
        bin = 'b'
    else:
        nl = {'newline': ''}  # type: Dict[str, Any]
        bin = ''
    return open(name, mode + bin, **nl)


def replace_python_tag(wheelname, new_tag):
    # type: (str, str) -> str
    """Replace the Python tag in a wheel file name with a new value.
    """
    parts = wheelname.split('-')
    parts[-3] = new_tag
    return '-'.join(parts)


def fix_script(path):
    # type: (str) -> Optional[bool]
    """Replace #!python with #!/path/to/python
    Return True if file was changed."""
    # XXX RECORD hashes will need to be updated
    if os.path.isfile(path):
        with open(path, 'rb') as script:
            firstline = script.readline()
            if not firstline.startswith(b'#!python'):
                return False
            exename = sys.executable.encode(sys.getfilesystemencoding())
            firstline = b'#!' + exename + os.linesep.encode("ascii")
            rest = script.read()
        with open(path, 'wb') as script:
            script.write(firstline)
            script.write(rest)
        return True
    return None


dist_info_re = re.compile(r"""^(?P<namever>(?P<name>.+?)(-(?P<ver>.+?))?)
                                \.dist-info$""", re.VERBOSE)


def root_is_purelib(name, wheeldir):
    # type: (str, str) -> bool
    """
    Return True if the extracted wheel in wheeldir should go into purelib.
    """
    name_folded = name.replace("-", "_")
    for item in os.listdir(wheeldir):
        match = dist_info_re.match(item)
        if match and match.group('name') == name_folded:
            with open(os.path.join(wheeldir, item, 'WHEEL')) as wheel:
                for line in wheel:
                    line = line.lower().rstrip()
                    if line == "root-is-purelib: true":
                        return True
    return False


def get_entrypoints(filename):
    # type: (str) -> Tuple[Dict[str, str], Dict[str, str]]
    if not os.path.exists(filename):
        return {}, {}

    # This is done because you can pass a string to entry_points wrappers which
    # means that they may or may not be valid INI files. The attempt here is to
    # strip leading and trailing whitespace in order to make them valid INI
    # files.
    with open(filename) as fp:
        data = StringIO()
        for line in fp:
            data.write(line.strip())
            data.write("\n")
        data.seek(0)

    # get the entry points and then the script names
    entry_points = pkg_resources.EntryPoint.parse_map(data)
    console = entry_points.get('console_scripts', {})
    gui = entry_points.get('gui_scripts', {})

    def _split_ep(s):
        """get the string representation of EntryPoint, remove space and split
        on '='"""
        return str(s).replace(" ", "").split("=")

    # convert the EntryPoint objects into strings with module:function
    console = dict(_split_ep(v) for v in console.values())
    gui = dict(_split_ep(v) for v in gui.values())
    return console, gui


def message_about_scripts_not_on_PATH(scripts):
    # type: (Sequence[str]) -> Optional[str]
    """Determine if any scripts are not on PATH and format a warning.

    Returns a warning message if one or more scripts are not on PATH,
    otherwise None.
    """
    if not scripts:
        return None

    # Group scripts by the path they were installed in
    grouped_by_dir = collections.defaultdict(set)  # type: Dict[str, set]
    for destfile in scripts:
        parent_dir = os.path.dirname(destfile)
        script_name = os.path.basename(destfile)
        grouped_by_dir[parent_dir].add(script_name)

    # We don't want to warn for directories that are on PATH.
    not_warn_dirs = [
        os.path.normcase(i).rstrip(os.sep) for i in
        os.environ.get("PATH", "").split(os.pathsep)
    ]
    # If an executable sits with sys.executable, we don't warn for it.
    #     This covers the case of venv invocations without activating the venv.
    not_warn_dirs.append(os.path.normcase(os.path.dirname(sys.executable)))
    warn_for = {
        parent_dir: scripts for parent_dir, scripts in grouped_by_dir.items()
        if os.path.normcase(parent_dir) not in not_warn_dirs
    }
    if not warn_for:
        return None

    # Format a message
    msg_lines = []
    for parent_dir, scripts in warn_for.items():
        sorted_scripts = sorted(scripts)  # type: List[str]
        if len(sorted_scripts) == 1:
            start_text = "script {} is".format(sorted_scripts[0])
        else:
            start_text = "scripts {} are".format(
                ", ".join(sorted_scripts[:-1]) + " and " + sorted_scripts[-1]
            )

        msg_lines.append(
            "The {} installed in '{}' which is not on PATH."
            .format(start_text, parent_dir)
        )

    last_line_fmt = (
        "Consider adding {} to PATH or, if you prefer "
        "to suppress this warning, use --no-warn-script-location."
    )
    if len(msg_lines) == 1:
        msg_lines.append(last_line_fmt.format("this directory"))
    else:
        msg_lines.append(last_line_fmt.format("these directories"))

    # Returns the formatted multiline message
    return "\n".join(msg_lines)


def sorted_outrows(outrows):
    # type: (Iterable[InstalledCSVRow]) -> List[InstalledCSVRow]
    """
    Return the given rows of a RECORD file in sorted order.

    Each row is a 3-tuple (path, hash, size) and corresponds to a record of
    a RECORD file (see PEP 376 and PEP 427 for details).  For the rows
    passed to this function, the size can be an integer as an int or string,
    or the empty string.
    """
    # Normally, there should only be one row per path, in which case the
    # second and third elements don't come into play when sorting.
    # However, in cases in the wild where a path might happen to occur twice,
    # we don't want the sort operation to trigger an error (but still want
    # determinism).  Since the third element can be an int or string, we
    # coerce each element to a string to avoid a TypeError in this case.
    # For additional background, see--
    # https://github.com/pypa/pip/issues/5868
    return sorted(outrows, key=lambda row: tuple(str(x) for x in row))


def get_csv_rows_for_installed(
    old_csv_rows,  # type: Iterable[List[str]]
    installed,  # type: Dict[str, str]
    changed,  # type: set
    generated,  # type: List[str]
    lib_dir,  # type: str
):
    # type: (...) -> List[InstalledCSVRow]
    """
    :param installed: A map from archive RECORD path to installation RECORD
        path.
    """
    installed_rows = []  # type: List[InstalledCSVRow]
    for row in old_csv_rows:
        if len(row) > 3:
            logger.warning(
                'RECORD line has more than three elements: {}'.format(row)
            )
        # Make a copy because we are mutating the row.
        row = list(row)
        old_path = row[0]
        new_path = installed.pop(old_path, old_path)
        row[0] = new_path
        if new_path in changed:
            digest, length = rehash(new_path)
            row[1] = digest
            row[2] = length
        installed_rows.append(tuple(row))
    for f in generated:
        digest, length = rehash(f)
        installed_rows.append((normpath(f, lib_dir), digest, str(length)))
    for f in installed:
        installed_rows.append((installed[f], '', ''))
    return installed_rows


def move_wheel_files(
    name,  # type: str
    req,  # type: Requirement
    wheeldir,  # type: str
    user=False,  # type: bool
    home=None,  # type: Optional[str]
    root=None,  # type: Optional[str]
    pycompile=True,  # type: bool
    scheme=None,  # type: Optional[Mapping[str, str]]
    isolated=False,  # type: bool
    prefix=None,  # type: Optional[str]
    warn_script_location=True  # type: bool
):
    # type: (...) -> None
    """Install a wheel"""
    # TODO: Investigate and break this up.
    # TODO: Look into moving this into a dedicated class for representing an
    #       installation.

    if not scheme:
        scheme = distutils_scheme(
            name, user=user, home=home, root=root, isolated=isolated,
            prefix=prefix,
        )

    if root_is_purelib(name, wheeldir):
        lib_dir = scheme['purelib']
    else:
        lib_dir = scheme['platlib']

    info_dir = []  # type: List[str]
    data_dirs = []
    source = wheeldir.rstrip(os.path.sep) + os.path.sep

    # Record details of the files moved
    #   installed = files copied from the wheel to the destination
    #   changed = files changed while installing (scripts #! line typically)
    #   generated = files newly generated during the install (script wrappers)
    installed = {}  # type: Dict[str, str]
    changed = set()
    generated = []  # type: List[str]

    # Compile all of the pyc files that we're going to be installing
    if pycompile:
        with captured_stdout() as stdout:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore')
                compileall.compile_dir(source, force=True, quiet=True)
        logger.debug(stdout.getvalue())

    def record_installed(srcfile, destfile, modified=False):
        """Map archive RECORD paths to installation RECORD paths."""
        oldpath = normpath(srcfile, wheeldir)
        newpath = normpath(destfile, lib_dir)
        installed[oldpath] = newpath
        if modified:
            changed.add(destfile)

    def clobber(source, dest, is_base, fixer=None, filter=None):
        ensure_dir(dest)  # common for the 'include' path

        for dir, subdirs, files in os.walk(source):
            basedir = dir[len(source):].lstrip(os.path.sep)
            destdir = os.path.join(dest, basedir)
            if is_base and basedir.split(os.path.sep, 1)[0].endswith('.data'):
                continue
            for s in subdirs:
                destsubdir = os.path.join(dest, basedir, s)
                if is_base and basedir == '' and destsubdir.endswith('.data'):
                    data_dirs.append(s)
                    continue
                elif (is_base and
                        s.endswith('.dist-info') and
                        canonicalize_name(s).startswith(
                            canonicalize_name(req.name))):
                    assert not info_dir, ('Multiple .dist-info directories: ' +
                                          destsubdir + ', ' +
                                          ', '.join(info_dir))
                    info_dir.append(destsubdir)
            for f in files:
                # Skip unwanted files
                if filter and filter(f):
                    continue
                srcfile = os.path.join(dir, f)
                destfile = os.path.join(dest, basedir, f)
                # directory creation is lazy and after the file filtering above
                # to ensure we don't install empty dirs; empty dirs can't be
                # uninstalled.
                ensure_dir(destdir)

                # copyfile (called below) truncates the destination if it
                # exists and then writes the new contents. This is fine in most
                # cases, but can cause a segfault if pip has loaded a shared
                # object (e.g. from pyopenssl through its vendored urllib3)
                # Since the shared object is mmap'd an attempt to call a
                # symbol in it will then cause a segfault. Unlinking the file
                # allows writing of new contents while allowing the process to
                # continue to use the old copy.
                if os.path.exists(destfile):
                    os.unlink(destfile)

                # We use copyfile (not move, copy, or copy2) to be extra sure
                # that we are not moving directories over (copyfile fails for
                # directories) as well as to ensure that we are not copying
                # over any metadata because we want more control over what
                # metadata we actually copy over.
                shutil.copyfile(srcfile, destfile)

                # Copy over the metadata for the file, currently this only
                # includes the atime and mtime.
                st = os.stat(srcfile)
                if hasattr(os, "utime"):
                    os.utime(destfile, (st.st_atime, st.st_mtime))

                # If our file is executable, then make our destination file
                # executable.
                if os.access(srcfile, os.X_OK):
                    st = os.stat(srcfile)
                    permissions = (
                        st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    )
                    os.chmod(destfile, permissions)

                changed = False
                if fixer:
                    changed = fixer(destfile)
                record_installed(srcfile, destfile, changed)

    clobber(source, lib_dir, True)

    assert info_dir, "%s .dist-info directory not found" % req

    # Get the defined entry points
    ep_file = os.path.join(info_dir[0], 'entry_points.txt')
    console, gui = get_entrypoints(ep_file)

    def is_entrypoint_wrapper(name):
        # EP, EP.exe and EP-script.py are scripts generated for
        # entry point EP by setuptools
        if name.lower().endswith('.exe'):
            matchname = name[:-4]
        elif name.lower().endswith('-script.py'):
            matchname = name[:-10]
        elif name.lower().endswith(".pya"):
            matchname = name[:-4]
        else:
            matchname = name
        # Ignore setuptools-generated scripts
        return (matchname in console or matchname in gui)

    for datadir in data_dirs:
        fixer = None
        filter = None
        for subdir in os.listdir(os.path.join(wheeldir, datadir)):
            fixer = None
            if subdir == 'scripts':
                fixer = fix_script
                filter = is_entrypoint_wrapper
            source = os.path.join(wheeldir, datadir, subdir)
            dest = scheme[subdir]
            clobber(source, dest, False, fixer=fixer, filter=filter)

    maker = ScriptMaker(None, scheme['scripts'])

    # Ensure old scripts are overwritten.
    # See https://github.com/pypa/pip/issues/1800
    maker.clobber = True

    # Ensure we don't generate any variants for scripts because this is almost
    # never what somebody wants.
    # See https://bitbucket.org/pypa/distlib/issue/35/
    maker.variants = {''}

    # This is required because otherwise distlib creates scripts that are not
    # executable.
    # See https://bitbucket.org/pypa/distlib/issue/32/
    maker.set_mode = True

    # Simplify the script and fix the fact that the default script swallows
    # every single stack trace.
    # See https://bitbucket.org/pypa/distlib/issue/34/
    # See https://bitbucket.org/pypa/distlib/issue/33/
    def _get_script_text(entry):
        if entry.suffix is None:
            raise InstallationError(
                "Invalid script entry point: %s for req: %s - A callable "
                "suffix is required. Cf https://packaging.python.org/en/"
                "latest/distributing.html#console-scripts for more "
                "information." % (entry, req)
            )
        return maker.script_template % {
            "module": entry.prefix,
            "import_name": entry.suffix.split(".")[0],
            "func": entry.suffix,
        }
    # ignore type, because mypy disallows assigning to a method,
    # see https://github.com/python/mypy/issues/2427
    maker._get_script_text = _get_script_text  # type: ignore
    maker.script_template = r"""# -*- coding: utf-8 -*-
import re
import sys

from %(module)s import %(import_name)s

if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw?|\.exe)?$', '', sys.argv[0])
    sys.exit(%(func)s())
"""

    # Special case pip and setuptools to generate versioned wrappers
    #
    # The issue is that some projects (specifically, pip and setuptools) use
    # code in setup.py to create "versioned" entry points - pip2.7 on Python
    # 2.7, pip3.3 on Python 3.3, etc. But these entry points are baked into
    # the wheel metadata at build time, and so if the wheel is installed with
    # a *different* version of Python the entry points will be wrong. The
    # correct fix for this is to enhance the metadata to be able to describe
    # such versioned entry points, but that won't happen till Metadata 2.0 is
    # available.
    # In the meantime, projects using versioned entry points will either have
    # incorrect versioned entry points, or they will not be able to distribute
    # "universal" wheels (i.e., they will need a wheel per Python version).
    #
    # Because setuptools and pip are bundled with _ensurepip and virtualenv,
    # we need to use universal wheels. So, as a stopgap until Metadata 2.0, we
    # override the versioned entry points in the wheel and generate the
    # correct ones. This code is purely a short-term measure until Metadata 2.0
    # is available.
    #
    # To add the level of hack in this section of code, in order to support
    # ensurepip this code will look for an ``ENSUREPIP_OPTIONS`` environment
    # variable which will control which version scripts get installed.
    #
    # ENSUREPIP_OPTIONS=altinstall
    #   - Only pipX.Y and easy_install-X.Y will be generated and installed
    # ENSUREPIP_OPTIONS=install
    #   - pipX.Y, pipX, easy_install-X.Y will be generated and installed. Note
    #     that this option is technically if ENSUREPIP_OPTIONS is set and is
    #     not altinstall
    # DEFAULT
    #   - The default behavior is to install pip, pipX, pipX.Y, easy_install
    #     and easy_install-X.Y.
    pip_script = console.pop('pip', None)
    if pip_script:
        if "ENSUREPIP_OPTIONS" not in os.environ:
            spec = 'pip = ' + pip_script
            generated.extend(maker.make(spec))

        if os.environ.get("ENSUREPIP_OPTIONS", "") != "altinstall":
            spec = 'pip%s = %s' % (sys.version[:1], pip_script)
            generated.extend(maker.make(spec))

        spec = 'pip%s = %s' % (sys.version[:3], pip_script)
        generated.extend(maker.make(spec))
        # Delete any other versioned pip entry points
        pip_ep = [k for k in console if re.match(r'pip(\d(\.\d)?)?$', k)]
        for k in pip_ep:
            del console[k]
    easy_install_script = console.pop('easy_install', None)
    if easy_install_script:
        if "ENSUREPIP_OPTIONS" not in os.environ:
            spec = 'easy_install = ' + easy_install_script
            generated.extend(maker.make(spec))

        spec = 'easy_install-%s = %s' % (sys.version[:3], easy_install_script)
        generated.extend(maker.make(spec))
        # Delete any other versioned easy_install entry points
        easy_install_ep = [
            k for k in console if re.match(r'easy_install(-\d\.\d)?$', k)
        ]
        for k in easy_install_ep:
            del console[k]

    # Generate the console and GUI entry points specified in the wheel
    if len(console) > 0:
        generated_console_scripts = maker.make_multiple(
            ['%s = %s' % kv for kv in console.items()]
        )
        generated.extend(generated_console_scripts)

        if warn_script_location:
            msg = message_about_scripts_not_on_PATH(generated_console_scripts)
            if msg is not None:
                logger.warning(msg)

    if len(gui) > 0:
        generated.extend(
            maker.make_multiple(
                ['%s = %s' % kv for kv in gui.items()],
                {'gui': True}
            )
        )

    # Record pip as the installer
    installer = os.path.join(info_dir[0], 'INSTALLER')
    temp_installer = os.path.join(info_dir[0], 'INSTALLER.pip')
    with open(temp_installer, 'wb') as installer_file:
        installer_file.write(b'pip\n')
    shutil.move(temp_installer, installer)
    generated.append(installer)

    # Record details of all files installed
    record = os.path.join(info_dir[0], 'RECORD')
    temp_record = os.path.join(info_dir[0], 'RECORD.pip')
    with open_for_csv(record, 'r') as record_in:
        with open_for_csv(temp_record, 'w+') as record_out:
            reader = csv.reader(record_in)
            outrows = get_csv_rows_for_installed(
                reader, installed=installed, changed=changed,
                generated=generated, lib_dir=lib_dir,
            )
            writer = csv.writer(record_out)
            # Sort to simplify testing.
            for row in sorted_outrows(outrows):
                writer.writerow(row)
    shutil.move(temp_record, record)


def wheel_version(source_dir):
    # type: (Optional[str]) -> Optional[Tuple[int, ...]]
    """
    Return the Wheel-Version of an extracted wheel, if possible.

    Otherwise, return None if we couldn't parse / extract it.
    """
    try:
        dist = [d for d in pkg_resources.find_on_path(None, source_dir)][0]

        wheel_data = dist.get_metadata('WHEEL')
        wheel_data = Parser().parsestr(wheel_data)

        version = wheel_data['Wheel-Version'].strip()
        version = tuple(map(int, version.split('.')))
        return version
    except Exception:
        return None


def check_compatibility(version, name):
    # type: (Optional[Tuple[int, ...]], str) -> None
    """
    Raises errors or warns if called with an incompatible Wheel-Version.

    Pip should refuse to install a Wheel-Version that's a major series
    ahead of what it's compatible with (e.g 2.0 > 1.1); and warn when
    installing a version only minor version ahead (e.g 1.2 > 1.1).

    version: a 2-tuple representing a Wheel-Version (Major, Minor)
    name: name of wheel or package to raise exception about

    :raises UnsupportedWheel: when an incompatible Wheel-Version is given
    """
    if not version:
        raise UnsupportedWheel(
            "%s is in an unsupported or invalid wheel" % name
        )
    if version[0] > VERSION_COMPATIBLE[0]:
        raise UnsupportedWheel(
            "%s's Wheel-Version (%s) is not compatible with this version "
            "of pip" % (name, '.'.join(map(str, version)))
        )
    elif version > VERSION_COMPATIBLE:
        logger.warning(
            'Installing from a newer Wheel-Version (%s)',
            '.'.join(map(str, version)),
        )


def format_tag(file_tag):
    # type: (Tuple[str, ...]) -> str
    """
    Format three tags in the form "<python_tag>-<abi_tag>-<platform_tag>".

    :param file_tag: A 3-tuple of tags (python_tag, abi_tag, platform_tag).
    """
    return '-'.join(file_tag)


class Wheel(object):
    """A wheel file"""

    # TODO: Maybe move the class into the models sub-package
    # TODO: Maybe move the install code into this class

    wheel_file_re = re.compile(
        r"""^(?P<namever>(?P<name>.+?)-(?P<ver>.*?))
        ((-(?P<build>\d[^-]*?))?-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)
        \.whl|\.dist-info)$""",
        re.VERBOSE
    )

    def __init__(self, filename):
        # type: (str) -> None
        """
        :raises InvalidWheelFilename: when the filename is invalid for a wheel
        """
        wheel_info = self.wheel_file_re.match(filename)
        if not wheel_info:
            raise InvalidWheelFilename(
                "%s is not a valid wheel filename." % filename
            )
        self.filename = filename
        self.name = wheel_info.group('name').replace('_', '-')
        # we'll assume "_" means "-" due to wheel naming scheme
        # (https://github.com/pypa/pip/issues/1150)
        self.version = wheel_info.group('ver').replace('_', '-')
        self.build_tag = wheel_info.group('build')
        self.pyversions = wheel_info.group('pyver').split('.')
        self.abis = wheel_info.group('abi').split('.')
        self.plats = wheel_info.group('plat').split('.')

        # All the tag combinations from this file
        self.file_tags = {
            (x, y, z) for x in self.pyversions
            for y in self.abis for z in self.plats
        }

    def get_formatted_file_tags(self):
        # type: () -> List[str]
        """
        Return the wheel's tags as a sorted list of strings.
        """
        return sorted(format_tag(tag) for tag in self.file_tags)

    def support_index_min(self, tags=None):
        # type: (Optional[List[Pep425Tag]]) -> Optional[int]
        """
        Return the lowest index that one of the wheel's file_tag combinations
        achieves in the supported_tags list e.g. if there are 8 supported tags,
        and one of the file tags is first in the list, then return 0.  Returns
        None is the wheel is not supported.
        """
        if tags is None:  # for mock
            tags = pep425tags.get_supported()
        indexes = [tags.index(c) for c in self.file_tags if c in tags]
        return min(indexes) if indexes else None

    def supported(self, tags=None):
        # type: (Optional[List[Pep425Tag]]) -> bool
        """Is this wheel supported on this system?"""
        if tags is None:  # for mock
            tags = pep425tags.get_supported()
        return bool(set(tags).intersection(self.file_tags))


def _contains_egg_info(
        s, _egg_info_re=re.compile(r'([a-z0-9_.]+)-([a-z0-9_.!+-]+)', re.I)):
    """Determine whether the string looks like an egg_info.

    :param s: The string to parse. E.g. foo-2.1
    """
    return bool(_egg_info_re.search(s))


def should_use_ephemeral_cache(
    req,  # type: InstallRequirement
    format_control,  # type: FormatControl
    autobuilding,  # type: bool
    cache_available  # type: bool
):
    # type: (...) -> Optional[bool]
    """
    Return whether to build an InstallRequirement object using the
    ephemeral cache.

    :param cache_available: whether a cache directory is available for the
        autobuilding=True case.

    :return: True or False to build the requirement with ephem_cache=True
        or False, respectively; or None not to build the requirement.
    """
    if req.constraint:
        return None
    if req.is_wheel:
        if not autobuilding:
            logger.info(
                'Skipping %s, due to already being wheel.', req.name,
            )
        return None
    if not autobuilding:
        return False

    if req.editable or not req.source_dir:
        return None

    if "binary" not in format_control.get_allowed_formats(
            canonicalize_name(req.name)):
        logger.info(
            "Skipping bdist_wheel for %s, due to binaries "
            "being disabled for it.", req.name,
        )
        return None

    if req.link and not req.link.is_artifact:
        # VCS checkout. Build wheel just for this run.
        return True

    link = req.link
    base, ext = link.splitext()
    if cache_available and _contains_egg_info(base):
        return False

    # Otherwise, build the wheel just for this run using the ephemeral
    # cache since we are either in the case of e.g. a local directory, or
    # no cache directory is available to use.
    return True


def format_command_result(
    command_args,  # type: List[str]
    command_output,  # type: str
):
    # type: (...) -> str
    """
    Format command information for logging.
    """
    command_desc = format_command_args(command_args)
    text = 'Command arguments: {}\n'.format(command_desc)

    if not command_output:
        text += 'Command output: None'
    elif logger.getEffectiveLevel() > logging.DEBUG:
        text += 'Command output: [use --verbose to show]'
    else:
        if not command_output.endswith('\n'):
            command_output += '\n'
        text += 'Command output:\n{}{}'.format(command_output, LOG_DIVIDER)

    return text


def get_legacy_build_wheel_path(
    names,  # type: List[str]
    temp_dir,  # type: str
    req,  # type: InstallRequirement
    command_args,  # type: List[str]
    command_output,  # type: str
):
    # type: (...) -> Optional[str]
    """
    Return the path to the wheel in the temporary build directory.
    """
    # Sort for determinism.
    names = sorted(names)
    if not names:
        msg = (
            'Legacy build of wheel for {!r} created no files.\n'
        ).format(req.name)
        msg += format_command_result(command_args, command_output)
        logger.warning(msg)
        return None

    if len(names) > 1:
        msg = (
            'Legacy build of wheel for {!r} created more than one file.\n'
            'Filenames (choosing first): {}\n'
        ).format(req.name, names)
        msg += format_command_result(command_args, command_output)
        logger.warning(msg)

    return os.path.join(temp_dir, names[0])


class WheelBuilder(object):
    """Build wheels from a RequirementSet."""

    def __init__(
        self,
        finder,  # type: PackageFinder
        preparer,  # type: RequirementPreparer
        wheel_cache,  # type: WheelCache
        build_options=None,  # type: Optional[List[str]]
        global_options=None,  # type: Optional[List[str]]
        no_clean=False  # type: bool
    ):
        # type: (...) -> None
        self.finder = finder
        self.preparer = preparer
        self.wheel_cache = wheel_cache

        self._wheel_dir = preparer.wheel_download_dir

        self.build_options = build_options or []
        self.global_options = global_options or []
        self.no_clean = no_clean

    def _build_one(self, req, output_dir, python_tag=None):
        """Build one wheel.

        :return: The filename of the built wheel, or None if the build failed.
        """
        # Install build deps into temporary directory (PEP 518)
        with req.build_env:
            return self._build_one_inside_env(req, output_dir,
                                              python_tag=python_tag)

    def _build_one_inside_env(self, req, output_dir, python_tag=None):
        with TempDirectory(kind="wheel") as temp_dir:
            if req.use_pep517:
                builder = self._build_one_pep517
            else:
                builder = self._build_one_legacy
            wheel_path = builder(req, temp_dir.path, python_tag=python_tag)
            if wheel_path is not None:
                wheel_name = os.path.basename(wheel_path)
                dest_path = os.path.join(output_dir, wheel_name)
                try:
                    wheel_hash, length = hash_file(wheel_path)
                    shutil.move(wheel_path, dest_path)
                    logger.info('Created wheel for %s: '
                                'filename=%s size=%d sha256=%s',
                                req.name, wheel_name, length,
                                wheel_hash.hexdigest())
                    logger.info('Stored in directory: %s', output_dir)
                    return dest_path
                except Exception:
                    pass
            # Ignore return, we can't do anything else useful.
            self._clean_one(req)
            return None

    def _base_setup_args(self, req):
        # NOTE: Eventually, we'd want to also -S to the flags here, when we're
        # isolating. Currently, it breaks Python in virtualenvs, because it
        # relies on site.py to find parts of the standard library outside the
        # virtualenv.
        base_cmd = make_setuptools_shim_args(req.setup_py_path,
                                             unbuffered_output=True)
        return base_cmd + list(self.global_options)

    def _build_one_pep517(self, req, tempd, python_tag=None):
        """Build one InstallRequirement using the PEP 517 build process.

        Returns path to wheel if successfully built. Otherwise, returns None.
        """
        assert req.metadata_directory is not None
        if self.build_options:
            # PEP 517 does not support --build-options
            logger.error('Cannot build wheel for %s using PEP 517 when '
                         '--build-options is present' % (req.name,))
            return None
        try:
            req.spin_message = 'Building wheel for %s (PEP 517)' % (req.name,)
            logger.debug('Destination directory: %s', tempd)
            wheel_name = req.pep517_backend.build_wheel(
                tempd,
                metadata_directory=req.metadata_directory
            )
            if python_tag:
                # General PEP 517 backends don't necessarily support
                # a "--python-tag" option, so we rename the wheel
                # file directly.
                new_name = replace_python_tag(wheel_name, python_tag)
                os.rename(
                    os.path.join(tempd, wheel_name),
                    os.path.join(tempd, new_name)
                )
                # Reassign to simplify the return at the end of function
                wheel_name = new_name
        except Exception:
            logger.error('Failed building wheel for %s', req.name)
            return None
        return os.path.join(tempd, wheel_name)

    def _build_one_legacy(self, req, tempd, python_tag=None):
        """Build one InstallRequirement using the "legacy" build process.

        Returns path to wheel if successfully built. Otherwise, returns None.
        """
        base_args = self._base_setup_args(req)

        spin_message = 'Building wheel for %s (setup.py)' % (req.name,)
        with open_spinner(spin_message) as spinner:
            logger.debug('Destination directory: %s', tempd)
            wheel_args = base_args + ['bdist_wheel', '-d', tempd] \
                + self.build_options

            if python_tag is not None:
                wheel_args += ["--python-tag", python_tag]

            try:
                output = call_subprocess(wheel_args, cwd=req.setup_py_dir,
                                         spinner=spinner)
            except Exception:
                spinner.finish("error")
                logger.error('Failed building wheel for %s', req.name)
                return None
            names = os.listdir(tempd)
            wheel_path = get_legacy_build_wheel_path(
                names=names,
                temp_dir=tempd,
                req=req,
                command_args=wheel_args,
                command_output=output,
            )
            return wheel_path

    def _clean_one(self, req):
        base_args = self._base_setup_args(req)

        logger.info('Running setup.py clean for %s', req.name)
        clean_args = base_args + ['clean', '--all']
        try:
            call_subprocess(clean_args, cwd=req.source_dir)
            return True
        except Exception:
            logger.error('Failed cleaning build dir for %s', req.name)
            return False

    def build(
        self,
        requirements,  # type: Iterable[InstallRequirement]
        session,  # type: PipSession
        autobuilding=False  # type: bool
    ):
        # type: (...) -> List[InstallRequirement]
        """Build wheels.

        :param unpack: If True, replace the sdist we built from with the
            newly built wheel, in preparation for installation.
        :return: True if all the wheels built correctly.
        """
        buildset = []
        format_control = self.finder.format_control
        # Whether a cache directory is available for autobuilding=True.
        cache_available = bool(self._wheel_dir or self.wheel_cache.cache_dir)

        for req in requirements:
            ephem_cache = should_use_ephemeral_cache(
                req, format_control=format_control, autobuilding=autobuilding,
                cache_available=cache_available,
            )
            if ephem_cache is None:
                continue

            buildset.append((req, ephem_cache))

        if not buildset:
            return []

        # Is any wheel build not using the ephemeral cache?
        if any(not ephem_cache for _, ephem_cache in buildset):
            have_directory_for_build = self._wheel_dir or (
                autobuilding and self.wheel_cache.cache_dir
            )
            assert have_directory_for_build

        # TODO by @pradyunsg
        # Should break up this method into 2 separate methods.

        # Build the wheels.
        logger.info(
            'Building wheels for collected packages: %s',
            ', '.join([req.name for (req, _) in buildset]),
        )
        _cache = self.wheel_cache  # shorter name
        with indent_log():
            build_success, build_failure = [], []
            for req, ephem in buildset:
                python_tag = None
                if autobuilding:
                    python_tag = pep425tags.implementation_tag
                    if ephem:
                        output_dir = _cache.get_ephem_path_for_link(req.link)
                    else:
                        output_dir = _cache.get_path_for_link(req.link)
                    try:
                        ensure_dir(output_dir)
                    except OSError as e:
                        logger.warning("Building wheel for %s failed: %s",
                                       req.name, e)
                        build_failure.append(req)
                        continue
                else:
                    output_dir = self._wheel_dir
                wheel_file = self._build_one(
                    req, output_dir,
                    python_tag=python_tag,
                )
                if wheel_file:
                    build_success.append(req)
                    if autobuilding:
                        # XXX: This is mildly duplicative with prepare_files,
                        # but not close enough to pull out to a single common
                        # method.
                        # The code below assumes temporary source dirs -
                        # prevent it doing bad things.
                        if req.source_dir and not os.path.exists(os.path.join(
                                req.source_dir, PIP_DELETE_MARKER_FILENAME)):
                            raise AssertionError(
                                "bad source dir - missing marker")
                        # Delete the source we built the wheel from
                        req.remove_temporary_source()
                        # set the build directory again - name is known from
                        # the work prepare_files did.
                        req.source_dir = req.build_location(
                            self.preparer.build_dir
                        )
                        # Update the link for this.
                        req.link = Link(path_to_url(wheel_file))
                        assert req.link.is_wheel
                        # extract the wheel into the dir
                        unpack_url(
                            req.link, req.source_dir, None, False,
                            session=session,
                        )
                else:
                    build_failure.append(req)

        # notify success/failure
        if build_success:
            logger.info(
                'Successfully built %s',
                ' '.join([req.name for req in build_success]),
            )
        if build_failure:
            logger.info(
                'Failed to build %s',
                ' '.join([req.name for req in build_failure]),
            )
        # Return a list of requirements that failed to build
        return build_failure
