"""Generate and work with PEP 425 Compatibility Tags."""
from __future__ import absolute_import

import distutils.util
import logging
import platform
import re
import sys
import sysconfig
import warnings
from collections import OrderedDict

import pip._internal.utils.glibc
from pip._internal.utils.compat import get_extension_suffixes
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import (
        Tuple, Callable, List, Optional, Union, Dict
    )

    Pep425Tag = Tuple[str, str, str]

logger = logging.getLogger(__name__)

_osx_arch_pat = re.compile(r'(.+)_(\d+)_(\d+)_(.+)')


def get_config_var(var):
    # type: (str) -> Optional[str]
    try:
        return sysconfig.get_config_var(var)
    except IOError as e:  # Issue #1074
        warnings.warn("{}".format(e), RuntimeWarning)
        return None


def get_abbr_impl():
    # type: () -> str
    """Return abbreviated implementation name."""
    if hasattr(sys, 'pypy_version_info'):
        pyimpl = 'pp'
    elif sys.platform.startswith('java'):
        pyimpl = 'jy'
    elif sys.platform == 'cli':
        pyimpl = 'ip'
    else:
        pyimpl = 'cp'
    return pyimpl


def version_info_to_nodot(version_info):
    # type: (Tuple[int, ...]) -> str
    # Only use up to the first two numbers.
    return ''.join(map(str, version_info[:2]))


def get_impl_ver():
    # type: () -> str
    """Return implementation version."""
    impl_ver = get_config_var("py_version_nodot")
    if not impl_ver or get_abbr_impl() == 'pp':
        impl_ver = ''.join(map(str, get_impl_version_info()))
    return impl_ver


def get_impl_version_info():
    # type: () -> Tuple[int, ...]
    """Return sys.version_info-like tuple for use in decrementing the minor
    version."""
    if get_abbr_impl() == 'pp':
        # as per https://github.com/pypa/pip/issues/2882
        # attrs exist only on pypy
        return (sys.version_info[0],
                sys.pypy_version_info.major,  # type: ignore
                sys.pypy_version_info.minor)  # type: ignore
    else:
        return sys.version_info[0], sys.version_info[1]


def get_impl_tag():
    # type: () -> str
    """
    Returns the Tag for this specific implementation.
    """
    return "{}{}".format(get_abbr_impl(), get_impl_ver())


def get_flag(var, fallback, expected=True, warn=True):
    # type: (str, Callable[..., bool], Union[bool, int], bool) -> bool
    """Use a fallback method for determining SOABI flags if the needed config
    var is unset or unavailable."""
    val = get_config_var(var)
    if val is None:
        if warn:
            logger.debug("Config variable '%s' is unset, Python ABI tag may "
                         "be incorrect", var)
        return fallback()
    return val == expected


def get_abi_tag():
    # type: () -> Optional[str]
    """Return the ABI tag based on SOABI (if available) or emulate SOABI
    (CPython 2, PyPy)."""
    soabi = get_config_var('SOABI')
    impl = get_abbr_impl()
    if not soabi and impl in {'cp', 'pp'} and hasattr(sys, 'maxunicode'):
        d = ''
        m = ''
        u = ''
        is_cpython = (impl == 'cp')
        if get_flag(
                'Py_DEBUG', lambda: hasattr(sys, 'gettotalrefcount'),
                warn=is_cpython):
            d = 'd'
        if sys.version_info < (3, 8) and get_flag(
                'WITH_PYMALLOC', lambda: is_cpython, warn=is_cpython):
            m = 'm'
        if sys.version_info < (3, 3) and get_flag(
                'Py_UNICODE_SIZE', lambda: sys.maxunicode == 0x10ffff,
                expected=4, warn=is_cpython):
            u = 'u'
        abi = '%s%s%s%s%s' % (impl, get_impl_ver(), d, m, u)
    elif soabi and soabi.startswith('cpython-'):
        abi = 'cp' + soabi.split('-')[1]
    elif soabi:
        abi = soabi.replace('.', '_').replace('-', '_')
    else:
        abi = None
    return abi


def _is_running_32bit():
    # type: () -> bool
    return sys.maxsize == 2147483647


def get_platform():
    # type: () -> str
    """Return our platform name 'win32', 'linux_x86_64'"""
    if sys.platform == 'darwin':
        # distutils.util.get_platform() returns the release based on the value
        # of MACOSX_DEPLOYMENT_TARGET on which Python was built, which may
        # be significantly older than the user's current machine.
        release, _, machine = platform.mac_ver()
        split_ver = release.split('.')

        if machine == "x86_64" and _is_running_32bit():
            machine = "i386"
        elif machine == "ppc64" and _is_running_32bit():
            machine = "ppc"

        return 'macosx_{}_{}_{}'.format(split_ver[0], split_ver[1], machine)

    # XXX remove distutils dependency
    result = distutils.util.get_platform().replace('.', '_').replace('-', '_')
    if result == "linux_x86_64" and _is_running_32bit():
        # 32 bit Python program (running on a 64 bit Linux): pip should only
        # install and run 32 bit compiled extensions in that case.
        result = "linux_i686"

    return result


def is_manylinux1_compatible():
    # type: () -> bool
    # Only Linux, and only x86-64 / i686
    if get_platform() not in {"linux_x86_64", "linux_i686"}:
        return False

    # Check for presence of _manylinux module
    try:
        import _manylinux
        return bool(_manylinux.manylinux1_compatible)
    except (ImportError, AttributeError):
        # Fall through to heuristic check below
        pass

    # Check glibc version. CentOS 5 uses glibc 2.5.
    return pip._internal.utils.glibc.have_compatible_glibc(2, 5)


def is_manylinux2010_compatible():
    # type: () -> bool
    # Only Linux, and only x86-64 / i686
    if get_platform() not in {"linux_x86_64", "linux_i686"}:
        return False

    # Check for presence of _manylinux module
    try:
        import _manylinux
        return bool(_manylinux.manylinux2010_compatible)
    except (ImportError, AttributeError):
        # Fall through to heuristic check below
        pass

    # Check glibc version. CentOS 6 uses glibc 2.12.
    return pip._internal.utils.glibc.have_compatible_glibc(2, 12)


def get_darwin_arches(major, minor, machine):
    # type: (int, int, str) -> List[str]
    """Return a list of supported arches (including group arches) for
    the given major, minor and machine architecture of an macOS machine.
    """
    arches = []

    def _supports_arch(major, minor, arch):
        # type: (int, int, str) -> bool
        # Looking at the application support for macOS versions in the chart
        # provided by https://en.wikipedia.org/wiki/OS_X#Versions it appears
        # our timeline looks roughly like:
        #
        # 10.0 - Introduces ppc support.
        # 10.4 - Introduces ppc64, i386, and x86_64 support, however the ppc64
        #        and x86_64 support is CLI only, and cannot be used for GUI
        #        applications.
        # 10.5 - Extends ppc64 and x86_64 support to cover GUI applications.
        # 10.6 - Drops support for ppc64
        # 10.7 - Drops support for ppc
        #
        # Given that we do not know if we're installing a CLI or a GUI
        # application, we must be conservative and assume it might be a GUI
        # application and behave as if ppc64 and x86_64 support did not occur
        # until 10.5.
        #
        # Note: The above information is taken from the "Application support"
        #       column in the chart not the "Processor support" since I believe
        #       that we care about what instruction sets an application can use
        #       not which processors the OS supports.
        if arch == 'ppc':
            return (major, minor) <= (10, 5)
        if arch == 'ppc64':
            return (major, minor) == (10, 5)
        if arch == 'i386':
            return (major, minor) >= (10, 4)
        if arch == 'x86_64':
            return (major, minor) >= (10, 5)
        if arch in groups:
            for garch in groups[arch]:
                if _supports_arch(major, minor, garch):
                    return True
        return False

    groups = OrderedDict([
        ("fat", ("i386", "ppc")),
        ("intel", ("x86_64", "i386")),
        ("fat64", ("x86_64", "ppc64")),
        ("fat32", ("x86_64", "i386", "ppc")),
    ])  # type: Dict[str, Tuple[str, ...]]

    if _supports_arch(major, minor, machine):
        arches.append(machine)

    for garch in groups:
        if machine in groups[garch] and _supports_arch(major, minor, garch):
            arches.append(garch)

    arches.append('universal')

    return arches


def get_all_minor_versions_as_strings(version_info):
    # type: (Tuple[int, ...]) -> List[str]
    versions = []
    major = version_info[:-1]
    # Support all previous minor Python versions.
    for minor in range(version_info[-1], -1, -1):
        versions.append(''.join(map(str, major + (minor,))))
    return versions


def get_supported(
    versions=None,  # type: Optional[List[str]]
    noarch=False,  # type: bool
    platform=None,  # type: Optional[str]
    impl=None,  # type: Optional[str]
    abi=None  # type: Optional[str]
):
    # type: (...) -> List[Pep425Tag]
    """Return a list of supported tags for each version specified in
    `versions`.

    :param versions: a list of string versions, of the form ["33", "32"],
        or None. The first version will be assumed to support our ABI.
    :param platform: specify the exact platform you want valid
        tags for, or None. If None, use the local system platform.
    :param impl: specify the exact implementation you want valid
        tags for, or None. If None, use the local interpreter impl.
    :param abi: specify the exact abi you want valid
        tags for, or None. If None, use the local interpreter abi.
    """
    supported = []

    # Versions must be given with respect to the preference
    if versions is None:
        version_info = get_impl_version_info()
        versions = get_all_minor_versions_as_strings(version_info)

    impl = impl or get_abbr_impl()

    abis = []  # type: List[str]

    abi = abi or get_abi_tag()
    if abi:
        abis[0:0] = [abi]

    abi3s = set()
    for suffix in get_extension_suffixes():
        if suffix.startswith('.abi'):
            abi3s.add(suffix.split('.', 2)[1])

    abis.extend(sorted(list(abi3s)))

    abis.append('none')

    if not noarch:
        arch = platform or get_platform()
        arch_prefix, arch_sep, arch_suffix = arch.partition('_')
        if arch.startswith('macosx'):
            # support macosx-10.6-intel on macosx-10.9-x86_64
            match = _osx_arch_pat.match(arch)
            if match:
                name, major, minor, actual_arch = match.groups()
                tpl = '{}_{}_%i_%s'.format(name, major)
                arches = []
                for m in reversed(range(int(minor) + 1)):
                    for a in get_darwin_arches(int(major), m, actual_arch):
                        arches.append(tpl % (m, a))
            else:
                # arch pattern didn't match (?!)
                arches = [arch]
        elif arch_prefix == 'manylinux2010':
            # manylinux1 wheels run on most manylinux2010 systems with the
            # exception of wheels depending on ncurses. PEP 571 states
            # manylinux1 wheels should be considered manylinux2010 wheels:
            # https://www.python.org/dev/peps/pep-0571/#backwards-compatibility-with-manylinux1-wheels
            arches = [arch, 'manylinux1' + arch_sep + arch_suffix]
        elif platform is None:
            arches = []
            if is_manylinux2010_compatible():
                arches.append('manylinux2010' + arch_sep + arch_suffix)
            if is_manylinux1_compatible():
                arches.append('manylinux1' + arch_sep + arch_suffix)
            arches.append(arch)
        else:
            arches = [arch]

        # Current version, current API (built specifically for our Python):
        for abi in abis:
            for arch in arches:
                supported.append(('%s%s' % (impl, versions[0]), abi, arch))

        # abi3 modules compatible with older version of Python
        for version in versions[1:]:
            # abi3 was introduced in Python 3.2
            if version in {'31', '30'}:
                break
            for abi in abi3s:   # empty set if not Python 3
                for arch in arches:
                    supported.append(("%s%s" % (impl, version), abi, arch))

        # Has binaries, does not use the Python API:
        for arch in arches:
            supported.append(('py%s' % (versions[0][0]), 'none', arch))

    # No abi / arch, but requires our implementation:
    supported.append(('%s%s' % (impl, versions[0]), 'none', 'any'))
    # Tagged specifically as being cross-version compatible
    # (with just the major version specified)
    supported.append(('%s%s' % (impl, versions[0][0]), 'none', 'any'))

    # No abi / arch, generic Python
    for i, version in enumerate(versions):
        supported.append(('py%s' % (version,), 'none', 'any'))
        if i == 0:
            supported.append(('py%s' % (version[0]), 'none', 'any'))

    return supported


implementation_tag = get_impl_tag()
