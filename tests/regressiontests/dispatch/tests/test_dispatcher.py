from django.dispatch.dispatcher import *
from django.dispatch import dispatcher, robust

import unittest, pprint, copy

def x(a):
    return a

class Dummy( object ):
    pass


class Callable(object):

    def __call__( self, a ):
        return a

    def a( self, a ):
        return a


class DispatcherTests(unittest.TestCase):
    """Test suite for dispatcher (barely started)"""

    def setUp(self):
        # track the initial state, since it's possible that others have bleed receivers in
        self.sendersBack = copy.copy(dispatcher.sendersBack)
        self.connections = copy.copy(dispatcher.connections)
        self.senders = copy.copy(dispatcher.senders)
        
    def _isclean( self ):
        """Assert that everything has been cleaned up automatically"""
        self.assertEqual(dispatcher.sendersBack, self.sendersBack)
        self.assertEqual(dispatcher.connections, self.connections)
        self.assertEqual(dispatcher.senders, self.senders)
    
    def testExact (self):
        a = Dummy()
        signal = 'this'
        connect( x, signal, a )
        expected = [(x,a)]
        result = send('this',a, a=a)
        self.assertEqual(result, expected)
        disconnect( x, signal, a )
        self.assertEqual(len(list(getAllReceivers(a,signal))), 0)
        self._isclean()

    def testAnonymousSend(self):
        a = Dummy()
        signal = 'this'
        connect( x, signal )
        expected = [(x,a)]
        result = send(signal,None, a=a)
        assert result == expected,"""Send didn't return expected result:\n\texpected:%s\n\tgot:%s"""% (expected, result)
        disconnect( x, signal )
        assert len(list(getAllReceivers(None,signal))) == 0
        self._isclean()

    def testAnyRegistration(self):
        a = Dummy()
        signal = 'this'
        connect( x, signal, Any )
        expected = [(x,a)]
        result = send('this',object(), a=a)
        assert result == expected,"""Send didn't return expected result:\n\texpected:%s\n\tgot:%s"""% (expected, result)
        disconnect( x, signal, Any )
        expected = []
        result = send('this',object(), a=a)
        assert result == expected,"""Send didn't return expected result:\n\texpected:%s\n\tgot:%s"""% (expected, result)
        assert len(list(getAllReceivers(Any,signal))) == 0

        self._isclean()
        
    def testAnyRegistration2(self):
        a = Dummy()
        signal = 'this'
        connect( x, Any, a )
        expected = [(x,a)]
        result = send('this',a, a=a)
        assert result == expected,"""Send didn't return expected result:\n\texpected:%s\n\tgot:%s"""% (expected, result)
        disconnect( x, Any, a )
        assert len(list(getAllReceivers(a,Any))) == 0
        self._isclean()

    def testGarbageCollected(self):
        a = Callable()
        b = Dummy()
        signal = 'this'
        connect( a.a, signal, b )
        expected = []
        del a
        result = send('this',b, a=b)
        assert result == expected,"""Send didn't return expected result:\n\texpected:%s\n\tgot:%s"""% (expected, result)
        assert len(list(getAllReceivers(b,signal))) == 0, """Remaining handlers: %s"""%(getAllReceivers(b,signal),)
        self._isclean()

    def testGarbageCollectedObj(self):
        class x:
            def __call__( self, a ):
                return a
        a = Callable()
        b = Dummy()
        signal = 'this'
        connect( a, signal, b )
        expected = []
        del a
        result = send('this',b, a=b)
        self.assertEqual(result, expected)
        self.assertEqual(len(list(getAllReceivers(b,signal))), 0)
        self._isclean()


    def testMultipleRegistration(self):
        a = Callable()
        b = Dummy()
        signal = 'this'
        connect( a, signal, b )
        connect( a, signal, b )
        connect( a, signal, b )
        connect( a, signal, b )
        connect( a, signal, b )
        connect( a, signal, b )
        result = send('this',b, a=b)
        assert len( result ) == 1, result
        assert len(list(getAllReceivers(b,signal))) == 1, """Remaining handlers: %s"""%(getAllReceivers(b,signal),)
        del a
        del b
        del result
        self._isclean()

    def testRobust( self ):
        """Test the sendRobust function"""
        def fails( ):
            raise ValueError( 'this' )
        a = object()
        signal = 'this'
        connect( fails, Any, a )
        result = robust.sendRobust('this',a, a=a)
        err = result[0][1]
        assert isinstance( err, ValueError )
        assert err.args == ('this',)

def getSuite():
    return unittest.makeSuite(DispatcherTests,'test')
        
if __name__ == "__main__":
    unittest.main ()
