import concurrent.futures
import sys
import threading

import pytest

import numpy as np
from numpy._core import _rational_tests
from numpy._core.tests.test_stringdtype import random_unicode_string_list
from numpy.testing import IS_64BIT, IS_WASM
from numpy.testing._private.utils import run_threaded

if IS_WASM:
    pytest.skip(allow_module_level=True, reason="no threading support in wasm")

pytestmark = pytest.mark.thread_unsafe(
    reason="tests in this module are already explicitly multi-threaded"
)

def test_parallel_randomstate():
    # if the coercion cache is enabled and not thread-safe, creating
    # RandomState instances simultaneously leads to a data race
    def func(seed):
        np.random.RandomState(seed)

    run_threaded(func, 500, pass_count=True)

    # seeding and setting state shouldn't race with generating RNG samples
    rng = np.random.RandomState()

    def func(seed):
        base_rng = np.random.RandomState(seed)
        state = base_rng.get_state()
        rng.seed(seed)
        rng.random()
        rng.set_state(state)

    run_threaded(func, 8, pass_count=True)

def test_parallel_ufunc_execution():
    # if the loop data cache or dispatch cache are not thread-safe
    # computing ufuncs simultaneously in multiple threads leads
    # to a data race that causes crashes or spurious exceptions
    for dtype in [np.float32, np.float64, np.int32]:
        for op in [np.random.random((25,)).astype(dtype), dtype(25)]:
            for ufunc in [np.isnan, np.sin]:
                run_threaded(lambda: ufunc(op), 500)

    # see gh-26690
    NUM_THREADS = 50

    a = np.ones(1000)

    def f(b):
        b.wait()
        return a.sum()

    run_threaded(f, NUM_THREADS, pass_barrier=True)


def test_temp_elision_thread_safety():
    amid = np.ones(50000)
    bmid = np.ones(50000)
    alarge = np.ones(1000000)
    blarge = np.ones(1000000)

    def func(count):
        if count % 4 == 0:
            (amid * 2) + bmid
        elif count % 4 == 1:
            (amid + bmid) - 2
        elif count % 4 == 2:
            (alarge * 2) + blarge
        else:
            (alarge + blarge) - 2

    run_threaded(func, 100, pass_count=True)


def test_eigvalsh_thread_safety():
    # if lapack isn't thread safe this will randomly segfault or error
    # see gh-24512
    rng = np.random.RandomState(873699172)
    matrices = (
        rng.random((5, 10, 10, 3, 3)),
        rng.random((5, 10, 10, 3, 3)),
    )

    run_threaded(lambda i: np.linalg.eigvalsh(matrices[i]), 2,
                 pass_count=True)


def test_printoptions_thread_safety():
    # until NumPy 2.1 the printoptions state was stored in globals
    # this verifies that they are now stored in a context variable
    b = threading.Barrier(2)

    def legacy_113():
        np.set_printoptions(legacy='1.13', precision=12)
        b.wait()
        po = np.get_printoptions()
        assert po['legacy'] == '1.13'
        assert po['precision'] == 12
        orig_linewidth = po['linewidth']
        with np.printoptions(linewidth=34, legacy='1.21'):
            po = np.get_printoptions()
            assert po['legacy'] == '1.21'
            assert po['precision'] == 12
            assert po['linewidth'] == 34
        po = np.get_printoptions()
        assert po['linewidth'] == orig_linewidth
        assert po['legacy'] == '1.13'
        assert po['precision'] == 12

    def legacy_125():
        np.set_printoptions(legacy='1.25', precision=7)
        b.wait()
        po = np.get_printoptions()
        assert po['legacy'] == '1.25'
        assert po['precision'] == 7
        orig_linewidth = po['linewidth']
        with np.printoptions(linewidth=6, legacy='1.13'):
            po = np.get_printoptions()
            assert po['legacy'] == '1.13'
            assert po['precision'] == 7
            assert po['linewidth'] == 6
        po = np.get_printoptions()
        assert po['linewidth'] == orig_linewidth
        assert po['legacy'] == '1.25'
        assert po['precision'] == 7

    task1 = threading.Thread(target=legacy_113)
    task2 = threading.Thread(target=legacy_125)

    task1.start()
    task2.start()
    task1.join()
    task2.join()


def test_parallel_reduction():
    # gh-28041
    NUM_THREADS = 50

    x = np.arange(1000)

    def closure(b):
        b.wait()
        np.sum(x)

    run_threaded(closure, NUM_THREADS, pass_barrier=True)


def test_parallel_flat_iterator():
    # gh-28042
    x = np.arange(20).reshape(5, 4).T

    def closure(b):
        b.wait()
        for _ in range(100):
            list(x.flat)

    run_threaded(closure, outer_iterations=100, pass_barrier=True)

    # gh-28143
    def prepare_args():
        return [np.arange(10)]

    def closure(x, b):
        b.wait()
        for _ in range(100):
            y = np.arange(10)
            y.flat[x] = x

    run_threaded(closure, pass_barrier=True, prepare_args=prepare_args)


def test_multithreaded_repeat():
    x0 = np.arange(10)

    def closure(b):
        b.wait()
        for _ in range(100):
            x = np.repeat(x0, 2, axis=0)[::2]

    run_threaded(closure, max_workers=10, pass_barrier=True)


def test_structured_advanced_indexing():
    # Test that copyswap(n) used by integer array indexing is threadsafe
    # for structured datatypes, see gh-15387. This test can behave randomly.

    # Create a deeply nested dtype to make a failure more likely:
    dt = np.dtype([("", "f8")])
    dt = np.dtype([("", dt)] * 2)
    dt = np.dtype([("", dt)] * 2)
    # The array should be large enough to likely run into threading issues
    arr = np.random.uniform(size=(6000, 8)).view(dt)[:, 0]

    rng = np.random.default_rng()

    def func(arr):
        indx = rng.integers(0, len(arr), size=6000, dtype=np.intp)
        arr[indx]

    tpe = concurrent.futures.ThreadPoolExecutor(max_workers=8)
    futures = [tpe.submit(func, arr) for _ in range(10)]
    for f in futures:
        f.result()

    assert arr.dtype is dt


def test_structured_threadsafety2():
    # Nonzero (and some other functions) should be threadsafe for
    # structured datatypes, see gh-15387. This test can behave randomly.
    from concurrent.futures import ThreadPoolExecutor

    # Create a deeply nested dtype to make a failure more likely:
    dt = np.dtype([("", "f8")])
    dt = np.dtype([("", dt)])
    dt = np.dtype([("", dt)] * 2)
    # The array should be large enough to likely run into threading issues
    arr = np.random.uniform(size=(5000, 4)).view(dt)[:, 0]

    def func(arr):
        arr.nonzero()

    tpe = ThreadPoolExecutor(max_workers=8)
    futures = [tpe.submit(func, arr) for _ in range(10)]
    for f in futures:
        f.result()

    assert arr.dtype is dt


def test_stringdtype_multithreaded_access_and_mutation():
    # this test uses an RNG and may crash or cause deadlocks if there is a
    # threading bug
    rng = np.random.default_rng(0x4D3D3D3)

    string_list = random_unicode_string_list()

    def func(arr):
        rnd = rng.random()
        # either write to random locations in the array, compute a ufunc, or
        # re-initialize the array
        if rnd < 0.25:
            num = np.random.randint(0, arr.size)
            arr[num] = arr[num] + "hello"
        elif rnd < 0.5:
            if rnd < 0.375:
                np.add(arr, arr)
            else:
                np.add(arr, arr, out=arr)
        elif rnd < 0.75:
            if rnd < 0.875:
                np.multiply(arr, np.int64(2))
            else:
                np.multiply(arr, np.int64(2), out=arr)
        else:
            arr[:] = string_list

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as tpe:
        arr = np.array(string_list, dtype="T")
        futures = [tpe.submit(func, arr) for _ in range(500)]

        for f in futures:
            f.result()


@pytest.mark.skipif(
    not IS_64BIT,
    reason="Sometimes causes failures or crashes due to OOM on 32 bit runners"
)
def test_legacy_usertype_cast_init_thread_safety():
    def closure(b):
        b.wait()
        np.full((10, 10), 1, _rational_tests.rational)

    run_threaded(closure, 250, pass_barrier=True)

@pytest.mark.parametrize("dtype", [bool, int, float])
def test_nonzero(dtype):
    # See: gh-28361
    #
    # np.nonzero uses np.count_nonzero to determine the size of the output.
    # array. In a second pass the indices of the non-zero elements are
    # determined, but they can have changed
    #
    # This test triggers a data race which is suppressed in the TSAN CI.
    # The test is to ensure np.nonzero does not generate a segmentation fault
    x = np.random.randint(4, size=100).astype(dtype)
    expected_warning = ('number of non-zero array elements changed'
                        ' during function execution')

    def func(index):
        for _ in range(10):
            if index == 0:
                x[::2] = np.random.randint(2)
            else:
                try:
                    _ = np.nonzero(x)
                except RuntimeError as ex:
                    assert expected_warning in str(ex)

    run_threaded(func, max_workers=10, pass_count=True, outer_iterations=5)


# These are all implemented using PySequence_Fast, which needs locking to be safe
def np_broadcast(arrs):
    for i in range(50):
        np.broadcast(arrs)

def create_array(arrs):
    for i in range(50):
        np.array(arrs)

def create_nditer(arrs):
    for i in range(50):
        np.nditer(arrs)


@pytest.mark.parametrize(
    "kernel, outcome",
    (
        (np_broadcast, "error"),
        (create_array, "error"),
        (create_nditer, "success"),
    ),
)
def test_arg_locking(kernel, outcome):
    # should complete without triggering races but may error

    done = 0
    arrs = [np.array([1, 2, 3]) for _ in range(1000)]

    def read_arrs(b):
        nonlocal done
        b.wait()
        try:
            kernel(arrs)
        finally:
            done += 1

    def contract_and_expand_list(b):
        b.wait()
        while done < 4:
            if len(arrs) > 10:
                arrs.pop(0)
            elif len(arrs) <= 10:
                arrs.extend([np.array([1, 2, 3]) for _ in range(1000)])

    def replace_list_items(b):
        b.wait()
        rng = np.random.RandomState()
        rng.seed(0x4d3d3d3)
        while done < 4:
            data = rng.randint(0, 1000, size=4)
            arrs[data[0]] = data[1:]

    for mutation_func in (replace_list_items, contract_and_expand_list):
        b = threading.Barrier(5)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as tpe:
                tasks = [tpe.submit(read_arrs, b) for _ in range(4)]
                tasks.append(tpe.submit(mutation_func, b))
                for t in tasks:
                    t.result()
        except RuntimeError as e:
            if outcome == "success":
                raise
            assert "Inconsistent object during array creation?" in str(e)
            msg = "replace_list_items should not raise errors"
            assert mutation_func is contract_and_expand_list, msg
        finally:
            if len(tasks) < 5:
                b.abort()

@pytest.mark.skipif(sys.version_info < (3, 12), reason="Python >= 3.12 required")
def test_array__buffer__thread_safety():
    import inspect
    arr = np.arange(1000)
    flags = [inspect.BufferFlags.STRIDED, inspect.BufferFlags.READ]

    def func(b):
        b.wait()
        for i in range(100):
            arr.__buffer__(flags[i % 2])

    run_threaded(func, max_workers=8, pass_barrier=True)

@pytest.mark.skipif(sys.version_info < (3, 12), reason="Python >= 3.12 required")
def test_void_dtype__buffer__thread_safety():
    import inspect
    dt = np.dtype([('name', np.str_, 16), ('grades', np.float64, (2,))])
    x = np.array(('ndarray_scalar', (1.2, 3.0)), dtype=dt)[()]
    assert isinstance(x, np.void)
    flags = [inspect.BufferFlags.STRIDES, inspect.BufferFlags.READ]

    def func(b):
        b.wait()
        for i in range(100):
            x.__buffer__(flags[i % 2])

    run_threaded(func, max_workers=8, pass_barrier=True)
