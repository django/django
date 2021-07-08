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

    @classmethod
    def cls_all_kinds(cls, name, address='home', age=25, *args, **kwargs):
        return kwargs


class TestInspectMethods(unittest.TestCase):
    def test_get_callable_parameters(self):
        self.assertIs(
            inspect._get_callable_parameters(Person.no_arguments),
            inspect._get_callable_parameters(Person.no_arguments),
        )
        self.assertIs(
            inspect._get_callable_parameters(Person().no_arguments),
            inspect._get_callable_parameters(Person().no_arguments),
        )

    def test_get_func_full_args_no_arguments(self):
        self.assertEqual(inspect.get_func_full_args(Person.no_arguments), [])
        self.assertEqual(inspect.get_func_full_args(Person().no_arguments), [])

    def test_get_func_full_args_one_argument(self):
        self.assertEqual(inspect.get_func_full_args(Person.one_argument), [('something',)])
        self.assertEqual(
            inspect.get_func_full_args(Person().one_argument),
            [('something',)],
        )

    def test_get_func_full_args_all_arguments_method(self):
        arguments = [('name',), ('address', 'home'), ('age', 25), ('*args',), ('**kwargs',)]
        self.assertEqual(inspect.get_func_full_args(Person.all_kinds), arguments)
        self.assertEqual(inspect.get_func_full_args(Person().all_kinds), arguments)

    def test_get_func_full_args_all_arguments_classmethod(self):
        arguments = [
            ('name',), ('address', 'home'), ('age', 25), ('*args',), ('**kwargs',),
        ]
        self.assertEqual(inspect.get_func_full_args(Person.cls_all_kinds), arguments)
        self.assertEqual(inspect.get_func_full_args(Person().cls_all_kinds), arguments)

    def test_func_accepts_var_args_has_var_args(self):
        self.assertIs(inspect.func_accepts_var_args(Person.just_args), True)
        self.assertIs(inspect.func_accepts_var_args(Person().just_args), True)

    def test_func_accepts_var_args_no_var_args(self):
        self.assertIs(inspect.func_accepts_var_args(Person.one_argument), False)
        self.assertIs(inspect.func_accepts_var_args(Person().one_argument), False)

    def test_method_has_no_args(self):
        self.assertIs(inspect.method_has_no_args(Person.no_arguments), True)
        self.assertIs(inspect.method_has_no_args(Person().no_arguments), True)
        self.assertIs(inspect.method_has_no_args(Person.one_argument), False)
        self.assertIs(inspect.method_has_no_args(Person().one_argument), False)

    def test_func_supports_parameter(self):
        self.assertIs(inspect.func_supports_parameter(Person.all_kinds, 'address'), True)
        self.assertIs(
            inspect.func_supports_parameter(Person().all_kinds, 'address'),
            True,
        )
        self.assertIs(inspect.func_supports_parameter(Person.all_kinds, 'zone'), False)
        self.assertIs(
            inspect.func_supports_parameter(Person().all_kinds, 'zone'),
            False,
        )

    def test_func_accepts_kwargs(self):
        self.assertIs(inspect.func_accepts_kwargs(Person.just_args), False)
        self.assertIs(inspect.func_accepts_kwargs(Person().just_args), False)
        self.assertIs(inspect.func_accepts_kwargs(Person.all_kinds), True)
        self.assertIs(inspect.func_accepts_kwargs(Person().just_args), False)
