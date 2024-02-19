import os
import shutil
import subprocess
import sys
import pytest

import numpy as np
from numpy.testing import IS_WASM

# This import is copied from random.tests.test_extending
try:
    import cython
    from Cython.Compiler.Version import version as cython_version
except ImportError:
    cython = None
else:
    from numpy._utils import _pep440

    # Cython 0.29.30 is required for Python 3.11 and there are
    # other fixes in the 0.29 series that are needed even for earlier
    # Python versions.
    # Note: keep in sync with the one in pyproject.toml
    required_version = "0.29.30"
    if _pep440.parse(cython_version) < _pep440.Version(required_version):
        # too old or wrong cython, skip the test
        cython = None

pytestmark = pytest.mark.skipif(cython is None, reason="requires cython")


@pytest.fixture(scope='module')
def install_temp(tmpdir_factory):
    # Based in part on test_cython from random.tests.test_extending
    if IS_WASM:
        pytest.skip("No subprocess")

    srcdir = os.path.join(os.path.dirname(__file__), 'examples', 'cython')
    build_dir = tmpdir_factory.mktemp("cython_test") / "build"
    os.makedirs(build_dir, exist_ok=True)
    try:
        subprocess.check_call(["meson", "--version"])
    except FileNotFoundError:
        pytest.skip("No usable 'meson' found")
    if sys.platform == "win32":
        subprocess.check_call(["meson", "setup",
                               "--buildtype=release",
                               "--vsenv", str(srcdir)],
                              cwd=build_dir,
                              )
    else:
        subprocess.check_call(["meson", "setup", str(srcdir)],
                              cwd=build_dir
                              )
    subprocess.check_call(["meson", "compile", "-vv"], cwd=build_dir)

    sys.path.append(str(build_dir))

def test_is_timedelta64_object(install_temp):
    import checks

    assert checks.is_td64(np.timedelta64(1234))
    assert checks.is_td64(np.timedelta64(1234, "ns"))
    assert checks.is_td64(np.timedelta64("NaT", "ns"))

    assert not checks.is_td64(1)
    assert not checks.is_td64(None)
    assert not checks.is_td64("foo")
    assert not checks.is_td64(np.datetime64("now", "s"))


def test_is_datetime64_object(install_temp):
    import checks

    assert checks.is_dt64(np.datetime64(1234, "ns"))
    assert checks.is_dt64(np.datetime64("NaT", "ns"))

    assert not checks.is_dt64(1)
    assert not checks.is_dt64(None)
    assert not checks.is_dt64("foo")
    assert not checks.is_dt64(np.timedelta64(1234))


def test_get_datetime64_value(install_temp):
    import checks

    dt64 = np.datetime64("2016-01-01", "ns")

    result = checks.get_dt64_value(dt64)
    expected = dt64.view("i8")

    assert result == expected


def test_get_timedelta64_value(install_temp):
    import checks

    td64 = np.timedelta64(12345, "h")

    result = checks.get_td64_value(td64)
    expected = td64.view("i8")

    assert result == expected


def test_get_datetime64_unit(install_temp):
    import checks

    dt64 = np.datetime64("2016-01-01", "ns")
    result = checks.get_dt64_unit(dt64)
    expected = 10
    assert result == expected

    td64 = np.timedelta64(12345, "h")
    result = checks.get_dt64_unit(td64)
    expected = 5
    assert result == expected


def test_abstract_scalars(install_temp):
    import checks

    assert checks.is_integer(1)
    assert checks.is_integer(np.int8(1))
    assert checks.is_integer(np.uint64(1))

def test_conv_intp(install_temp):
    import checks

    class myint:
        def __int__(self):
            return 3

    # These conversion passes via `__int__`, not `__index__`:
    assert checks.conv_intp(3.) == 3
    assert checks.conv_intp(myint()) == 3
