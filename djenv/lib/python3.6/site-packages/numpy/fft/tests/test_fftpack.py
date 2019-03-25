from __future__ import division, absolute_import, print_function

import numpy as np
from numpy.random import random
from numpy.testing import (
        assert_array_almost_equal, assert_array_equal, assert_raises,
        )
import threading
import sys
if sys.version_info[0] >= 3:
    import queue
else:
    import Queue as queue


def fft1(x):
    L = len(x)
    phase = -2j*np.pi*(np.arange(L)/float(L))
    phase = np.arange(L).reshape(-1, 1) * phase
    return np.sum(x*np.exp(phase), axis=1)


class TestFFTShift(object):

    def test_fft_n(self):
        assert_raises(ValueError, np.fft.fft, [1, 2, 3], 0)


class TestFFT1D(object):

    def test_fft(self):
        x = random(30) + 1j*random(30)
        assert_array_almost_equal(fft1(x), np.fft.fft(x))
        assert_array_almost_equal(fft1(x) / np.sqrt(30),
                                  np.fft.fft(x, norm="ortho"))

    def test_ifft(self):
        x = random(30) + 1j*random(30)
        assert_array_almost_equal(x, np.fft.ifft(np.fft.fft(x)))
        assert_array_almost_equal(
            x, np.fft.ifft(np.fft.fft(x, norm="ortho"), norm="ortho"))

    def test_fft2(self):
        x = random((30, 20)) + 1j*random((30, 20))
        assert_array_almost_equal(np.fft.fft(np.fft.fft(x, axis=1), axis=0),
                                  np.fft.fft2(x))
        assert_array_almost_equal(np.fft.fft2(x) / np.sqrt(30 * 20),
                                  np.fft.fft2(x, norm="ortho"))

    def test_ifft2(self):
        x = random((30, 20)) + 1j*random((30, 20))
        assert_array_almost_equal(np.fft.ifft(np.fft.ifft(x, axis=1), axis=0),
                                  np.fft.ifft2(x))
        assert_array_almost_equal(np.fft.ifft2(x) * np.sqrt(30 * 20),
                                  np.fft.ifft2(x, norm="ortho"))

    def test_fftn(self):
        x = random((30, 20, 10)) + 1j*random((30, 20, 10))
        assert_array_almost_equal(
            np.fft.fft(np.fft.fft(np.fft.fft(x, axis=2), axis=1), axis=0),
            np.fft.fftn(x))
        assert_array_almost_equal(np.fft.fftn(x) / np.sqrt(30 * 20 * 10),
                                  np.fft.fftn(x, norm="ortho"))

    def test_ifftn(self):
        x = random((30, 20, 10)) + 1j*random((30, 20, 10))
        assert_array_almost_equal(
            np.fft.ifft(np.fft.ifft(np.fft.ifft(x, axis=2), axis=1), axis=0),
            np.fft.ifftn(x))
        assert_array_almost_equal(np.fft.ifftn(x) * np.sqrt(30 * 20 * 10),
                                  np.fft.ifftn(x, norm="ortho"))

    def test_rfft(self):
        x = random(30)
        for n in [x.size, 2*x.size]:
            for norm in [None, 'ortho']:
                assert_array_almost_equal(
                    np.fft.fft(x, n=n, norm=norm)[:(n//2 + 1)],
                    np.fft.rfft(x, n=n, norm=norm))
            assert_array_almost_equal(np.fft.rfft(x, n=n) / np.sqrt(n),
                                      np.fft.rfft(x, n=n, norm="ortho"))

    def test_irfft(self):
        x = random(30)
        assert_array_almost_equal(x, np.fft.irfft(np.fft.rfft(x)))
        assert_array_almost_equal(
            x, np.fft.irfft(np.fft.rfft(x, norm="ortho"), norm="ortho"))

    def test_rfft2(self):
        x = random((30, 20))
        assert_array_almost_equal(np.fft.fft2(x)[:, :11], np.fft.rfft2(x))
        assert_array_almost_equal(np.fft.rfft2(x) / np.sqrt(30 * 20),
                                  np.fft.rfft2(x, norm="ortho"))

    def test_irfft2(self):
        x = random((30, 20))
        assert_array_almost_equal(x, np.fft.irfft2(np.fft.rfft2(x)))
        assert_array_almost_equal(
            x, np.fft.irfft2(np.fft.rfft2(x, norm="ortho"), norm="ortho"))

    def test_rfftn(self):
        x = random((30, 20, 10))
        assert_array_almost_equal(np.fft.fftn(x)[:, :, :6], np.fft.rfftn(x))
        assert_array_almost_equal(np.fft.rfftn(x) / np.sqrt(30 * 20 * 10),
                                  np.fft.rfftn(x, norm="ortho"))

    def test_irfftn(self):
        x = random((30, 20, 10))
        assert_array_almost_equal(x, np.fft.irfftn(np.fft.rfftn(x)))
        assert_array_almost_equal(
            x, np.fft.irfftn(np.fft.rfftn(x, norm="ortho"), norm="ortho"))

    def test_hfft(self):
        x = random(14) + 1j*random(14)
        x_herm = np.concatenate((random(1), x, random(1)))
        x = np.concatenate((x_herm, x[::-1].conj()))
        assert_array_almost_equal(np.fft.fft(x), np.fft.hfft(x_herm))
        assert_array_almost_equal(np.fft.hfft(x_herm) / np.sqrt(30),
                                  np.fft.hfft(x_herm, norm="ortho"))

    def test_ihttf(self):
        x = random(14) + 1j*random(14)
        x_herm = np.concatenate((random(1), x, random(1)))
        x = np.concatenate((x_herm, x[::-1].conj()))
        assert_array_almost_equal(x_herm, np.fft.ihfft(np.fft.hfft(x_herm)))
        assert_array_almost_equal(
            x_herm, np.fft.ihfft(np.fft.hfft(x_herm, norm="ortho"),
                                 norm="ortho"))

    def test_all_1d_norm_preserving(self):
        # verify that round-trip transforms are norm-preserving
        x = random(30)
        x_norm = np.linalg.norm(x)
        n = x.size * 2
        func_pairs = [(np.fft.fft, np.fft.ifft),
                      (np.fft.rfft, np.fft.irfft),
                      # hfft: order so the first function takes x.size samples
                      #       (necessary for comparison to x_norm above)
                      (np.fft.ihfft, np.fft.hfft),
                      ]
        for forw, back in func_pairs:
            for n in [x.size, 2*x.size]:
                for norm in [None, 'ortho']:
                    tmp = forw(x, n=n, norm=norm)
                    tmp = back(tmp, n=n, norm=norm)
                    assert_array_almost_equal(x_norm,
                                              np.linalg.norm(tmp))

class TestFFTThreadSafe(object):
    threads = 16
    input_shape = (800, 200)

    def _test_mtsame(self, func, *args):
        def worker(args, q):
            q.put(func(*args))

        q = queue.Queue()
        expected = func(*args)

        # Spin off a bunch of threads to call the same function simultaneously
        t = [threading.Thread(target=worker, args=(args, q))
             for i in range(self.threads)]
        [x.start() for x in t]

        [x.join() for x in t]
        # Make sure all threads returned the correct value
        for i in range(self.threads):
            assert_array_equal(q.get(timeout=5), expected,
                'Function returned wrong value in multithreaded context')

    def test_fft(self):
        a = np.ones(self.input_shape) * 1+0j
        self._test_mtsame(np.fft.fft, a)

    def test_ifft(self):
        a = np.ones(self.input_shape) * 1+0j
        self._test_mtsame(np.fft.ifft, a)

    def test_rfft(self):
        a = np.ones(self.input_shape)
        self._test_mtsame(np.fft.rfft, a)

    def test_irfft(self):
        a = np.ones(self.input_shape) * 1+0j
        self._test_mtsame(np.fft.irfft, a)
