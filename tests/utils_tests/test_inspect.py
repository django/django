import subprocess
import unittest
from typing import TYPE_CHECKING

from django.shortcuts import aget_object_or_404
from django.utils import inspect
from django.utils.version import PY314

if TYPE_CHECKING:
    from django.utils.safestring import SafeString


class Person:
    def no_arguments(self):
        return None

    def one_argument(self, something):
        return something

    def just_args(self, *args):
        return args

    def all_kinds(self, name, address="home", age=25, *args, **kwargs):
        return kwargs

    @classmethod
    def cls_all_kinds(cls, name, address="home", age=25, *args, **kwargs):
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
        self.assertEqual(
            inspect.get_func_full_args(Person.one_argument), [("something",)]
        )
        self.assertEqual(
            inspect.get_func_full_args(Person().one_argument),
            [("something",)],
        )

    def test_get_func_full_args_all_arguments_method(self):
        arguments = [
            ("name",),
            ("address", "home"),
            ("age", 25),
            ("*args",),
            ("**kwargs",),
        ]
        self.assertEqual(inspect.get_func_full_args(Person.all_kinds), arguments)
        self.assertEqual(inspect.get_func_full_args(Person().all_kinds), arguments)

    def test_get_func_full_args_all_arguments_classmethod(self):
        arguments = [
            ("name",),
            ("address", "home"),
            ("age", 25),
            ("*args",),
            ("**kwargs",),
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
        self.assertIs(
            inspect.func_supports_parameter(Person.all_kinds, "address"), True
        )
        self.assertIs(
            inspect.func_supports_parameter(Person().all_kinds, "address"),
            True,
        )
        self.assertIs(inspect.func_supports_parameter(Person.all_kinds, "zone"), False)
        self.assertIs(
            inspect.func_supports_parameter(Person().all_kinds, "zone"),
            False,
        )

    def test_func_accepts_kwargs(self):
        self.assertIs(inspect.func_accepts_kwargs(Person.just_args), False)
        self.assertIs(inspect.func_accepts_kwargs(Person().just_args), False)
        self.assertIs(inspect.func_accepts_kwargs(Person.all_kinds), True)
        self.assertIs(inspect.func_accepts_kwargs(Person().just_args), False)

    @unittest.skipUnless(PY314, "Deferred annotations are Python 3.14+ only")
    def test_func_accepts_kwargs_deferred_annotations(self):

        def func_with_annotations(self, name: str, complex: SafeString) -> None:
            pass

        # Inspection fails with deferred annotations with python 3.14+. Earlier
        # Python versions trigger the NameError on module initialization.
        self.assertIs(inspect.func_accepts_kwargs(func_with_annotations), False)


class IsModuleLevelFunctionTestCase(unittest.TestCase):
    @classmethod
    def _class_method(cls) -> None:
        return None

    @staticmethod
    def _static_method() -> None:
        return None

    def test_builtin(self):
        self.assertIs(inspect.is_module_level_function(any), False)
        self.assertIs(inspect.is_module_level_function(isinstance), False)

    def test_from_module(self):
        self.assertIs(inspect.is_module_level_function(subprocess.run), True)
        self.assertIs(inspect.is_module_level_function(subprocess.check_output), True)
        self.assertIs(
            inspect.is_module_level_function(inspect.is_module_level_function), True
        )

    def test_private_function(self):
        def private_function():
            pass

        self.assertIs(inspect.is_module_level_function(private_function), False)

    def test_coroutine(self):
        self.assertIs(inspect.is_module_level_function(aget_object_or_404), True)

    def test_method(self):
        self.assertIs(inspect.is_module_level_function(self.test_method), False)
        self.assertIs(inspect.is_module_level_function(self.setUp), False)

    def test_unbound_method(self):
        self.assertIs(
            inspect.is_module_level_function(self.__class__.test_unbound_method), True
        )
        self.assertIs(inspect.is_module_level_function(self.__class__.setUp), True)

    def test_lambda(self):
        self.assertIs(inspect.is_module_level_function(lambda: True), False)

    def test_class_and_static_method(self):
        self.assertIs(inspect.is_module_level_function(self._static_method), True)
        self.assertIs(inspect.is_module_level_function(self._class_method), False)
