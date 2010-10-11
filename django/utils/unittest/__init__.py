"""
unittest2

unittest2 is a backport of the new features added to the unittest testing
framework in Python 2.7. It is tested to run on Python 2.4 - 2.6.

To use unittest2 instead of unittest simply replace ``import unittest`` with
``import unittest2``.


Copyright (c) 1999-2003 Steve Purcell
Copyright (c) 2003-2010 Python Software Foundation
This module is free software, and you may redistribute it and/or modify
it under the same terms as Python itself, so long as this copyright message
and disclaimer are retained in their original form.

IN NO EVENT SHALL THE AUTHOR BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,
SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OF
THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH
DAMAGE.

THE AUTHOR SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS IS" BASIS,
AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,
SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
"""

import sys

# Django hackery to load the appropriate version of unittest

if sys.version_info >= (2,7):
    # unittest2 features are native in Python 2.7
    from unittest import *
else:
    try:
        # check the system path first
        from unittest2 import *
    except ImportError:
        # otherwise use our bundled version
        __all__ = ['TestResult', 'TestCase', 'TestSuite',
                   'TextTestRunner', 'TestLoader', 'FunctionTestCase', 'main',
                   'defaultTestLoader', 'SkipTest', 'skip', 'skipIf', 'skipUnless',
                   'expectedFailure', 'TextTestResult', '__version__', 'collector']

        __version__ = '0.5.1'

        # Expose obsolete functions for backwards compatibility
        __all__.extend(['getTestCaseNames', 'makeSuite', 'findTestCases'])


        from django.utils.unittest.collector import collector
        from django.utils.unittest.result import TestResult
        from django.utils.unittest.case import \
            TestCase, FunctionTestCase, SkipTest, skip, skipIf,\
            skipUnless, expectedFailure

        from django.utils.unittest.suite import BaseTestSuite, TestSuite
        from django.utils.unittest.loader import \
            TestLoader, defaultTestLoader, makeSuite, getTestCaseNames,\
            findTestCases

        from django.utils.unittest.main import TestProgram, main, main_
        from django.utils.unittest.runner import TextTestRunner, TextTestResult

        try:
            from django.utils.unittest.signals import\
                installHandler, registerResult, removeResult, removeHandler
        except ImportError:
            # Compatibility with platforms that don't have the signal module
            pass
        else:
            __all__.extend(['installHandler', 'registerResult', 'removeResult',
                            'removeHandler'])

        # deprecated
        _TextTestResult = TextTestResult

        __unittest = True
