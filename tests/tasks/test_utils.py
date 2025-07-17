import datetime
import subprocess

from django.tasks import utils
from django.test import SimpleTestCase

from . import tasks as test_tasks


class IsModuleLevelFunctionTestCase(SimpleTestCase):
    @classmethod
    def _class_method(cls) -> None:
        return None

    @staticmethod
    def _static_method() -> None:
        return None

    def test_builtin(self):
        self.assertIs(utils.is_module_level_function(any), False)
        self.assertIs(utils.is_module_level_function(isinstance), False)

    def test_from_module(self):
        self.assertIs(utils.is_module_level_function(subprocess.run), True)
        self.assertIs(utils.is_module_level_function(subprocess.check_output), True)
        self.assertIs(utils.is_module_level_function(test_tasks.noop_task.func), True)

    def test_private_function(self):
        def private_function():
            pass

        self.assertIs(utils.is_module_level_function(private_function), False)

    def test_coroutine(self):
        self.assertIs(
            utils.is_module_level_function(test_tasks.noop_task_async.func), True
        )

    def test_method(self):
        self.assertIs(utils.is_module_level_function(self.test_method), False)
        self.assertIs(utils.is_module_level_function(self.setUp), False)

    def test_unbound_method(self):
        self.assertIs(
            utils.is_module_level_function(self.__class__.test_unbound_method), True
        )
        self.assertIs(utils.is_module_level_function(self.__class__.setUp), True)

    def test_lambda(self):
        self.assertIs(utils.is_module_level_function(lambda: True), False)

    def test_class_and_static_method(self):
        self.assertIs(utils.is_module_level_function(self._static_method), True)
        self.assertIs(utils.is_module_level_function(self._class_method), False)


class JSONNormalizeTestCase(SimpleTestCase):
    def test_round_trip(self):
        self.assertEqual(utils.json_normalize({}), {})
        self.assertEqual(utils.json_normalize([]), [])
        self.assertEqual(utils.json_normalize(()), [])
        self.assertEqual(utils.json_normalize({"foo": ()}), {"foo": []})

    def test_encode_error(self):
        for example in [self, any, datetime.datetime.now()]:
            with self.subTest(example):
                self.assertRaises(TypeError, utils.json_normalize, example)


class ExceptionTracebackTestCase(SimpleTestCase):
    def test_literal_exception(self):
        self.assertEqual(
            utils.get_exception_traceback(ValueError("Failure")),
            "ValueError: Failure\n",
        )

    def test_exception(self):
        try:
            1 / 0
        except ZeroDivisionError as e:
            traceback = utils.get_exception_traceback(e)
            self.assertIn("ZeroDivisionError: division by zero", traceback)
        else:
            self.fail("ZeroDivisionError not raised")

    def test_complex_exception(self):
        try:
            {}[datetime.datetime.now()]
        except KeyError as e:
            traceback = utils.get_exception_traceback(e)
            self.assertIn("KeyError: datetime.datetime", traceback)
        else:
            self.fail("KeyError not raised")
