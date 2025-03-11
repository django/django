"""
Tests for detecting redefinition of builtins.
"""
from pyflakes import messages as m
from pyflakes.test.harness import TestCase


class TestBuiltins(TestCase):

    def test_builtin_unbound_local(self):
        self.flakes('''
        def foo():
            a = range(1, 10)
            range = a
            return range

        foo()

        print(range)
        ''', m.UndefinedLocal)

    def test_global_shadowing_builtin(self):
        self.flakes('''
        def f():
            global range
            range = None
            print(range)

        f()
        ''')
