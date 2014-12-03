from django.test import SimpleTestCase

from .utils import render, setup


class BuiltinsTests(SimpleTestCase):

    @setup({'builtins01': '{{ True }}'})
    def test_builtins01(self):
        self.assertEqual(render('builtins01'), 'True')

    @setup({'builtins02': '{{ False }}'})
    def test_builtins02(self):
        self.assertEqual(render('builtins02'), 'False')

    @setup({'builtins03': '{{ None }}'})
    def test_builtins03(self):
        self.assertEqual(render('builtins03'), 'None')
