from unittest import skipIf
import warnings

from django.conf import settings
from django.test import SimpleTestCase

from ..utils import render, setup

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
        output = render(
            'numpy-array-index01',
            {'var': numpy.array(["first item", "second item"])},
        )
        self.assertEqual(output, 'second item')

    @setup({'numpy-array-index02': '{{ var.5 }}'})
    def test_numpy_array_index02(self):
        """
        Fail silently when the array index is out of range.
        """
        output = render(
            'numpy-array-index02',
            {'var': numpy.array(["first item", "second item"])},
        )
        if settings.TEMPLATE_STRING_IF_INVALID:
            self.assertEqual(output, 'INVALID')
        else:
            self.assertEqual(output, '')
