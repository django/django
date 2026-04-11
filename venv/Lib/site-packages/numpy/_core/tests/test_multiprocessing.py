import sys

import pytest

import numpy as np
from numpy.testing import IS_PYPY, IS_WASM

pytestmark = pytest.mark.thread_unsafe(
    reason="tests in this module are explicitly multi-processed"
)

def bool_array_writer(shm_name, n):
    # writer routine for test_read_write_bool_array
    import time
    from multiprocessing import shared_memory
    shm = shared_memory.SharedMemory(name=shm_name)
    arr = np.ndarray(n, dtype=np.bool_, buffer=shm.buf)
    for i in range(n):
        arr[i] = True
        time.sleep(0.00001)

def bool_array_reader(shm_name, n):
    # reader routine for test_read_write_bool_array
    from multiprocessing import shared_memory
    shm = shared_memory.SharedMemory(name=shm_name)
    arr = np.ndarray(n, dtype=np.bool_, buffer=shm.buf)
    for i in range(n):
        while not arr[i]:
            pass

@pytest.mark.skipif(IS_WASM,
                    reason="WASM does not support _posixshmem")
@pytest.mark.skipif(IS_PYPY and sys.platform == "win32",
                    reason="_winapi does not support UnmapViewOfFile")
def test_read_write_bool_array():
    # See: gh-30389
    #
    # Prior to Python 3.13, boolean scalar singletons (np.True / np.False) were
    # regular reference-counted objects. Due to the double evaluation in
    # PyArrayScalar_RETURN_BOOL_FROM_LONG, concurrent reads and writes of a
    # boolean array could corrupt their refcounts, potentially causing a crash
    # (e.g., `free(): invalid pointer`).
    #
    # This test creates a multi-process race between a writer and a reader to
    # ensure that NumPy does not exhibit such failures.
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import shared_memory
    n = 10000
    shm = shared_memory.SharedMemory(create=True, size=n)
    with ProcessPoolExecutor(max_workers=2) as executor:
        f_writer = executor.submit(bool_array_writer, shm.name, n)
        f_reader = executor.submit(bool_array_reader, shm.name, n)
    shm.unlink()
    f_writer.result()
    f_reader.result()
