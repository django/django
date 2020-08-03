import datetime
import functools
import os
import subprocess
import sys
from distutils.version import LooseVersion

# Private, stable API for detecting the Python version. PYXY means "Python X.Y
# or later". So that third-party apps can use these values, each constant
# should remain as long as the oldest supported Django version supports that
# Python version.
PY36 = sys.version_info >= (3, 6)
PY37 = sys.version_info >= (3, 7)
PY38 = sys.version_info >= (3, 8)
PY39 = sys.version_info >= (3, 9)


def get_version(version=None):
    """Return a PEP 440-compliant version number from VERSION."""
    if version is None:
        version = _get_version_from_django()
    _assert(version)
    return get_main_version(version) + _get_sub_version(version)


def get_main_version(version=None):
    """Return main version (X.Y[.Z]) from VERSION."""
    version = get_complete_version(version)
    parts = 2 if version[2] == 0 else 3
    return '.'.join(str(x) for x in version[:parts])


def _get_sub_version(version):
    """
    Return sub version
       sub = .devN - for pre-alpha releases
           | {a|b|rc}N - for alpha, beta, and rc releases
    """
    if _is_pre_alpha_release(version):
        return _create_pre_alpha_sub()

    if _is_final_release(version):
        return ''

    return _create_alpha_beta_or_rc_sub(version)


def _is_pre_alpha_release(version):
    prerelease_name, prerelease_number = version[3: 5]
    return prerelease_name == 'alpha' and prerelease_number == 0


def _is_final_release(version):
    prerelease_name = version[3]
    return prerelease_name == 'final'


def _create_pre_alpha_sub():
    git_changeset = get_git_changeset()
    if git_changeset:
        return '.dev%s' % git_changeset
    else:
        return ''


def _create_alpha_beta_or_rc_sub(version):
    prerelease_name, prerelease_number = version[3: 5]
    return {'alpha': 'a', 'beta': 'b', 'rc': 'rc'}[prerelease_name] + str(prerelease_number)


def get_complete_version(version=None):
    """
    Return a tuple of the django version. If version argument is non-empty,
    check for correctness of the tuple provided.
    """
    if version is None:
        from django import VERSION as version
    else:
        assert len(version) == 5
        assert version[3] in ('alpha', 'beta', 'rc', 'final')

    return version


def _get_version_from_django():
    from django import VERSION
    return VERSION


def _assert(version):
    assert len(version) == 5
    major, minor, micro, prerelease_name, prerelease_number = version
    assert prerelease_name in ('alpha', 'beta', 'rc', 'final')
    try:
        assert int(major) >= 0
        assert int(minor) >= 0
        assert int(micro) >= 0
        assert int(prerelease_number) >= 0
    except ValueError:
        assert False


def get_docs_version(version=None):
    version = get_complete_version(version)
    if version[3] != 'final':
        return 'dev'
    else:
        return '%d.%d' % version[:2]


@functools.lru_cache()
def get_git_changeset():
    """Return a numeric identifier of the latest git changeset.

    The result is the UTC timestamp of the changeset in YYYYMMDDHHMMSS format.
    This value isn't guaranteed to be unique, but collisions are very unlikely,
    so it's sufficient for generating the development version numbers.
    """
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_log = subprocess.run(
        ['git', 'log', '--pretty=format:%ct', '--quiet', '-1', 'HEAD'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=True, cwd=repo_dir, universal_newlines=True,
    )
    timestamp = git_log.stdout
    try:
        timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))
    except ValueError:
        return None
    return timestamp.strftime('%Y%m%d%H%M%S')


def get_version_tuple(version):
    """
    Return a tuple of version numbers (e.g. (1, 2, 3)) from the version
    string (e.g. '1.2.3').
    """
    loose_version = LooseVersion(version)
    version_numbers = []
    for item in loose_version.version:
        if not isinstance(item, int):
            break
        version_numbers.append(item)
    return tuple(version_numbers)
