from __future__ import print_function
from __future__ import absolute_import

import subprocess
import unittest

import greenlet
from . import _test_extension_cpp
from . import TestCase
from . import WIN

class CPPTests(TestCase):
    def test_exception_switch(self):
        greenlets = []
        for i in range(4):
            g = greenlet.greenlet(_test_extension_cpp.test_exception_switch)
            g.switch(i)
            greenlets.append(g)
        for i, g in enumerate(greenlets):
            self.assertEqual(g.switch(), i)

    def _do_test_unhandled_exception(self, target):
        import os
        import sys
        script = os.path.join(
            os.path.dirname(__file__),
            'fail_cpp_exception.py',
        )
        args = [sys.executable, script, target.__name__ if not isinstance(target, str) else target]
        __traceback_info__ = args
        with self.assertRaises(subprocess.CalledProcessError) as exc:
            subprocess.check_output(
                args,
                encoding='utf-8',
                stderr=subprocess.STDOUT
            )

        ex = exc.exception
        expected_exit = self.get_expected_returncodes_for_aborted_process()
        self.assertIn(ex.returncode, expected_exit)
        self.assertIn('fail_cpp_exception is running', ex.output)
        return ex.output


    def test_unhandled_nonstd_exception_aborts(self):
        # verify that plain unhandled throw aborts
        self._do_test_unhandled_exception(_test_extension_cpp.test_exception_throw_nonstd)

    def test_unhandled_std_exception_aborts(self):
        # verify that plain unhandled throw aborts
        self._do_test_unhandled_exception(_test_extension_cpp.test_exception_throw_std)

    @unittest.skipIf(WIN, "XXX: This does not crash on Windows")
    # Meaning the exception is getting lost somewhere...
    def test_unhandled_std_exception_as_greenlet_function_aborts(self):
        # verify that plain unhandled throw aborts
        output = self._do_test_unhandled_exception('run_as_greenlet_target')
        self.assertIn(
            # We really expect this to be prefixed with "greenlet: Unhandled C++ exception:"
            # as added by our handler for std::exception (see TUserGreenlet.cpp), but
            # that's not correct everywhere --- our handler never runs before std::terminate
            # gets called (for example, on arm32).
            'Thrown from an extension.',
            output
        )

    def test_unhandled_exception_in_greenlet_aborts(self):
        # verify that unhandled throw called in greenlet aborts too
        self._do_test_unhandled_exception('run_unhandled_exception_in_greenlet_aborts')


if __name__ == '__main__':
    unittest.main()
