import sys
import warnings

import pytest

import numpy as np
from numpy import random
from numpy.testing import (
    IS_WASM,
    assert_,
    assert_array_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_no_warnings,
    assert_raises,
)


class TestSeed:
    def test_scalar(self):
        s = np.random.RandomState(0)
        assert_equal(s.randint(1000), 684)
        s = np.random.RandomState(4294967295)
        assert_equal(s.randint(1000), 419)

    def test_array(self):
        s = np.random.RandomState(range(10))
        assert_equal(s.randint(1000), 468)
        s = np.random.RandomState(np.arange(10))
        assert_equal(s.randint(1000), 468)
        s = np.random.RandomState([0])
        assert_equal(s.randint(1000), 973)
        s = np.random.RandomState([4294967295])
        assert_equal(s.randint(1000), 265)

    def test_invalid_scalar(self):
        # seed must be an unsigned 32 bit integer
        assert_raises(TypeError, np.random.RandomState, -0.5)
        assert_raises(ValueError, np.random.RandomState, -1)

    def test_invalid_array(self):
        # seed must be an unsigned 32 bit integer
        assert_raises(TypeError, np.random.RandomState, [-0.5])
        assert_raises(ValueError, np.random.RandomState, [-1])
        assert_raises(ValueError, np.random.RandomState, [4294967296])
        assert_raises(ValueError, np.random.RandomState, [1, 2, 4294967296])
        assert_raises(ValueError, np.random.RandomState, [1, -2, 4294967296])

    def test_invalid_array_shape(self):
        # gh-9832
        assert_raises(ValueError, np.random.RandomState,
                      np.array([], dtype=np.int64))
        assert_raises(ValueError, np.random.RandomState, [[1, 2, 3]])
        assert_raises(ValueError, np.random.RandomState, [[1, 2, 3],
                                                          [4, 5, 6]])


class TestBinomial:
    def test_n_zero(self):
        # Tests the corner case of n == 0 for the binomial distribution.
        # binomial(0, p) should be zero for any p in [0, 1].
        # This test addresses issue #3480.
        zeros = np.zeros(2, dtype='int')
        for p in [0, .5, 1]:
            assert_(random.binomial(0, p) == 0)
            assert_array_equal(random.binomial(zeros, p), zeros)

    def test_p_is_nan(self):
        # Issue #4571.
        assert_raises(ValueError, random.binomial, 1, np.nan)


class TestMultinomial:
    def test_basic(self):
        random.multinomial(100, [0.2, 0.8])

    def test_zero_probability(self):
        random.multinomial(100, [0.2, 0.8, 0.0, 0.0, 0.0])

    def test_int_negative_interval(self):
        assert_(-5 <= random.randint(-5, -1) < -1)
        x = random.randint(-5, -1, 5)
        assert_(np.all(-5 <= x))
        assert_(np.all(x < -1))

    def test_size(self):
        # gh-3173
        p = [0.5, 0.5]
        assert_equal(np.random.multinomial(1, p, np.uint32(1)).shape, (1, 2))
        assert_equal(np.random.multinomial(1, p, np.uint32(1)).shape, (1, 2))
        assert_equal(np.random.multinomial(1, p, np.uint32(1)).shape, (1, 2))
        assert_equal(np.random.multinomial(1, p, [2, 2]).shape, (2, 2, 2))
        assert_equal(np.random.multinomial(1, p, (2, 2)).shape, (2, 2, 2))
        assert_equal(np.random.multinomial(1, p, np.array((2, 2))).shape,
                     (2, 2, 2))

        assert_raises(TypeError, np.random.multinomial, 1, p,
                      float(1))

    def test_multidimensional_pvals(self):
        assert_raises(ValueError, np.random.multinomial, 10, [[0, 1]])
        assert_raises(ValueError, np.random.multinomial, 10, [[0], [1]])
        assert_raises(ValueError, np.random.multinomial, 10, [[[0], [1]], [[1], [0]]])
        assert_raises(ValueError, np.random.multinomial, 10, np.array([[0, 1], [1, 0]]))


class TestSetState:
    def _create_rng(self):
        seed = 1234567890
        prng = random.RandomState(seed)
        state = prng.get_state()
        return prng, state

    def test_basic(self):
        prng, state = self._create_rng()
        old = prng.tomaxint(16)
        prng.set_state(state)
        new = prng.tomaxint(16)
        assert_(np.all(old == new))

    def test_gaussian_reset(self):
        # Make sure the cached every-other-Gaussian is reset.
        prng, state = self._create_rng()
        old = prng.standard_normal(size=3)
        prng.set_state(state)
        new = prng.standard_normal(size=3)
        assert_(np.all(old == new))

    def test_gaussian_reset_in_media_res(self):
        # When the state is saved with a cached Gaussian, make sure the
        # cached Gaussian is restored.
        prng, state = self._create_rng()
        prng.standard_normal()
        state = prng.get_state()
        old = prng.standard_normal(size=3)
        prng.set_state(state)
        new = prng.standard_normal(size=3)
        assert_(np.all(old == new))

    def test_backwards_compatibility(self):
        # Make sure we can accept old state tuples that do not have the
        # cached Gaussian value.
        prng, state = self._create_rng()
        old_state = state[:-2]
        x1 = prng.standard_normal(size=16)
        prng.set_state(old_state)
        x2 = prng.standard_normal(size=16)
        prng.set_state(state)
        x3 = prng.standard_normal(size=16)
        assert_(np.all(x1 == x2))
        assert_(np.all(x1 == x3))

    def test_negative_binomial(self):
        # Ensure that the negative binomial results take floating point
        # arguments without truncation.
        prng, _ = self._create_rng()
        prng.negative_binomial(0.5, 0.5)

    def test_set_invalid_state(self):
        # gh-25402
        prng, _ = self._create_rng()
        with pytest.raises(IndexError):
            prng.set_state(())


class TestRandint:

    # valid integer/boolean types
    itype = [np.bool, np.int8, np.uint8, np.int16, np.uint16,
             np.int32, np.uint32, np.int64, np.uint64]

    def test_unsupported_type(self):
        rng = random.RandomState()
        assert_raises(TypeError, rng.randint, 1, dtype=float)

    def test_bounds_checking(self):
        rng = random.RandomState()
        for dt in self.itype:
            lbnd = 0 if dt is np.bool else np.iinfo(dt).min
            ubnd = 2 if dt is np.bool else np.iinfo(dt).max + 1
            assert_raises(ValueError, rng.randint, lbnd - 1, ubnd, dtype=dt)
            assert_raises(ValueError, rng.randint, lbnd, ubnd + 1, dtype=dt)
            assert_raises(ValueError, rng.randint, ubnd, lbnd, dtype=dt)
            assert_raises(ValueError, rng.randint, 1, 0, dtype=dt)

    def test_rng_zero_and_extremes(self):
        rng = random.RandomState()
        for dt in self.itype:
            lbnd = 0 if dt is np.bool else np.iinfo(dt).min
            ubnd = 2 if dt is np.bool else np.iinfo(dt).max + 1

            tgt = ubnd - 1
            assert_equal(rng.randint(tgt, tgt + 1, size=1000, dtype=dt), tgt)

            tgt = lbnd
            assert_equal(rng.randint(tgt, tgt + 1, size=1000, dtype=dt), tgt)

            tgt = (lbnd + ubnd) // 2
            assert_equal(rng.randint(tgt, tgt + 1, size=1000, dtype=dt), tgt)

    def test_full_range(self):
        # Test for ticket #1690
        rng = random.RandomState()

        for dt in self.itype:
            lbnd = 0 if dt is np.bool else np.iinfo(dt).min
            ubnd = 2 if dt is np.bool else np.iinfo(dt).max + 1

            try:
                rng.randint(lbnd, ubnd, dtype=dt)
            except Exception as e:
                raise AssertionError("No error should have been raised, "
                                     "but one was with the following "
                                     "message:\n\n%s" % str(e))

    def test_in_bounds_fuzz(self):
        # Don't use fixed seed
        rng = random.RandomState()

        for dt in self.itype[1:]:
            for ubnd in [4, 8, 16]:
                vals = rng.randint(2, ubnd, size=2**16, dtype=dt)
                assert_(vals.max() < ubnd)
                assert_(vals.min() >= 2)

        vals = rng.randint(0, 2, size=2**16, dtype=np.bool)

        assert_(vals.max() < 2)
        assert_(vals.min() >= 0)

    def test_repeatability(self):
        import hashlib
        # We use a sha256 hash of generated sequences of 1000 samples
        # in the range [0, 6) for all but bool, where the range
        # is [0, 2). Hashes are for little endian numbers.
        tgt = {'bool':   '509aea74d792fb931784c4b0135392c65aec64beee12b0cc167548a2c3d31e71',  # noqa: E501
               'int16':  '7b07f1a920e46f6d0fe02314155a2330bcfd7635e708da50e536c5ebb631a7d4',  # noqa: E501
               'int32':  'e577bfed6c935de944424667e3da285012e741892dcb7051a8f1ce68ab05c92f',  # noqa: E501
               'int64':  '0fbead0b06759df2cfb55e43148822d4a1ff953c7eb19a5b08445a63bb64fa9e',  # noqa: E501
               'int8':   '001aac3a5acb935a9b186cbe14a1ca064b8bb2dd0b045d48abeacf74d0203404',  # noqa: E501
               'uint16': '7b07f1a920e46f6d0fe02314155a2330bcfd7635e708da50e536c5ebb631a7d4',  # noqa: E501
               'uint32': 'e577bfed6c935de944424667e3da285012e741892dcb7051a8f1ce68ab05c92f',  # noqa: E501
               'uint64': '0fbead0b06759df2cfb55e43148822d4a1ff953c7eb19a5b08445a63bb64fa9e',  # noqa: E501
               'uint8':  '001aac3a5acb935a9b186cbe14a1ca064b8bb2dd0b045d48abeacf74d0203404'}  # noqa: E501

        for dt in self.itype[1:]:
            rng = random.RandomState(1234)

            # view as little endian for hash
            if sys.byteorder == 'little':
                val = rng.randint(0, 6, size=1000, dtype=dt)
            else:
                val = rng.randint(0, 6, size=1000, dtype=dt).byteswap()

            res = hashlib.sha256(val.view(np.int8)).hexdigest()
            assert_(tgt[np.dtype(dt).name] == res)

        # bools do not depend on endianness
        rng = random.RandomState(1234)
        val = rng.randint(0, 2, size=1000, dtype=bool).view(np.int8)
        res = hashlib.sha256(val).hexdigest()
        assert_(tgt[np.dtype(bool).name] == res)

    def test_int64_uint64_corner_case(self):
        # When stored in Numpy arrays, `lbnd` is casted
        # as np.int64, and `ubnd` is casted as np.uint64.
        # Checking whether `lbnd` >= `ubnd` used to be
        # done solely via direct comparison, which is incorrect
        # because when Numpy tries to compare both numbers,
        # it casts both to np.float64 because there is
        # no integer superset of np.int64 and np.uint64. However,
        # `ubnd` is too large to be represented in np.float64,
        # causing it be round down to np.iinfo(np.int64).max,
        # leading to a ValueError because `lbnd` now equals
        # the new `ubnd`.

        dt = np.int64
        tgt = np.iinfo(np.int64).max
        lbnd = np.int64(np.iinfo(np.int64).max)
        ubnd = np.uint64(np.iinfo(np.int64).max + 1)

        # None of these function calls should
        # generate a ValueError now.
        actual = np.random.randint(lbnd, ubnd, dtype=dt)
        assert_equal(actual, tgt)

    def test_respect_dtype_singleton(self):
        # See gh-7203
        rng = random.RandomState()
        for dt in self.itype:
            lbnd = 0 if dt is np.bool else np.iinfo(dt).min
            ubnd = 2 if dt is np.bool else np.iinfo(dt).max + 1

            sample = rng.randint(lbnd, ubnd, dtype=dt)
            assert_equal(sample.dtype, np.dtype(dt))

        for dt in (bool, int):
            # The legacy rng uses "long" as the default integer:
            lbnd = 0 if dt is bool else np.iinfo("long").min
            ubnd = 2 if dt is bool else np.iinfo("long").max + 1

            # gh-7284: Ensure that we get Python data types
            sample = rng.randint(lbnd, ubnd, dtype=dt)
            assert_(not hasattr(sample, 'dtype'))
            assert_equal(type(sample), dt)


class TestRandomDist:
    # Make sure the random distribution returns the correct value for a
    # given seed
    seed = 1234567890

    def test_rand(self):
        rng = random.RandomState(self.seed)
        actual = rng.rand(3, 2)
        desired = np.array([[0.61879477158567997, 0.59162362775974664],
                            [0.88868358904449662, 0.89165480011560816],
                            [0.4575674820298663, 0.7781880808593471]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_randn(self):
        rng = random.RandomState(self.seed)
        actual = rng.randn(3, 2)
        desired = np.array([[1.34016345771863121, 1.73759122771936081],
                           [1.498988344300628, -0.2286433324536169],
                           [2.031033998682787, 2.17032494605655257]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_randint(self):
        rng = random.RandomState(self.seed)
        actual = rng.randint(-99, 99, size=(3, 2))
        desired = np.array([[31, 3],
                            [-52, 41],
                            [-48, -66]])
        assert_array_equal(actual, desired)

    def test_random_integers(self):
        rng = random.RandomState(self.seed)
        with pytest.warns(DeprecationWarning):
            actual = rng.random_integers(-99, 99, size=(3, 2))
        desired = np.array([[31, 3],
                            [-52, 41],
                            [-48, -66]])
        assert_array_equal(actual, desired)

    def test_random_integers_max_int(self):
        # Tests whether random_integers can generate the
        # maximum allowed Python int that can be converted
        # into a C long. Previous implementations of this
        # method have thrown an OverflowError when attempting
        # to generate this integer.
        with pytest.warns(DeprecationWarning):
            actual = np.random.random_integers(np.iinfo('l').max,
                                               np.iinfo('l').max)

        desired = np.iinfo('l').max
        assert_equal(actual, desired)

    def test_random_integers_deprecated(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)

            # DeprecationWarning raised with high == None
            assert_raises(DeprecationWarning,
                          np.random.random_integers,
                          np.iinfo('l').max)

            # DeprecationWarning raised with high != None
            assert_raises(DeprecationWarning,
                          np.random.random_integers,
                          np.iinfo('l').max, np.iinfo('l').max)

    def test_random(self):
        rng = random.RandomState(self.seed)
        actual = rng.random((3, 2))
        desired = np.array([[0.61879477158567997, 0.59162362775974664],
                            [0.88868358904449662, 0.89165480011560816],
                            [0.4575674820298663, 0.7781880808593471]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_choice_uniform_replace(self):
        rng = random.RandomState(self.seed)
        actual = rng.choice(4, 4)
        desired = np.array([2, 3, 2, 3])
        assert_array_equal(actual, desired)

    def test_choice_nonuniform_replace(self):
        rng = random.RandomState(self.seed)
        actual = rng.choice(4, 4, p=[0.4, 0.4, 0.1, 0.1])
        desired = np.array([1, 1, 2, 2])
        assert_array_equal(actual, desired)

    def test_choice_uniform_noreplace(self):
        rng = random.RandomState(self.seed)
        actual = rng.choice(4, 3, replace=False)
        desired = np.array([0, 1, 3])
        assert_array_equal(actual, desired)

    def test_choice_nonuniform_noreplace(self):
        rng = random.RandomState(self.seed)
        actual = rng.choice(4, 3, replace=False,
                                  p=[0.1, 0.3, 0.5, 0.1])
        desired = np.array([2, 3, 1])
        assert_array_equal(actual, desired)

    def test_choice_noninteger(self):
        rng = random.RandomState(self.seed)
        actual = rng.choice(['a', 'b', 'c', 'd'], 4)
        desired = np.array(['c', 'd', 'c', 'd'])
        assert_array_equal(actual, desired)

    def test_choice_exceptions(self):
        sample = np.random.choice
        assert_raises(ValueError, sample, -1, 3)
        assert_raises(ValueError, sample, 3., 3)
        assert_raises(ValueError, sample, [[1, 2], [3, 4]], 3)
        assert_raises(ValueError, sample, [], 3)
        assert_raises(ValueError, sample, [1, 2, 3, 4], 3,
                      p=[[0.25, 0.25], [0.25, 0.25]])
        assert_raises(ValueError, sample, [1, 2], 3, p=[0.4, 0.4, 0.2])
        assert_raises(ValueError, sample, [1, 2], 3, p=[1.1, -0.1])
        assert_raises(ValueError, sample, [1, 2], 3, p=[0.4, 0.4])
        assert_raises(ValueError, sample, [1, 2, 3], 4, replace=False)
        # gh-13087
        assert_raises(ValueError, sample, [1, 2, 3], -2, replace=False)
        assert_raises(ValueError, sample, [1, 2, 3], (-1,), replace=False)
        assert_raises(ValueError, sample, [1, 2, 3], (-1, 1), replace=False)
        assert_raises(ValueError, sample, [1, 2, 3], 2,
                      replace=False, p=[1, 0, 0])

    def test_choice_return_shape(self):
        p = [0.1, 0.9]
        # Check scalar
        assert_(np.isscalar(np.random.choice(2, replace=True)))
        assert_(np.isscalar(np.random.choice(2, replace=False)))
        assert_(np.isscalar(np.random.choice(2, replace=True, p=p)))
        assert_(np.isscalar(np.random.choice(2, replace=False, p=p)))
        assert_(np.isscalar(np.random.choice([1, 2], replace=True)))
        assert_(np.random.choice([None], replace=True) is None)
        a = np.array([1, 2])
        arr = np.empty(1, dtype=object)
        arr[0] = a
        assert_(np.random.choice(arr, replace=True) is a)

        # Check 0-d array
        s = ()
        assert_(not np.isscalar(np.random.choice(2, s, replace=True)))
        assert_(not np.isscalar(np.random.choice(2, s, replace=False)))
        assert_(not np.isscalar(np.random.choice(2, s, replace=True, p=p)))
        assert_(not np.isscalar(np.random.choice(2, s, replace=False, p=p)))
        assert_(not np.isscalar(np.random.choice([1, 2], s, replace=True)))
        assert_(np.random.choice([None], s, replace=True).ndim == 0)
        a = np.array([1, 2])
        arr = np.empty(1, dtype=object)
        arr[0] = a
        assert_(np.random.choice(arr, s, replace=True).item() is a)

        # Check multi dimensional array
        s = (2, 3)
        p = [0.1, 0.1, 0.1, 0.1, 0.4, 0.2]
        assert_equal(np.random.choice(6, s, replace=True).shape, s)
        assert_equal(np.random.choice(6, s, replace=False).shape, s)
        assert_equal(np.random.choice(6, s, replace=True, p=p).shape, s)
        assert_equal(np.random.choice(6, s, replace=False, p=p).shape, s)
        assert_equal(np.random.choice(np.arange(6), s, replace=True).shape, s)

        # Check zero-size
        assert_equal(np.random.randint(0, 0, size=(3, 0, 4)).shape, (3, 0, 4))
        assert_equal(np.random.randint(0, -10, size=0).shape, (0,))
        assert_equal(np.random.randint(10, 10, size=0).shape, (0,))
        assert_equal(np.random.choice(0, size=0).shape, (0,))
        assert_equal(np.random.choice([], size=(0,)).shape, (0,))
        assert_equal(np.random.choice(['a', 'b'], size=(3, 0, 4)).shape,
                     (3, 0, 4))
        assert_raises(ValueError, np.random.choice, [], 10)

    def test_choice_nan_probabilities(self):
        a = np.array([42, 1, 2])
        p = [None, None, None]
        assert_raises(ValueError, np.random.choice, a, p=p)

    def test_bytes(self):
        rng = random.RandomState(self.seed)
        actual = rng.bytes(10)
        desired = b'\x82Ui\x9e\xff\x97+Wf\xa5'
        assert_equal(actual, desired)

    def test_shuffle(self):
        # Test lists, arrays (of various dtypes), and multidimensional versions
        # of both, c-contiguous or not:
        for conv in [lambda x: np.array([]),
                     lambda x: x,
                     lambda x: np.asarray(x).astype(np.int8),
                     lambda x: np.asarray(x).astype(np.float32),
                     lambda x: np.asarray(x).astype(np.complex64),
                     lambda x: np.asarray(x).astype(object),
                     lambda x: [(i, i) for i in x],
                     lambda x: np.asarray([[i, i] for i in x]),
                     lambda x: np.vstack([x, x]).T,
                     # gh-11442
                     lambda x: (np.asarray([(i, i) for i in x],
                                           [("a", int), ("b", int)])
                                .view(np.recarray)),
                     # gh-4270
                     lambda x: np.asarray([(i, i) for i in x],
                                          [("a", object), ("b", np.int32)])]:
            rng = random.RandomState(self.seed)
            alist = conv([1, 2, 3, 4, 5, 6, 7, 8, 9, 0])
            rng.shuffle(alist)
            actual = alist
            desired = conv([0, 1, 9, 6, 2, 4, 5, 8, 7, 3])
            assert_array_equal(actual, desired)

    def test_shuffle_masked(self):
        # gh-3263
        a = np.ma.masked_values(np.reshape(range(20), (5, 4)) % 3 - 1, -1)
        b = np.ma.masked_values(np.arange(20) % 3 - 1, -1)
        a_orig = a.copy()
        b_orig = b.copy()
        for i in range(50):
            np.random.shuffle(a)
            assert_equal(
                sorted(a.data[~a.mask]), sorted(a_orig.data[~a_orig.mask]))
            np.random.shuffle(b)
            assert_equal(
                sorted(b.data[~b.mask]), sorted(b_orig.data[~b_orig.mask]))

    @pytest.mark.parametrize("random",
            [np.random, np.random.RandomState(), np.random.default_rng()])
    def test_shuffle_untyped_warning(self, random):
        # Create a dict works like a sequence but isn't one
        values = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}
        with pytest.warns(UserWarning,
                match="you are shuffling a 'dict' object") as rec:
            random.shuffle(values)
        assert "test_random" in rec[0].filename

    @pytest.mark.parametrize("random",
        [np.random, np.random.RandomState(), np.random.default_rng()])
    @pytest.mark.parametrize("use_array_like", [True, False])
    def test_shuffle_no_object_unpacking(self, random, use_array_like):
        class MyArr(np.ndarray):
            pass

        items = [
            None, np.array([3]), np.float64(3), np.array(10), np.float64(7)
        ]
        arr = np.array(items, dtype=object)
        item_ids = {id(i) for i in items}
        if use_array_like:
            arr = arr.view(MyArr)

        # The array was created fine, and did not modify any objects:
        assert all(id(i) in item_ids for i in arr)

        if use_array_like and not isinstance(random, np.random.Generator):
            # The old API gives incorrect results, but warns about it.
            with pytest.warns(UserWarning,
                    match="Shuffling a one dimensional array.*"):
                random.shuffle(arr)
        else:
            random.shuffle(arr)
            assert all(id(i) in item_ids for i in arr)

    def test_shuffle_memoryview(self):
        # gh-18273
        # allow graceful handling of memoryviews
        # (treat the same as arrays)
        rng = random.RandomState(self.seed)
        a = np.arange(5).data
        rng.shuffle(a)
        assert_equal(np.asarray(a), [0, 1, 4, 3, 2])
        rng = random.RandomState(self.seed)
        rng.shuffle(a)
        assert_equal(np.asarray(a), [0, 1, 2, 3, 4])
        rng = np.random.default_rng(self.seed)
        rng.shuffle(a)
        assert_equal(np.asarray(a), [4, 1, 0, 3, 2])

    def test_shuffle_not_writeable(self):
        a = np.zeros(3)
        a.flags.writeable = False
        with pytest.raises(ValueError, match='read-only'):
            np.random.shuffle(a)

    def test_beta(self):
        rng = random.RandomState(self.seed)
        actual = rng.beta(.1, .9, size=(3, 2))
        desired = np.array(
                [[1.45341850513746058e-02, 5.31297615662868145e-04],
                 [1.85366619058432324e-06, 4.19214516800110563e-03],
                 [1.58405155108498093e-04, 1.26252891949397652e-04]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_binomial(self):
        rng = random.RandomState(self.seed)
        actual = rng.binomial(100, .456, size=(3, 2))
        desired = np.array([[37, 43],
                            [42, 48],
                            [46, 45]])
        assert_array_equal(actual, desired)

    def test_chisquare(self):
        rng = random.RandomState(self.seed)
        actual = rng.chisquare(50, size=(3, 2))
        desired = np.array([[63.87858175501090585, 68.68407748911370447],
                            [65.77116116901505904, 47.09686762438974483],
                            [72.3828403199695174, 74.18408615260374006]])
        assert_array_almost_equal(actual, desired, decimal=13)

    def test_dirichlet(self):
        rng = random.RandomState(self.seed)
        alpha = np.array([51.72840233779265162, 39.74494232180943953])
        actual = rng.dirichlet(alpha, size=(3, 2))
        desired = np.array([[[0.54539444573611562, 0.45460555426388438],
                             [0.62345816822039413, 0.37654183177960598]],
                            [[0.55206000085785778, 0.44793999914214233],
                             [0.58964023305154301, 0.41035976694845688]],
                            [[0.59266909280647828, 0.40733090719352177],
                             [0.56974431743975207, 0.43025568256024799]]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_dirichlet_size(self):
        # gh-3173
        p = np.array([51.72840233779265162, 39.74494232180943953])
        assert_equal(np.random.dirichlet(p, np.uint32(1)).shape, (1, 2))
        assert_equal(np.random.dirichlet(p, np.uint32(1)).shape, (1, 2))
        assert_equal(np.random.dirichlet(p, np.uint32(1)).shape, (1, 2))
        assert_equal(np.random.dirichlet(p, [2, 2]).shape, (2, 2, 2))
        assert_equal(np.random.dirichlet(p, (2, 2)).shape, (2, 2, 2))
        assert_equal(np.random.dirichlet(p, np.array((2, 2))).shape, (2, 2, 2))

        assert_raises(TypeError, np.random.dirichlet, p, float(1))

    def test_dirichlet_bad_alpha(self):
        # gh-2089
        alpha = np.array([5.4e-01, -1.0e-16])
        assert_raises(ValueError, np.random.mtrand.dirichlet, alpha)

        # gh-15876
        assert_raises(ValueError, random.dirichlet, [[5, 1]])
        assert_raises(ValueError, random.dirichlet, [[5], [1]])
        assert_raises(ValueError, random.dirichlet, [[[5], [1]], [[1], [5]]])
        assert_raises(ValueError, random.dirichlet, np.array([[5, 1], [1, 5]]))

    def test_exponential(self):
        rng = random.RandomState(self.seed)
        actual = rng.exponential(1.1234, size=(3, 2))
        desired = np.array([[1.08342649775011624, 1.00607889924557314],
                            [2.46628830085216721, 2.49668106809923884],
                            [0.68717433461363442, 1.69175666993575979]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_exponential_0(self):
        assert_equal(np.random.exponential(scale=0), 0)
        assert_raises(ValueError, np.random.exponential, scale=-0.)

    def test_f(self):
        rng = random.RandomState(self.seed)
        actual = rng.f(12, 77, size=(3, 2))
        desired = np.array([[1.21975394418575878, 1.75135759791559775],
                            [1.44803115017146489, 1.22108959480396262],
                            [1.02176975757740629, 1.34431827623300415]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_gamma(self):
        rng = random.RandomState(self.seed)
        actual = rng.gamma(5, 3, size=(3, 2))
        desired = np.array([[24.60509188649287182, 28.54993563207210627],
                            [26.13476110204064184, 12.56988482927716078],
                            [31.71863275789960568, 33.30143302795922011]])
        assert_array_almost_equal(actual, desired, decimal=14)

    def test_gamma_0(self):
        assert_equal(np.random.gamma(shape=0, scale=0), 0)
        assert_raises(ValueError, np.random.gamma, shape=-0., scale=-0.)

    def test_geometric(self):
        rng = random.RandomState(self.seed)
        actual = rng.geometric(.123456789, size=(3, 2))
        desired = np.array([[8, 7],
                            [17, 17],
                            [5, 12]])
        assert_array_equal(actual, desired)

    def test_gumbel(self):
        rng = random.RandomState(self.seed)
        actual = rng.gumbel(loc=.123456789, scale=2.0, size=(3, 2))
        desired = np.array([[0.19591898743416816, 0.34405539668096674],
                            [-1.4492522252274278, -1.47374816298446865],
                            [1.10651090478803416, -0.69535848626236174]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_gumbel_0(self):
        assert_equal(np.random.gumbel(scale=0), 0)
        assert_raises(ValueError, np.random.gumbel, scale=-0.)

    def test_hypergeometric(self):
        rng = random.RandomState(self.seed)
        actual = rng.hypergeometric(10, 5, 14, size=(3, 2))
        desired = np.array([[10, 10],
                            [10, 10],
                            [9, 9]])
        assert_array_equal(actual, desired)

        # Test nbad = 0
        actual = rng.hypergeometric(5, 0, 3, size=4)
        desired = np.array([3, 3, 3, 3])
        assert_array_equal(actual, desired)

        actual = rng.hypergeometric(15, 0, 12, size=4)
        desired = np.array([12, 12, 12, 12])
        assert_array_equal(actual, desired)

        # Test ngood = 0
        actual = rng.hypergeometric(0, 5, 3, size=4)
        desired = np.array([0, 0, 0, 0])
        assert_array_equal(actual, desired)

        actual = rng.hypergeometric(0, 15, 12, size=4)
        desired = np.array([0, 0, 0, 0])
        assert_array_equal(actual, desired)

    def test_laplace(self):
        rng = random.RandomState(self.seed)
        actual = rng.laplace(loc=.123456789, scale=2.0, size=(3, 2))
        desired = np.array([[0.66599721112760157, 0.52829452552221945],
                            [3.12791959514407125, 3.18202813572992005],
                            [-0.05391065675859356, 1.74901336242837324]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_laplace_0(self):
        assert_equal(np.random.laplace(scale=0), 0)
        assert_raises(ValueError, np.random.laplace, scale=-0.)

    def test_logistic(self):
        rng = random.RandomState(self.seed)
        actual = rng.logistic(loc=.123456789, scale=2.0, size=(3, 2))
        desired = np.array([[1.09232835305011444, 0.8648196662399954],
                            [4.27818590694950185, 4.33897006346929714],
                            [-0.21682183359214885, 2.63373365386060332]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_lognormal(self):
        rng = random.RandomState(self.seed)
        actual = rng.lognormal(mean=.123456789, sigma=2.0, size=(3, 2))
        desired = np.array([[16.50698631688883822, 36.54846706092654784],
                            [22.67886599981281748, 0.71617561058995771],
                            [65.72798501792723869, 86.84341601437161273]])
        assert_array_almost_equal(actual, desired, decimal=13)

    def test_lognormal_0(self):
        assert_equal(np.random.lognormal(sigma=0), 1)
        assert_raises(ValueError, np.random.lognormal, sigma=-0.)

    def test_logseries(self):
        rng = random.RandomState(self.seed)
        actual = rng.logseries(p=.923456789, size=(3, 2))
        desired = np.array([[2, 2],
                            [6, 17],
                            [3, 6]])
        assert_array_equal(actual, desired)

    def test_multinomial(self):
        rng = random.RandomState(self.seed)
        actual = rng.multinomial(20, [1 / 6.] * 6, size=(3, 2))
        desired = np.array([[[4, 3, 5, 4, 2, 2],
                             [5, 2, 8, 2, 2, 1]],
                            [[3, 4, 3, 6, 0, 4],
                             [2, 1, 4, 3, 6, 4]],
                            [[4, 4, 2, 5, 2, 3],
                             [4, 3, 4, 2, 3, 4]]])
        assert_array_equal(actual, desired)

    def test_multivariate_normal(self):
        rng = random.RandomState(self.seed)
        mean = (.123456789, 10)
        cov = [[1, 0], [0, 1]]
        size = (3, 2)
        actual = rng.multivariate_normal(mean, cov, size)
        desired = np.array([[[1.463620246718631, 11.73759122771936],
                             [1.622445133300628, 9.771356667546383]],
                            [[2.154490787682787, 12.170324946056553],
                             [1.719909438201865, 9.230548443648306]],
                            [[0.689515026297799, 9.880729819607714],
                             [-0.023054015651998, 9.201096623542879]]])

        assert_array_almost_equal(actual, desired, decimal=15)

        # Check for default size, was raising deprecation warning
        actual = rng.multivariate_normal(mean, cov)
        desired = np.array([0.895289569463708, 9.17180864067987])
        assert_array_almost_equal(actual, desired, decimal=15)

        # Check that non positive-semidefinite covariance warns with
        # RuntimeWarning
        mean = [0, 0]
        cov = [[1, 2], [2, 1]]
        pytest.warns(RuntimeWarning, rng.multivariate_normal, mean, cov)

        # and that it doesn't warn with RuntimeWarning check_valid='ignore'
        assert_no_warnings(rng.multivariate_normal, mean, cov,
                           check_valid='ignore')

        # and that it raises with RuntimeWarning check_valid='raises'
        assert_raises(ValueError, rng.multivariate_normal, mean, cov,
                      check_valid='raise')

        cov = np.array([[1, 0.1], [0.1, 1]], dtype=np.float32)
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            rng.multivariate_normal(mean, cov)

    def test_negative_binomial(self):
        rng = random.RandomState(self.seed)
        actual = rng.negative_binomial(n=100, p=.12345, size=(3, 2))
        desired = np.array([[848, 841],
                            [892, 611],
                            [779, 647]])
        assert_array_equal(actual, desired)

    def test_noncentral_chisquare(self):
        rng = random.RandomState(self.seed)
        actual = rng.noncentral_chisquare(df=5, nonc=5, size=(3, 2))
        desired = np.array([[23.91905354498517511, 13.35324692733826346],
                            [31.22452661329736401, 16.60047399466177254],
                            [5.03461598262724586, 17.94973089023519464]])
        assert_array_almost_equal(actual, desired, decimal=14)

        actual = rng.noncentral_chisquare(df=.5, nonc=.2, size=(3, 2))
        desired = np.array([[1.47145377828516666,  0.15052899268012659],
                            [0.00943803056963588,  1.02647251615666169],
                            [0.332334982684171,  0.15451287602753125]])
        assert_array_almost_equal(actual, desired, decimal=14)

        rng = random.RandomState(self.seed)
        actual = rng.noncentral_chisquare(df=5, nonc=0, size=(3, 2))
        desired = np.array([[9.597154162763948, 11.725484450296079],
                            [10.413711048138335, 3.694475922923986],
                            [13.484222138963087, 14.377255424602957]])
        assert_array_almost_equal(actual, desired, decimal=14)

    def test_noncentral_f(self):
        rng = random.RandomState(self.seed)
        actual = rng.noncentral_f(dfnum=5, dfden=2, nonc=1,
                                        size=(3, 2))
        desired = np.array([[1.40598099674926669, 0.34207973179285761],
                            [3.57715069265772545, 7.92632662577829805],
                            [0.43741599463544162, 1.1774208752428319]])
        assert_array_almost_equal(actual, desired, decimal=14)

    def test_normal(self):
        rng = random.RandomState(self.seed)
        actual = rng.normal(loc=.123456789, scale=2.0, size=(3, 2))
        desired = np.array([[2.80378370443726244, 3.59863924443872163],
                            [3.121433477601256, -0.33382987590723379],
                            [4.18552478636557357, 4.46410668111310471]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_normal_0(self):
        assert_equal(np.random.normal(scale=0), 0)
        assert_raises(ValueError, np.random.normal, scale=-0.)

    def test_pareto(self):
        rng = random.RandomState(self.seed)
        actual = rng.pareto(a=.123456789, size=(3, 2))
        desired = np.array(
                [[2.46852460439034849e+03, 1.41286880810518346e+03],
                 [5.28287797029485181e+07, 6.57720981047328785e+07],
                 [1.40840323350391515e+02, 1.98390255135251704e+05]])
        # For some reason on 32-bit x86 Ubuntu 12.10 the [1, 0] entry in this
        # matrix differs by 24 nulps. Discussion:
        #   https://mail.python.org/pipermail/numpy-discussion/2012-September/063801.html
        # Consensus is that this is probably some gcc quirk that affects
        # rounding but not in any important way, so we just use a looser
        # tolerance on this test:
        np.testing.assert_array_almost_equal_nulp(actual, desired, nulp=30)

    def test_poisson(self):
        rng = random.RandomState(self.seed)
        actual = rng.poisson(lam=.123456789, size=(3, 2))
        desired = np.array([[0, 0],
                            [1, 0],
                            [0, 0]])
        assert_array_equal(actual, desired)

    def test_poisson_exceptions(self):
        lambig = np.iinfo('l').max
        lamneg = -1
        assert_raises(ValueError, np.random.poisson, lamneg)
        assert_raises(ValueError, np.random.poisson, [lamneg] * 10)
        assert_raises(ValueError, np.random.poisson, lambig)
        assert_raises(ValueError, np.random.poisson, [lambig] * 10)

    def test_power(self):
        rng = random.RandomState(self.seed)
        actual = rng.power(a=.123456789, size=(3, 2))
        desired = np.array([[0.02048932883240791, 0.01424192241128213],
                            [0.38446073748535298, 0.39499689943484395],
                            [0.00177699707563439, 0.13115505880863756]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_rayleigh(self):
        rng = random.RandomState(self.seed)
        actual = rng.rayleigh(scale=10, size=(3, 2))
        desired = np.array([[13.8882496494248393, 13.383318339044731],
                            [20.95413364294492098, 21.08285015800712614],
                            [11.06066537006854311, 17.35468505778271009]])
        assert_array_almost_equal(actual, desired, decimal=14)

    def test_rayleigh_0(self):
        assert_equal(np.random.rayleigh(scale=0), 0)
        assert_raises(ValueError, np.random.rayleigh, scale=-0.)

    def test_standard_cauchy(self):
        rng = random.RandomState(self.seed)
        actual = rng.standard_cauchy(size=(3, 2))
        desired = np.array([[0.77127660196445336, -6.55601161955910605],
                            [0.93582023391158309, -2.07479293013759447],
                            [-4.74601644297011926, 0.18338989290760804]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_standard_exponential(self):
        rng = random.RandomState(self.seed)
        actual = rng.standard_exponential(size=(3, 2))
        desired = np.array([[0.96441739162374596, 0.89556604882105506],
                            [2.1953785836319808, 2.22243285392490542],
                            [0.6116915921431676, 1.50592546727413201]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_standard_gamma(self):
        rng = random.RandomState(self.seed)
        actual = rng.standard_gamma(shape=3, size=(3, 2))
        desired = np.array([[5.50841531318455058, 6.62953470301903103],
                            [5.93988484943779227, 2.31044849402133989],
                            [7.54838614231317084, 8.012756093271868]])
        assert_array_almost_equal(actual, desired, decimal=14)

    def test_standard_gamma_0(self):
        assert_equal(np.random.standard_gamma(shape=0), 0)
        assert_raises(ValueError, np.random.standard_gamma, shape=-0.)

    def test_standard_normal(self):
        rng = random.RandomState(self.seed)
        actual = rng.standard_normal(size=(3, 2))
        desired = np.array([[1.34016345771863121, 1.73759122771936081],
                            [1.498988344300628, -0.2286433324536169],
                            [2.031033998682787, 2.17032494605655257]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_standard_t(self):
        rng = random.RandomState(self.seed)
        actual = rng.standard_t(df=10, size=(3, 2))
        desired = np.array([[0.97140611862659965, -0.08830486548450577],
                            [1.36311143689505321, -0.55317463909867071],
                            [-0.18473749069684214, 0.61181537341755321]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_triangular(self):
        rng = random.RandomState(self.seed)
        actual = rng.triangular(left=5.12, mode=10.23, right=20.34,
                                      size=(3, 2))
        desired = np.array([[12.68117178949215784, 12.4129206149193152],
                            [16.20131377335158263, 16.25692138747600524],
                            [11.20400690911820263, 14.4978144835829923]])
        assert_array_almost_equal(actual, desired, decimal=14)

    def test_uniform(self):
        rng = random.RandomState(self.seed)
        actual = rng.uniform(low=1.23, high=10.54, size=(3, 2))
        desired = np.array([[6.99097932346268003, 6.73801597444323974],
                            [9.50364421400426274, 9.53130618907631089],
                            [5.48995325769805476, 8.47493103280052118]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_uniform_range_bounds(self):
        fmin = np.finfo('float').min
        fmax = np.finfo('float').max

        func = np.random.uniform
        assert_raises(OverflowError, func, -np.inf, 0)
        assert_raises(OverflowError, func,  0,      np.inf)
        assert_raises(OverflowError, func,  fmin,   fmax)
        assert_raises(OverflowError, func, [-np.inf], [0])
        assert_raises(OverflowError, func, [0], [np.inf])

        # (fmax / 1e17) - fmin is within range, so this should not throw
        # account for i386 extended precision DBL_MAX / 1e17 + DBL_MAX >
        # DBL_MAX by increasing fmin a bit
        np.random.uniform(low=np.nextafter(fmin, 1), high=fmax / 1e17)

    def test_scalar_exception_propagation(self):
        # Tests that exceptions are correctly propagated in distributions
        # when called with objects that throw exceptions when converted to
        # scalars.
        #
        # Regression test for gh: 8865

        class ThrowingFloat(np.ndarray):
            def __float__(self):
                raise TypeError

        throwing_float = np.array(1.0).view(ThrowingFloat)
        assert_raises(TypeError, np.random.uniform, throwing_float,
                      throwing_float)

        class ThrowingInteger(np.ndarray):
            def __int__(self):
                raise TypeError

            __index__ = __int__

        throwing_int = np.array(1).view(ThrowingInteger)
        assert_raises(TypeError, np.random.hypergeometric, throwing_int, 1, 1)

    def test_vonmises(self):
        rng = random.RandomState(self.seed)
        actual = rng.vonmises(mu=1.23, kappa=1.54, size=(3, 2))
        desired = np.array([[2.28567572673902042, 2.89163838442285037],
                            [0.38198375564286025, 2.57638023113890746],
                            [1.19153771588353052, 1.83509849681825354]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_vonmises_small(self):
        # check infinite loop, gh-4720
        np.random.seed(self.seed)
        r = np.random.vonmises(mu=0., kappa=1.1e-8, size=10**6)
        np.testing.assert_(np.isfinite(r).all())

    def test_wald(self):
        rng = random.RandomState(self.seed)
        actual = rng.wald(mean=1.23, scale=1.54, size=(3, 2))
        desired = np.array([[3.82935265715889983, 5.13125249184285526],
                            [0.35045403618358717, 1.50832396872003538],
                            [0.24124319895843183, 0.22031101461955038]])
        assert_array_almost_equal(actual, desired, decimal=14)

    def test_weibull(self):
        rng = random.RandomState(self.seed)
        actual = rng.weibull(a=1.23, size=(3, 2))
        desired = np.array([[0.97097342648766727, 0.91422896443565516],
                            [1.89517770034962929, 1.91414357960479564],
                            [0.67057783752390987, 1.39494046635066793]])
        assert_array_almost_equal(actual, desired, decimal=15)

    def test_weibull_0(self):
        np.random.seed(self.seed)
        assert_equal(np.random.weibull(a=0, size=12), np.zeros(12))
        assert_raises(ValueError, np.random.weibull, a=-0.)

    def test_zipf(self):
        rng = random.RandomState(self.seed)
        actual = rng.zipf(a=1.23, size=(3, 2))
        desired = np.array([[66, 29],
                            [1, 1],
                            [3, 13]])
        assert_array_equal(actual, desired)


class TestBroadcast:
    # tests that functions that broadcast behave
    # correctly when presented with non-scalar arguments
    seed = 123456789

    # TODO: Include test for randint once it can broadcast
    # Can steal the test written in PR #6938

    def test_uniform(self):
        low = [0]
        high = [1]
        desired = np.array([0.53283302478975902,
                            0.53413660089041659,
                            0.50955303552646702])

        rng = random.RandomState(self.seed)
        actual = rng.uniform(low * 3, high)
        assert_array_almost_equal(actual, desired, decimal=14)

        rng = random.RandomState(self.seed)
        actual = rng.uniform(low, high * 3)
        assert_array_almost_equal(actual, desired, decimal=14)

    def test_normal(self):
        loc = [0]
        scale = [1]
        bad_scale = [-1]
        desired = np.array([2.2129019979039612,
                            2.1283977976520019,
                            1.8417114045748335])

        rng = random.RandomState(self.seed)
        actual = rng.normal(loc * 3, scale)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.normal, loc * 3, bad_scale)

        rng = random.RandomState(self.seed)
        actual = rng.normal(loc, scale * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.normal, loc, bad_scale * 3)

    def test_beta(self):
        a = [1]
        b = [2]
        bad_a = [-1]
        bad_b = [-2]
        desired = np.array([0.19843558305989056,
                            0.075230336409423643,
                            0.24976865978980844])

        rng = random.RandomState(self.seed)
        actual = rng.beta(a * 3, b)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.beta, bad_a * 3, b)
        assert_raises(ValueError, rng.beta, a * 3, bad_b)

        rng = random.RandomState(self.seed)
        actual = rng.beta(a, b * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.beta, bad_a, b * 3)
        assert_raises(ValueError, rng.beta, a, bad_b * 3)

    def test_exponential(self):
        scale = [1]
        bad_scale = [-1]
        desired = np.array([0.76106853658845242,
                            0.76386282278691653,
                            0.71243813125891797])

        rng = random.RandomState(self.seed)
        actual = rng.exponential(scale * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.exponential, bad_scale * 3)

    def test_standard_gamma(self):
        shape = [1]
        bad_shape = [-1]
        desired = np.array([0.76106853658845242,
                            0.76386282278691653,
                            0.71243813125891797])

        rng = random.RandomState(self.seed)
        actual = rng.standard_gamma(shape * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.standard_gamma, bad_shape * 3)

    def test_gamma(self):
        shape = [1]
        scale = [2]
        bad_shape = [-1]
        bad_scale = [-2]
        desired = np.array([1.5221370731769048,
                            1.5277256455738331,
                            1.4248762625178359])

        rng = random.RandomState(self.seed)
        actual = rng.gamma(shape * 3, scale)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.gamma, bad_shape * 3, scale)
        assert_raises(ValueError, rng.gamma, shape * 3, bad_scale)

        rng = random.RandomState(self.seed)
        actual = rng.gamma(shape, scale * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.gamma, bad_shape, scale * 3)
        assert_raises(ValueError, rng.gamma, shape, bad_scale * 3)

    def test_f(self):
        dfnum = [1]
        dfden = [2]
        bad_dfnum = [-1]
        bad_dfden = [-2]
        desired = np.array([0.80038951638264799,
                            0.86768719635363512,
                            2.7251095168386801])

        rng = random.RandomState(self.seed)
        actual = rng.f(dfnum * 3, dfden)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.f, bad_dfnum * 3, dfden)
        assert_raises(ValueError, rng.f, dfnum * 3, bad_dfden)

        rng = random.RandomState(self.seed)
        actual = rng.f(dfnum, dfden * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.f, bad_dfnum, dfden * 3)
        assert_raises(ValueError, rng.f, dfnum, bad_dfden * 3)

    def test_noncentral_f(self):
        dfnum = [2]
        dfden = [3]
        nonc = [4]
        bad_dfnum = [0]
        bad_dfden = [-1]
        bad_nonc = [-2]
        desired = np.array([9.1393943263705211,
                            13.025456344595602,
                            8.8018098359100545])

        rng = random.RandomState(self.seed)
        actual = rng.noncentral_f(dfnum * 3, dfden, nonc)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.noncentral_f, bad_dfnum * 3, dfden, nonc)
        assert_raises(ValueError, rng.noncentral_f, dfnum * 3, bad_dfden, nonc)
        assert_raises(ValueError, rng.noncentral_f, dfnum * 3, dfden, bad_nonc)

        rng = random.RandomState(self.seed)
        actual = rng.noncentral_f(dfnum, dfden * 3, nonc)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.noncentral_f, bad_dfnum, dfden * 3, nonc)
        assert_raises(ValueError, rng.noncentral_f, dfnum, bad_dfden * 3, nonc)
        assert_raises(ValueError, rng.noncentral_f, dfnum, dfden * 3, bad_nonc)

        rng = random.RandomState(self.seed)
        actual = rng.noncentral_f(dfnum, dfden, nonc * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.noncentral_f, bad_dfnum, dfden, nonc * 3)
        assert_raises(ValueError, rng.noncentral_f, dfnum, bad_dfden, nonc * 3)
        assert_raises(ValueError, rng.noncentral_f, dfnum, dfden, bad_nonc * 3)

    def test_noncentral_f_small_df(self):
        rng = random.RandomState(self.seed)
        desired = np.array([6.869638627492048, 0.785880199263955])
        actual = rng.noncentral_f(0.9, 0.9, 2, size=2)
        assert_array_almost_equal(actual, desired, decimal=14)

    def test_chisquare(self):
        df = [1]
        bad_df = [-1]
        desired = np.array([0.57022801133088286,
                            0.51947702108840776,
                            0.1320969254923558])

        rng = random.RandomState(self.seed)
        actual = rng.chisquare(df * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.chisquare, bad_df * 3)

    def test_noncentral_chisquare(self):
        df = [1]
        nonc = [2]
        bad_df = [-1]
        bad_nonc = [-2]
        desired = np.array([9.0015599467913763,
                            4.5804135049718742,
                            6.0872302432834564])

        rng = random.RandomState(self.seed)
        actual = rng.noncentral_chisquare(df * 3, nonc)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.noncentral_chisquare, bad_df * 3, nonc)
        assert_raises(ValueError, rng.noncentral_chisquare, df * 3, bad_nonc)

        rng = random.RandomState(self.seed)
        actual = rng.noncentral_chisquare(df, nonc * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.noncentral_chisquare, bad_df, nonc * 3)
        assert_raises(ValueError, rng.noncentral_chisquare, df, bad_nonc * 3)

    def test_standard_t(self):
        df = [1]
        bad_df = [-1]
        desired = np.array([3.0702872575217643,
                            5.8560725167361607,
                            1.0274791436474273])

        rng = random.RandomState(self.seed)
        actual = rng.standard_t(df * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.standard_t, bad_df * 3)

    def test_vonmises(self):
        mu = [2]
        kappa = [1]
        bad_kappa = [-1]
        desired = np.array([2.9883443664201312,
                            -2.7064099483995943,
                            -1.8672476700665914])

        rng = random.RandomState(self.seed)
        actual = rng.vonmises(mu * 3, kappa)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.vonmises, mu * 3, bad_kappa)

        rng = random.RandomState(self.seed)
        actual = rng.vonmises(mu, kappa * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.vonmises, mu, bad_kappa * 3)

    def test_pareto(self):
        a = [1]
        bad_a = [-1]
        desired = np.array([1.1405622680198362,
                            1.1465519762044529,
                            1.0389564467453547])

        rng = random.RandomState(self.seed)
        actual = rng.pareto(a * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.pareto, bad_a * 3)

    def test_weibull(self):
        a = [1]
        bad_a = [-1]
        desired = np.array([0.76106853658845242,
                            0.76386282278691653,
                            0.71243813125891797])

        rng = random.RandomState(self.seed)
        actual = rng.weibull(a * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.weibull, bad_a * 3)

    def test_power(self):
        a = [1]
        bad_a = [-1]
        desired = np.array([0.53283302478975902,
                            0.53413660089041659,
                            0.50955303552646702])

        rng = random.RandomState(self.seed)
        actual = rng.power(a * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.power, bad_a * 3)

    def test_laplace(self):
        loc = [0]
        scale = [1]
        bad_scale = [-1]
        desired = np.array([0.067921356028507157,
                            0.070715642226971326,
                            0.019290950698972624])

        rng = random.RandomState(self.seed)
        actual = rng.laplace(loc * 3, scale)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.laplace, loc * 3, bad_scale)

        rng = random.RandomState(self.seed)
        actual = rng.laplace(loc, scale * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.laplace, loc, bad_scale * 3)

    def test_gumbel(self):
        loc = [0]
        scale = [1]
        bad_scale = [-1]
        desired = np.array([0.2730318639556768,
                            0.26936705726291116,
                            0.33906220393037939])

        rng = random.RandomState(self.seed)
        actual = rng.gumbel(loc * 3, scale)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.gumbel, loc * 3, bad_scale)

        rng = random.RandomState(self.seed)
        actual = rng.gumbel(loc, scale * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.gumbel, loc, bad_scale * 3)

    def test_logistic(self):
        loc = [0]
        scale = [1]
        bad_scale = [-1]
        desired = np.array([0.13152135837586171,
                            0.13675915696285773,
                            0.038216792802833396])

        rng = random.RandomState(self.seed)
        actual = rng.logistic(loc * 3, scale)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.logistic, loc * 3, bad_scale)

        rng = random.RandomState(self.seed)
        actual = rng.logistic(loc, scale * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.logistic, loc, bad_scale * 3)

    def test_lognormal(self):
        mean = [0]
        sigma = [1]
        bad_sigma = [-1]
        desired = np.array([9.1422086044848427,
                            8.4013952870126261,
                            6.3073234116578671])

        rng = random.RandomState(self.seed)
        actual = rng.lognormal(mean * 3, sigma)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.lognormal, mean * 3, bad_sigma)

        rng = random.RandomState(self.seed)
        actual = rng.lognormal(mean, sigma * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.lognormal, mean, bad_sigma * 3)

    def test_rayleigh(self):
        scale = [1]
        bad_scale = [-1]
        desired = np.array([1.2337491937897689,
                            1.2360119924878694,
                            1.1936818095781789])

        rng = random.RandomState(self.seed)
        actual = rng.rayleigh(scale * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.rayleigh, bad_scale * 3)

    def test_wald(self):
        mean = [0.5]
        scale = [1]
        bad_mean = [0]
        bad_scale = [-2]
        desired = np.array([0.11873681120271318,
                            0.12450084820795027,
                            0.9096122728408238])

        rng = random.RandomState(self.seed)
        actual = rng.wald(mean * 3, scale)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.wald, bad_mean * 3, scale)
        assert_raises(ValueError, rng.wald, mean * 3, bad_scale)

        rng = random.RandomState(self.seed)
        actual = rng.wald(mean, scale * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.wald, bad_mean, scale * 3)
        assert_raises(ValueError, rng.wald, mean, bad_scale * 3)
        assert_raises(ValueError, rng.wald, 0.0, 1)
        assert_raises(ValueError, rng.wald, 0.5, 0.0)

    def test_triangular(self):
        left = [1]
        right = [3]
        mode = [2]
        bad_left_one = [3]
        bad_mode_one = [4]
        bad_left_two, bad_mode_two = right * 2
        desired = np.array([2.03339048710429,
                            2.0347400359389356,
                            2.0095991069536208])

        rng = random.RandomState(self.seed)
        actual = rng.triangular(left * 3, mode, right)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.triangular, bad_left_one * 3, mode, right)
        assert_raises(ValueError, rng.triangular, left * 3, bad_mode_one, right)
        assert_raises(ValueError, rng.triangular, bad_left_two * 3, bad_mode_two,
                      right)

        rng = random.RandomState(self.seed)
        actual = rng.triangular(left, mode * 3, right)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.triangular, bad_left_one, mode * 3, right)
        assert_raises(ValueError, rng.triangular, left, bad_mode_one * 3, right)
        assert_raises(ValueError, rng.triangular, bad_left_two, bad_mode_two * 3,
                      right)

        rng = random.RandomState(self.seed)
        actual = rng.triangular(left, mode, right * 3)
        assert_array_almost_equal(actual, desired, decimal=14)
        assert_raises(ValueError, rng.triangular, bad_left_one, mode, right * 3)
        assert_raises(ValueError, rng.triangular, left, bad_mode_one, right * 3)
        assert_raises(ValueError, rng.triangular, bad_left_two, bad_mode_two,
                      right * 3)

    def test_binomial(self):
        n = [1]
        p = [0.5]
        bad_n = [-1]
        bad_p_one = [-1]
        bad_p_two = [1.5]
        desired = np.array([1, 1, 1])

        rng = random.RandomState(self.seed)
        actual = rng.binomial(n * 3, p)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.binomial, bad_n * 3, p)
        assert_raises(ValueError, rng.binomial, n * 3, bad_p_one)
        assert_raises(ValueError, rng.binomial, n * 3, bad_p_two)

        rng = random.RandomState(self.seed)
        actual = rng.binomial(n, p * 3)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.binomial, bad_n, p * 3)
        assert_raises(ValueError, rng.binomial, n, bad_p_one * 3)
        assert_raises(ValueError, rng.binomial, n, bad_p_two * 3)

    def test_negative_binomial(self):
        n = [1]
        p = [0.5]
        bad_n = [-1]
        bad_p_one = [-1]
        bad_p_two = [1.5]
        desired = np.array([1, 0, 1])

        rng = random.RandomState(self.seed)
        actual = rng.negative_binomial(n * 3, p)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.negative_binomial, bad_n * 3, p)
        assert_raises(ValueError, rng.negative_binomial, n * 3, bad_p_one)
        assert_raises(ValueError, rng.negative_binomial, n * 3, bad_p_two)

        rng = random.RandomState(self.seed)
        actual = rng.negative_binomial(n, p * 3)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.negative_binomial, bad_n, p * 3)
        assert_raises(ValueError, rng.negative_binomial, n, bad_p_one * 3)
        assert_raises(ValueError, rng.negative_binomial, n, bad_p_two * 3)

    def test_poisson(self):
        max_lam = np.random.RandomState()._poisson_lam_max

        lam = [1]
        bad_lam_one = [-1]
        bad_lam_two = [max_lam * 2]
        desired = np.array([1, 1, 0])

        rng = random.RandomState(self.seed)
        actual = rng.poisson(lam * 3)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.poisson, bad_lam_one * 3)
        assert_raises(ValueError, rng.poisson, bad_lam_two * 3)

    def test_zipf(self):
        a = [2]
        bad_a = [0]
        desired = np.array([2, 2, 1])

        rng = random.RandomState(self.seed)
        actual = rng.zipf(a * 3)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.zipf, bad_a * 3)
        with np.errstate(invalid='ignore'):
            assert_raises(ValueError, rng.zipf, np.nan)
            assert_raises(ValueError, rng.zipf, [0, 0, np.nan])

    def test_geometric(self):
        p = [0.5]
        bad_p_one = [-1]
        bad_p_two = [1.5]
        desired = np.array([2, 2, 2])

        rng = random.RandomState(self.seed)
        actual = rng.geometric(p * 3)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.geometric, bad_p_one * 3)
        assert_raises(ValueError, rng.geometric, bad_p_two * 3)

    def test_hypergeometric(self):
        ngood = [1]
        nbad = [2]
        nsample = [2]
        bad_ngood = [-1]
        bad_nbad = [-2]
        bad_nsample_one = [0]
        bad_nsample_two = [4]
        desired = np.array([1, 1, 1])

        rng = random.RandomState(self.seed)
        actual = rng.hypergeometric(ngood * 3, nbad, nsample)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.hypergeometric, bad_ngood * 3, nbad, nsample)
        assert_raises(ValueError, rng.hypergeometric, ngood * 3, bad_nbad, nsample)
        assert_raises(ValueError, rng.hypergeometric, ngood * 3, nbad, bad_nsample_one)
        assert_raises(ValueError, rng.hypergeometric, ngood * 3, nbad, bad_nsample_two)

        rng = random.RandomState(self.seed)
        actual = rng.hypergeometric(ngood, nbad * 3, nsample)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.hypergeometric, bad_ngood, nbad * 3, nsample)
        assert_raises(ValueError, rng.hypergeometric, ngood, bad_nbad * 3, nsample)
        assert_raises(ValueError, rng.hypergeometric, ngood, nbad * 3, bad_nsample_one)
        assert_raises(ValueError, rng.hypergeometric, ngood, nbad * 3, bad_nsample_two)

        rng = random.RandomState(self.seed)
        actual = rng.hypergeometric(ngood, nbad, nsample * 3)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.hypergeometric, bad_ngood, nbad, nsample * 3)
        assert_raises(ValueError, rng.hypergeometric, ngood, bad_nbad, nsample * 3)
        assert_raises(ValueError, rng.hypergeometric, ngood, nbad, bad_nsample_one * 3)
        assert_raises(ValueError, rng.hypergeometric, ngood, nbad, bad_nsample_two * 3)

    def test_logseries(self):
        p = [0.5]
        bad_p_one = [2]
        bad_p_two = [-1]
        desired = np.array([1, 1, 1])

        rng = random.RandomState(self.seed)
        actual = rng.logseries(p * 3)
        assert_array_equal(actual, desired)
        assert_raises(ValueError, rng.logseries, bad_p_one * 3)
        assert_raises(ValueError, rng.logseries, bad_p_two * 3)


@pytest.mark.skipif(IS_WASM, reason="can't start thread")
class TestThread:
    # make sure each state produces the same sequence even in threads
    seeds = range(4)

    def check_function(self, function, sz):
        from threading import Thread

        out1 = np.empty((len(self.seeds),) + sz)
        out2 = np.empty((len(self.seeds),) + sz)

        # threaded generation
        t = [Thread(target=function, args=(np.random.RandomState(s), o))
             for s, o in zip(self.seeds, out1)]
        [x.start() for x in t]
        [x.join() for x in t]

        # the same serial
        for s, o in zip(self.seeds, out2):
            function(np.random.RandomState(s), o)

        # these platforms change x87 fpu precision mode in threads
        if np.intp().dtype.itemsize == 4 and sys.platform == "win32":
            assert_array_almost_equal(out1, out2)
        else:
            assert_array_equal(out1, out2)

    def test_normal(self):
        def gen_random(state, out):
            out[...] = state.normal(size=10000)
        self.check_function(gen_random, sz=(10000,))

    def test_exp(self):
        def gen_random(state, out):
            out[...] = state.exponential(scale=np.ones((100, 1000)))
        self.check_function(gen_random, sz=(100, 1000))

    def test_multinomial(self):
        def gen_random(state, out):
            out[...] = state.multinomial(10, [1 / 6.] * 6, size=10000)
        self.check_function(gen_random, sz=(10000, 6))


# See Issue #4263
class TestSingleEltArrayInput:
    def _create_arrays(self):
        return np.array([2]), np.array([3]), np.array([4]), (1,)

    def test_one_arg_funcs(self):
        argOne, _, _, tgtShape = self._create_arrays()
        funcs = (np.random.exponential, np.random.standard_gamma,
                 np.random.chisquare, np.random.standard_t,
                 np.random.pareto, np.random.weibull,
                 np.random.power, np.random.rayleigh,
                 np.random.poisson, np.random.zipf,
                 np.random.geometric, np.random.logseries)

        probfuncs = (np.random.geometric, np.random.logseries)

        for func in funcs:
            if func in probfuncs:  # p < 1.0
                out = func(np.array([0.5]))

            else:
                out = func(argOne)

            assert_equal(out.shape, tgtShape)

    def test_two_arg_funcs(self):
        argOne, argTwo, _, tgtShape = self._create_arrays()
        funcs = (np.random.uniform, np.random.normal,
                 np.random.beta, np.random.gamma,
                 np.random.f, np.random.noncentral_chisquare,
                 np.random.vonmises, np.random.laplace,
                 np.random.gumbel, np.random.logistic,
                 np.random.lognormal, np.random.wald,
                 np.random.binomial, np.random.negative_binomial)

        probfuncs = (np.random.binomial, np.random.negative_binomial)

        for func in funcs:
            if func in probfuncs:  # p <= 1
                argTwo = np.array([0.5])

            else:
                argTwo = argTwo

            out = func(argOne, argTwo)
            assert_equal(out.shape, tgtShape)

            out = func(argOne[0], argTwo)
            assert_equal(out.shape, tgtShape)

            out = func(argOne, argTwo[0])
            assert_equal(out.shape, tgtShape)

    def test_randint(self):
        _, _, _, tgtShape = self._create_arrays()
        itype = [bool, np.int8, np.uint8, np.int16, np.uint16,
                 np.int32, np.uint32, np.int64, np.uint64]
        func = np.random.randint
        high = np.array([1])
        low = np.array([0])

        for dt in itype:
            out = func(low, high, dtype=dt)
            assert_equal(out.shape, tgtShape)

            out = func(low[0], high, dtype=dt)
            assert_equal(out.shape, tgtShape)

            out = func(low, high[0], dtype=dt)
            assert_equal(out.shape, tgtShape)

    def test_three_arg_funcs(self):
        argOne, argTwo, argThree, tgtShape = self._create_arrays()
        funcs = [np.random.noncentral_f, np.random.triangular,
                 np.random.hypergeometric]

        for func in funcs:
            out = func(argOne, argTwo, argThree)
            assert_equal(out.shape, tgtShape)

            out = func(argOne[0], argTwo, argThree)
            assert_equal(out.shape, tgtShape)

            out = func(argOne, argTwo[0], argThree)
            assert_equal(out.shape, tgtShape)
