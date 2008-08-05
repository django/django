from django.dispatch.dispatcher import *
from django.dispatch import dispatcher, robust
import unittest
import copy
import sys
import gc

if sys.platform.startswith('java'):
    def garbage_collect():
        """Run the garbage collector and wait a bit to let it do his work"""
        import time
        gc.collect()
        time.sleep(0.1)
else:
    def garbage_collect():
        gc.collect()

def x(a):
    return a

class Dummy(object):
    pass

class Callable(object):
    def __call__(self, a):
        return a
    
    def a(self, a):
        return a

class DispatcherTests(unittest.TestCase):
    """Test suite for dispatcher (barely started)"""
    
    def setUp(self):
        # track the initial state, since it's possible that others have bleed receivers in
        garbage_collect()
        self.sendersBack = copy.copy(dispatcher.sendersBack)
        self.connections = copy.copy(dispatcher.connections)
        self.senders = copy.copy(dispatcher.senders)
    
    def _testIsClean(self):
        """Assert that everything has been cleaned up automatically"""
        self.assertEqual(dispatcher.sendersBack, self.sendersBack)
        self.assertEqual(dispatcher.connections, self.connections)
        self.assertEqual(dispatcher.senders, self.senders)
    
    def testExact(self):
        a = Dummy()
        signal = 'this'
        connect(x, signal, a)
        expected = [(x,a)]
        result = send('this',a, a=a)
        self.assertEqual(result, expected)
        disconnect(x, signal, a)
        self.assertEqual(list(getAllReceivers(a,signal)), [])
        self._testIsClean()
    
    def testAnonymousSend(self):
        a = Dummy()
        signal = 'this'
        connect(x, signal)
        expected = [(x,a)]
        result = send(signal,None, a=a)
        self.assertEqual(result, expected)
        disconnect(x, signal)
        self.assertEqual(list(getAllReceivers(None,signal)), [])
        self._testIsClean()
    
    def testAnyRegistration(self):
        a = Dummy()
        signal = 'this'
        connect(x, signal, Any)
        expected = [(x,a)]
        result = send('this',object(), a=a)
        self.assertEqual(result, expected)
        disconnect(x, signal, Any)
        expected = []
        result = send('this',object(), a=a)
        self.assertEqual(result, expected)
        self.assertEqual(list(getAllReceivers(Any,signal)), [])
        
        self._testIsClean()
    
    def testAnyRegistration2(self):
        a = Dummy()
        signal = 'this'
        connect(x, Any, a)
        expected = [(x,a)]
        result = send('this',a, a=a)
        self.assertEqual(result, expected)
        disconnect(x, Any, a)
        self.assertEqual(list(getAllReceivers(a,Any)), [])
        self._testIsClean()
    
    def testGarbageCollected(self):
        a = Callable()
        b = Dummy()
        signal = 'this'
        connect(a.a, signal, b)
        expected = []
        del a
        garbage_collect()
        result = send('this',b, a=b)
        self.assertEqual(result, expected)
        self.assertEqual(list(getAllReceivers(b,signal)), [])
        self._testIsClean()
    
    def testGarbageCollectedObj(self):
        class x:
            def __call__(self, a):
                return a
        a = Callable()
        b = Dummy()
        signal = 'this'
        connect(a, signal, b)
        expected = []
        del a
        garbage_collect()
        result = send('this',b, a=b)
        self.assertEqual(result, expected)
        self.assertEqual(list(getAllReceivers(b,signal)), [])
        self._testIsClean()

    
    def testMultipleRegistration(self):
        a = Callable()
        b = Dummy()
        signal = 'this'
        connect(a, signal, b)
        connect(a, signal, b)
        connect(a, signal, b)
        connect(a, signal, b)
        connect(a, signal, b)
        connect(a, signal, b)
        result = send('this',b, a=b)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(list(getAllReceivers(b,signal))), 1)
        del a
        del b
        del result
        garbage_collect()
        self._testIsClean()
    
    def testRobust(self):
        """Test the sendRobust function"""
        def fails():
            raise ValueError('this')
        a = object()
        signal = 'this'
        connect(fails, Any, a)
        result = robust.sendRobust('this',a, a=a)
        err = result[0][1]
        self.assert_(isinstance(err, ValueError))
        self.assertEqual(err.args, ('this',))

def getSuite():
    return unittest.makeSuite(DispatcherTests,'test')

if __name__ == "__main__":
    unittest.main()
