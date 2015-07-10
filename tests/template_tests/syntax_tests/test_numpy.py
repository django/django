import warnings
from unittest import skipIf

from django.test import SimpleTestCase

from ..utils import setup

try:
    import numpy
except ImportError:
    numpy = False


@skipIf(numpy is False, "Numpy must be installed to run these tests.")
class NumpyTests(SimpleTestCase):
    # Ignore numpy deprecation warnings (#23890)
    warnings.filterwarnings(
        "ignore",
        "Using a non-integer number instead of an "
        "integer will result in an error in the future",
        DeprecationWarning
    )

    @setup({'numpy-array-index01': '{{ var.1 }}'})
    def test_numpy_array_index01(self):
        """
        Numpy's array-index syntax allows a template to access a certain
        item of a subscriptable object.
        """
        output = self.engine.render_to_string(
            'numpy-array-index01',
            {'var': numpy.array(["first item", "second item"])},
        )
        self.assertEqual(output, 'second item')

    @setup({'numpy-array-index02': '{{ var.5 }}'})
    def test_numpy_array_index02(self):
        """
        Fail silently when the array index is out of range.
        """
        output = self.engine.render_to_string(
            'numpy-array-index02',
            {'var': numpy.array(["first item", "second item"])},
        )
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')
