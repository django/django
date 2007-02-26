from django.dispatch.robustapply import *

import unittest
def noArgument():
    pass
def oneArgument (blah):
    pass
def twoArgument(blah, other):
    pass
class TestCases( unittest.TestCase ):
    def test01( self ):
        robustApply(noArgument )
    def test02( self ):
        self.assertRaises( TypeError, robustApply, noArgument, "this" )
    def test03( self ):
        self.assertRaises( TypeError, robustApply, oneArgument )
    def test04( self ):
        """Raise error on duplication of a particular argument"""
        self.assertRaises( TypeError, robustApply, oneArgument, "this", blah = "that" )

def getSuite():
    return unittest.makeSuite(TestCases,'test')


if __name__ == "__main__":
    unittest.main()
    
