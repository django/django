import gc
import sys
import time

from django.dispatch import Signal
from django.utils import unittest


if sys.platform.startswith('java'):
    def garbage_collect():
        # Some JVM GCs will execute finalizers in a different thread, meaning
        # we need to wait for that to complete before we go on looking for the
        # effects of that.
        gc.collect()
        time.sleep(0.1)
elif hasattr(sys, "pypy_version_info"):
    def garbage_collect():
        # Collecting weakreferences can take two collections on PyPy.
        gc.collect()
        gc.collect()
else:
    def garbage_collect():
        gc.collect()

def receiver_1_arg(val, **kwargs):
    return val

class Callable(object):
    def __call__(self, val, **kwargs):
        return val

    def a(self, val, **kwargs):
        return val

a_signal = Signal(providing_args=["val"])

class DispatcherTests(unittest.TestCase):
    """Test suite for dispatcher (barely started)"""

    def _testIsClean(self, signal):
        """Assert that everything has been cleaned up automatically"""
        self.assertEqual(signal.receivers, [])

        # force cleanup just in case
        signal.receivers = []

    def testExact(self):
        a_signal.connect(receiver_1_arg, sender=self)
        expected = [(receiver_1_arg,"test")]
        result = a_signal.send(sender=self, val="test")
        self.assertEqual(result, expected)
        a_signal.disconnect(receiver_1_arg, sender=self)
        self._testIsClean(a_signal)

    def testIgnoredSender(self):
        a_signal.connect(receiver_1_arg)
        expected = [(receiver_1_arg,"test")]
        result = a_signal.send(sender=self, val="test")
        self.assertEqual(result, expected)
        a_signal.disconnect(receiver_1_arg)
        self._testIsClean(a_signal)

    def testGarbageCollected(self):
        a = Callable()
        a_signal.connect(a.a, sender=self)
        expected = []
        del a
        garbage_collect()
        result = a_signal.send(sender=self, val="test")
        self.assertEqual(result, expected)
        self._testIsClean(a_signal)

    def testMultipleRegistration(self):
        a = Callable()
        a_signal.connect(a)
        a_signal.connect(a)
        a_signal.connect(a)
        a_signal.connect(a)
        a_signal.connect(a)
        a_signal.connect(a)
        result = a_signal.send(sender=self, val="test")
        self.assertEqual(len(result), 1)
        self.assertEqual(len(a_signal.receivers), 1)
        del a
        del result
        garbage_collect()
        self._testIsClean(a_signal)

    def testUidRegistration(self):
        def uid_based_receiver_1(**kwargs):
            pass

        def uid_based_receiver_2(**kwargs):
            pass

        a_signal.connect(uid_based_receiver_1, dispatch_uid = "uid")
        a_signal.connect(uid_based_receiver_2, dispatch_uid = "uid")
        self.assertEqual(len(a_signal.receivers), 1)
        a_signal.disconnect(dispatch_uid = "uid")
        self._testIsClean(a_signal)

    def testRobust(self):
        """Test the sendRobust function"""
        def fails(val, **kwargs):
            raise ValueError('this')
        a_signal.connect(fails)
        result = a_signal.send_robust(sender=self, val="test")
        err = result[0][1]
        self.assertTrue(isinstance(err, ValueError))
        self.assertEqual(err.args, ('this',))
        a_signal.disconnect(fails)
        self._testIsClean(a_signal)

    def testDisconnection(self):
        receiver_1 = Callable()
        receiver_2 = Callable()
        receiver_3 = Callable()
        a_signal.connect(receiver_1)
        a_signal.connect(receiver_2)
        a_signal.connect(receiver_3)
        a_signal.disconnect(receiver_1)
        del receiver_2
        garbage_collect()
        a_signal.disconnect(receiver_3)
        self._testIsClean(a_signal)
