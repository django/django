import sys, os
from django.utils.unittest import TestCase
from django.utils.six import StringIO
from django.core.management import call_command

class Bug19164Test(TestCase):
    """
    Test for bug #19164 -
    """
    def test_bug_19164(self):
        """Just make sure running the command don't raise the error"""
        out = StringIO()
        try:
            call_command('diffsettings', stdout=out) 
        except TypeError, ex:
            self.assertNotEqual(str(ex), '_setup() takes exactly 2 arguments (1 given)')
