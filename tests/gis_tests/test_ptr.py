import ctypes
from unittest import mock

from django.contrib.gis.ptr import CPointerBase
from django.test import SimpleTestCase


class CPointerBaseTests(SimpleTestCase):

    def test(self):
        destructor_mock = mock.Mock()

        class NullPointerException(Exception):
            pass

        class FakeGeom1(CPointerBase):
            null_ptr_exception_class = NullPointerException

        class FakeGeom2(FakeGeom1):
            ptr_type = ctypes.POINTER(ctypes.c_float)
            destructor = destructor_mock

        fg1 = FakeGeom1()
        fg2 = FakeGeom2()

        # These assignments are OK. None is allowed because it's equivalent
        # to the NULL pointer.
        fg1.ptr = fg1.ptr_type()
        fg1.ptr = None
        fg2.ptr = fg2.ptr_type(ctypes.c_float(5.23))
        fg2.ptr = None

        # Because pointers have been set to NULL, an exception is raised on
        # access. Raising an exception is preferable to a segmentation fault
        # that commonly occurs when a C method is given a NULL reference.
        for fg in (fg1, fg2):
            with self.assertRaises(NullPointerException):
                fg.ptr

        # Anything that's either not None or the acceptable pointer type
        # results in a TypeError when trying to assign it to the `ptr` property.
        # Thus, memory addresses (integers) and pointers of the incorrect type
        # (in `bad_ptrs`) aren't allowed.
        bad_ptrs = (5, ctypes.c_char_p(b'foobar'))
        for bad_ptr in bad_ptrs:
            for fg in (fg1, fg2):
                with self.assertRaisesMessage(TypeError, 'Incompatible pointer type'):
                    fg.ptr = bad_ptr

        # Object can be deleted without a destructor set.
        fg = FakeGeom1()
        fg.ptr = fg.ptr_type(1)
        del fg

        # A NULL pointer isn't passed to the destructor.
        fg = FakeGeom2()
        fg.ptr = None
        del fg
        self.assertFalse(destructor_mock.called)

        # The destructor is called if set.
        fg = FakeGeom2()
        ptr = fg.ptr_type(ctypes.c_float(1.))
        fg.ptr = ptr
        del fg
        destructor_mock.assert_called_with(ptr)
