import subprocess
import sys
import textwrap

import pytest

from numpy.testing import IS_WASM


@pytest.mark.skipif(IS_WASM, reason="can't start subprocess")
def test_lazy_load():
    # gh-22045. lazyload doesn't import submodule names into the namespace

    # Test within a new process, to ensure that we do not mess with the
    # global state during the test run (could lead to cryptic test failures).
    # This is generally unsafe, especially, since we also reload the C-modules.
    code = textwrap.dedent(r"""
        import sys
        from importlib.util import LazyLoader, find_spec, module_from_spec

        # create lazy load of numpy as np
        spec = find_spec("numpy")
        module = module_from_spec(spec)
        sys.modules["numpy"] = module
        loader = LazyLoader(spec.loader)
        loader.exec_module(module)
        np = module

        # test a subpackage import
        from numpy.lib import recfunctions  # noqa: F401

        # test triggering the import of the package
        np.ndarray
        """)
    p = subprocess.run(
        (sys.executable, '-c', code),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        check=False,
    )
    assert p.returncode == 0, p.stdout
