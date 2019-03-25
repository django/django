"""Generate and work with PEP 425 Compatibility Tags."""

import distutils.util
import platform
import sys
import sysconfig
import warnings

try:
    from importlib.machinery import get_all_suffixes
except ImportError:
    from imp import get_suffixes as get_all_suffixes


def get_config_var(var):
    try:
        return sysconfig.get_config_var(var)
    except IOError as e:  # pip Issue #1074
        warnings.warn("{0}".format(e), RuntimeWarning)
        return None


def get_abbr_impl():
    """Return abbreviated implementation name."""
    impl = platform.python_implementation()
    if impl == 'PyPy':
        return 'pp'
    elif impl == 'Jython':
        return 'jy'
    elif impl == 'IronPython':
        return 'ip'
    elif impl == 'CPython':
        return 'cp'

    raise LookupError('Unknown Python implementation: ' + impl)


def get_impl_ver():
    """Return implementation version."""
    impl_ver = get_config_var("py_version_nodot")
    if not impl_ver or get_abbr_impl() == 'pp':
        impl_ver = ''.join(map(str, get_impl_version_info()))
    return impl_ver


def get_impl_version_info():
    """Return sys.version_info-like tuple for use in decrementing the minor
    version."""
    if get_abbr_impl() == 'pp':
        # as per https://github.com/pypa/pip/issues/2882
        return (sys.version_info[0], sys.pypy_version_info.major,
                sys.pypy_version_info.minor)
    else:
        return sys.version_info[0], sys.version_info[1]


def get_flag(var, fallback, expected=True, warn=True):
    """Use a fallback method for determining SOABI flags if the needed config
    var is unset or unavailable."""
    val = get_config_var(var)
    if val is None:
        if warn:
            warnings.warn("Config variable '{0}' is unset, Python ABI tag may "
                          "be incorrect".format(var), RuntimeWarning, 2)
        return fallback()
    return val == expected


def get_abi_tag():
    """Return the ABI tag based on SOABI (if available) or emulate SOABI
    (CPython 2, PyPy)."""
    soabi = get_config_var('SOABI')
    impl = get_abbr_impl()
    if not soabi and impl in ('cp', 'pp') and hasattr(sys, 'maxunicode'):
        d = ''
        m = ''
        u = ''
        if get_flag('Py_DEBUG',
                    lambda: hasattr(sys, 'gettotalrefcount'),
                    warn=(impl == 'cp')):
            d = 'd'
        if get_flag('WITH_PYMALLOC',
                    lambda: impl == 'cp',
                    warn=(impl == 'cp')):
            m = 'm'
        if get_flag('Py_UNICODE_SIZE',
                    lambda: sys.maxunicode == 0x10ffff,
                    expected=4,
                    warn=(impl == 'cp' and
                          sys.version_info < (3, 3))) \
                and sys.version_info < (3, 3):
            u = 'u'
        abi = '%s%s%s%s%s' % (impl, get_impl_ver(), d, m, u)
    elif soabi and soabi.startswith('cpython-'):
        abi = 'cp' + soabi.split('-')[1]
    elif soabi:
        abi = soabi.replace('.', '_').replace('-', '_')
    else:
        abi = None
    return abi


def get_platform():
    """Return our platform name 'win32', 'linux_x86_64'"""
    # XXX remove distutils dependency
    result = distutils.util.get_platform().replace('.', '_').replace('-', '_')
    if result == "linux_x86_64" and sys.maxsize == 2147483647:
        # pip pull request #3497
        result = "linux_i686"
    return result


def get_supported(versions=None, supplied_platform=None):
    """Return a list of supported tags for each version specified in
    `versions`.

    :param versions: a list of string versions, of the form ["33", "32"],
        or None. The first version will be assumed to support our ABI.
    """
    supported = []

    # Versions must be given with respect to the preference
    if versions is None:
        versions = []
        version_info = get_impl_version_info()
        major = version_info[:-1]
        # Support all previous minor Python versions.
        for minor in range(version_info[-1], -1, -1):
            versions.append(''.join(map(str, major + (minor,))))

    impl = get_abbr_impl()

    abis = []

    abi = get_abi_tag()
    if abi:
        abis[0:0] = [abi]

    abi3s = set()
    for suffix in get_all_suffixes():
        if suffix[0].startswith('.abi'):
            abi3s.add(suffix[0].split('.', 2)[1])

    abis.extend(sorted(list(abi3s)))

    abis.append('none')

    platforms = []
    if supplied_platform:
        platforms.append(supplied_platform)
    platforms.append(get_platform())

    # Current version, current API (built specifically for our Python):
    for abi in abis:
        for arch in platforms:
            supported.append(('%s%s' % (impl, versions[0]), abi, arch))

    # abi3 modules compatible with older version of Python
    for version in versions[1:]:
        # abi3 was introduced in Python 3.2
        if version in ('31', '30'):
            break
        for abi in abi3s:   # empty set if not Python 3
            for arch in platforms:
                supported.append(("%s%s" % (impl, version), abi, arch))

    # No abi / arch, but requires our implementation:
    for i, version in enumerate(versions):
        supported.append(('%s%s' % (impl, version), 'none', 'any'))
        if i == 0:
            # Tagged specifically as being cross-version compatible
            # (with just the major version specified)
            supported.append(('%s%s' % (impl, versions[0][0]), 'none', 'any'))

    # Major Python version + platform; e.g. binaries not using the Python API
    for arch in platforms:
        supported.append(('py%s' % (versions[0][0]), 'none', arch))

    # No abi / arch, generic Python
    for i, version in enumerate(versions):
        supported.append(('py%s' % (version,), 'none', 'any'))
        if i == 0:
            supported.append(('py%s' % (version[0]), 'none', 'any'))

    return supported
