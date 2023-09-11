from __future__ import annotations

from ._version import get_versions

__ALL__ = ['version', '__version__', 'full_version', 'git_revision', 'release']


_built_with_meson = False
try:
    from ._version_meson import get_versions
    _built_with_meson = True
except ImportError:
    from ._version import get_versions

vinfo: dict[str, str] = get_versions()
version = vinfo["version"]
__version__ = vinfo.get("closest-tag", vinfo["version"])
git_revision = vinfo['full-revisionid']
release = 'dev0' not in version and '+' not in version
full_version = version
short_version = version.split("+")[0]

del get_versions, vinfo
