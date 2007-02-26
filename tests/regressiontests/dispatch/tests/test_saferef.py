from django.dispatch.saferef import *

import unittest
class Test1( object):
    def x( self ):
        pass
def test2(obj):
    pass
class Test2( object ):
    def __call__( self, obj ):
        pass
class Tester (unittest.TestCase):
    def setUp (self):
        ts = []
        ss = []
        for x in xrange( 5000 ):
            t = Test1()
            ts.append( t)
            s = safeRef(t.x, self._closure )
            ss.append( s)
        ts.append( test2 )
        ss.append( safeRef(test2, self._closure) )
        for x in xrange( 30 ):
            t = Test2()
            ts.append( t)
            s = safeRef(t, self._closure )
            ss.append( s)
        self.ts = ts
        self.ss = ss
        self.closureCount = 0
    def tearDown( self ):
        del self.ts
        del self.ss
    def testIn(self):
        """Test the "in" operator for safe references (cmp)"""
        for t in self.ts[:50]:
            assert safeRef(t.x) in self.ss
    def testValid(self):
        """Test that the references are valid (return instance methods)"""
        for s in self.ss:
            assert s()
    def testShortCircuit (self):
        """Test that creation short-circuits to reuse existing references"""
        sd = {}
        for s in self.ss:
            sd[s] = 1
        for t in self.ts:
            if hasattr( t, 'x'):
                assert sd.has_key( safeRef(t.x))
            else:
                assert sd.has_key( safeRef(t))
    def testRepresentation (self):
        """Test that the reference object's representation works

        XXX Doesn't currently check the results, just that no error
            is raised
        """
        repr( self.ss[-1] )
        
    def test(self):
        self.closureCount = 0
        wholeI = len(self.ts)
        for i in xrange( len(self.ts)-1, -1, -1):
            del self.ts[i]
            if wholeI-i != self.closureCount:
                """Unexpected number of items closed, expected %s, got %s closed"""%( wholeI-i,self.closureCount)
        
    def _closure(self, ref):
        """Dumb utility mechanism to increment deletion counter"""
        self.closureCount +=1

def getSuite():
    return unittest.makeSuite(Tester,'test')

if __name__ == "__main__":
    unittest.main ()
