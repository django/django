import pickle
import subprocess
import sys
import textwrap
from importlib import reload

import pytest

import numpy.exceptions as ex
from numpy.testing import IS_WASM, assert_, assert_equal, assert_raises


@pytest.mark.thread_unsafe(reason="reloads global module")
def test_numpy_reloading():
    # gh-7844. Also check that relevant globals retain their identity.
    import numpy as np
    import numpy._globals

    _NoValue = np._NoValue
    VisibleDeprecationWarning = ex.VisibleDeprecationWarning
    ModuleDeprecationWarning = ex.ModuleDeprecationWarning

    with pytest.warns(UserWarning):
        reload(np)
    assert_(_NoValue is np._NoValue)
    assert_(ModuleDeprecationWarning is ex.ModuleDeprecationWarning)
    assert_(VisibleDeprecationWarning is ex.VisibleDeprecationWarning)

    assert_raises(RuntimeError, reload, numpy._globals)
    with pytest.warns(UserWarning):
        reload(np)
    assert_(_NoValue is np._NoValue)
    assert_(ModuleDeprecationWarning is ex.ModuleDeprecationWarning)
    assert_(VisibleDeprecationWarning is ex.VisibleDeprecationWarning)

def test_novalue():
    import numpy as np
    for proto in range(2, pickle.HIGHEST_PROTOCOL + 1):
        assert_equal(repr(np._NoValue), '<no value>')
        assert_(pickle.loads(pickle.dumps(np._NoValue,
                                          protocol=proto)) is np._NoValue)


@pytest.mark.skipif(IS_WASM, reason="can't start subprocess")
def test_full_reimport():
    # Reimporting numpy like this is not safe due to use of global C state,
    # and has unexpected side effects. Test that an ImportError is raised.
    # When all extension modules are isolated, this should test that clearing
    # sys.modules and reimporting numpy works without error.

    # Test within a new process, to ensure that we do not mess with the
    # global state during the test run (could lead to cryptic test failures).
    # This is generally unsafe, especially, since we also reload the C-modules.
    code = textwrap.dedent(r"""
        import sys
        import numpy as np

        for k in [k for k in sys.modules if k.startswith('numpy')]:
            del sys.modules[k]

        try:
            import numpy as np
        except ImportError as err:
            if str(err) != "cannot load module more than once per process":
                raise SystemExit(f"Unexpected ImportError: {err}")
        else:
            raise SystemExit("DID NOT RAISE ImportError")
        """)
    p = subprocess.run(
        (sys.executable, '-c', code),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        check=False,
    )
    assert p.returncode == 0, p.stdout
