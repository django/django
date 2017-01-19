import unittest

from django.utils import inspect


class Person:
    def no_arguments(self):
        return None

    def one_argument(self, something):
        return something

    def just_args(self, *args):
        return args

    def all_kinds(self, name, address='home', age=25, *args, **kwargs):
        return kwargs


class TestInspectMethods(unittest.TestCase):
    def test_get_func_full_args_no_arguments(self):
        self.assertEqual(inspect.get_func_full_args(Person.no_arguments), [])

    def test_get_func_full_args_one_argument(self):
        self.assertEqual(inspect.get_func_full_args(Person.one_argument), [('something',)])

    def test_get_func_full_args_all_arguments(self):
        arguments = [('name',), ('address', 'home'), ('age', 25), ('*args',), ('**kwargs',)]
        self.assertEqual(inspect.get_func_full_args(Person.all_kinds), arguments)

    def test_func_accepts_var_args_has_var_args(self):
        self.assertIs(inspect.func_accepts_var_args(Person.just_args), True)

    def test_func_accepts_var_args_no_var_args(self):
        self.assertIs(inspect.func_accepts_var_args(Person.one_argument), False)
