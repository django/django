from os import path
import pickle

import numpy as np


class TestNumPy2Compatibility:

    data_dir = path.join(path.dirname(__file__), "data")
    filename = path.join(data_dir, "numpy_2_0_array.pkl")

    def test_importable__core_stubs(self):
        """
        Checks if stubs for `numpy._core` are importable.
        """
        from numpy._core.multiarray import _reconstruct
        from numpy._core.umath import cos
        from numpy._core._multiarray_umath import exp
        from numpy._core._internal import ndarray
        from numpy._core._dtype import _construction_repr
        from numpy._core._dtype_ctypes import dtype_from_ctypes_type

    def test_unpickle_numpy_2_0_file(self):
        """
        Checks that NumPy 1.26 and pickle is able to load pickles
        created with NumPy 2.0 without errors/warnings.
        """
        with open(self.filename, mode="rb") as file:
            content = file.read()

        # Let's make sure that the pickle object we're loading
        # was built with NumPy 2.0.
        assert b"numpy._core.multiarray" in content

        arr = pickle.loads(content, encoding="latin1")

        assert isinstance(arr, np.ndarray)
        assert arr.shape == (73,) and arr.dtype == np.float64

    def test_numpy_load_numpy_2_0_file(self):
        """
        Checks that `numpy.load` for NumPy 1.26 is able to load pickles
        created with NumPy 2.0 without errors/warnings.
        """
        arr = np.load(self.filename, encoding="latin1", allow_pickle=True)

        assert isinstance(arr, np.ndarray)
        assert arr.shape == (73,) and arr.dtype == np.float64
