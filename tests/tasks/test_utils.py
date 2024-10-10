import datetime
import hashlib
import optparse
import subprocess
from typing import List
from unittest.mock import Mock

from django.core.exceptions import ImproperlyConfigured
from django.tasks import utils
from django.tasks.exceptions import InvalidTaskError
from django.test import SimpleTestCase

from . import tasks as test_tasks


class IsGlobalFunctionTestCase(SimpleTestCase):
    def test_builtin(self):
        self.assertFalse(utils.is_global_function(any))
        self.assertFalse(utils.is_global_function(isinstance))

    def test_from_module(self):
        self.assertTrue(utils.is_global_function(subprocess.run))
        self.assertTrue(utils.is_global_function(subprocess.check_output))
        self.assertTrue(utils.is_global_function(test_tasks.noop_task.func))

    def test_private_function(self):
        def private_function():
            pass

        self.assertFalse(utils.is_global_function(private_function))

    def test_coroutine(self):
        self.assertTrue(utils.is_global_function(test_tasks.noop_task_async.func))

    def test_method(self):
        self.assertFalse(utils.is_global_function(self.test_method))
        self.assertFalse(utils.is_global_function(self.setUp))

    def test_lambda(self):
        self.assertFalse(utils.is_global_function(lambda: True))

    def test_uninitialised_method(self):
        # This import has to be here, so the module is loaded during the test
        from . import is_global_function_fixture

        self.assertTrue(is_global_function_fixture.really_global_function)
        self.assertIsNotNone(is_global_function_fixture.inner_func_is_global_function)
        self.assertFalse(is_global_function_fixture.inner_func_is_global_function)


class IsJSONSerializableTestCase(SimpleTestCase):
    def test_serializable(self):
        for example in [123, 12.3, "123", {"123": 456}, [], None]:
            with self.subTest(example):
                self.assertTrue(utils.is_json_serializable(example))

    def test_not_serializable(self):
        for example in [
            self,
            any,
            datetime.datetime.now(),
        ]:
            with self.subTest(example):
                self.assertFalse(utils.is_json_serializable(example))


class JSONNormalizeTestCase(SimpleTestCase):
    def test_round_trip(self):
        self.assertEqual(utils.json_normalize({}), {})
        self.assertEqual(utils.json_normalize([]), [])
        self.assertEqual(utils.json_normalize(()), [])
        self.assertEqual(utils.json_normalize({"foo": ()}), {"foo": []})

    def test_encode_error(self):
        for example in [self, any, datetime.datetime.now()]:
            with self.subTest(example):
                self.assertFalse(utils.is_json_serializable(example))
                self.assertRaises(TypeError, utils.json_normalize, example)


class RetryTestCase(SimpleTestCase):
    def test_retry(self):
        sentinel = Mock(side_effect=ValueError(""))

        with self.assertRaises(ValueError):
            utils.retry()(sentinel)()

        self.assertEqual(sentinel.call_count, 3)

    def test_keeps_return_value(self):
        self.assertTrue(utils.retry()(lambda: True)())
        self.assertFalse(utils.retry()(lambda: False)())


class ExceptionSerializationTestCase(SimpleTestCase):
    def test_serialize_exceptions(self):
        for exc in [
            ValueError(10),
            SyntaxError("Wrong"),
            ImproperlyConfigured("It's wrong"),
            InvalidTaskError(""),
            SystemExit(),
        ]:
            with self.subTest(exc):
                data = utils.exception_to_dict(exc)
                self.assertEqual(utils.json_normalize(data), data)
                self.assertEqual(
                    set(data.keys()), {"exc_type", "exc_args", "exc_traceback"}
                )
                exception = utils.exception_from_dict(data)
                self.assertIsInstance(exception, type(exc))
                self.assertEqual(exception.args, exc.args)

                # Check that the exception traceback contains a minimal traceback
                msg = str(exc.args[0]) if exc.args else ""
                traceback = data["exc_traceback"]
                self.assertIn(exc.__class__.__name__, traceback)
                self.assertIn(msg, traceback)

    def test_serialize_full_traceback(self):
        try:
            # Using optparse to generate an error because:
            # - it's pure python
            # - it's easy to trip down
            # - it's unlikely to change ever
            optparse.OptionParser(option_list=[1])  # type: ignore
        except Exception as e:
            traceback = utils.exception_to_dict(e)["exc_traceback"]
            # The test is willingly fuzzy to ward against changes in the
            # traceback formatting
            self.assertIn("traceback", traceback.lower())
            self.assertIn("line", traceback.lower())
            self.assertIn(optparse.__file__, traceback)
            self.assertTrue(
                traceback.endswith("TypeError: not an Option instance: 1\n")
            )

    def test_serialize_traceback_from_c_module(self):
        try:
            # Same as test_serialize_full_traceback, but uses hashlib
            # because it's in C, not in Python
            hashlib.md5(1)  # type: ignore
        except Exception as e:
            traceback = utils.exception_to_dict(e)["exc_traceback"]
            self.assertIn("traceback", traceback.lower())
            self.assertTrue(
                traceback.endswith(
                    "TypeError: object supporting the buffer API required\n"
                )
            )
            self.assertIn("hashlib.md5(1)", traceback)

    def test_cannot_deserialize_non_exception(self):
        serialized_exceptions: List[utils.SerializedExceptionDict] = [
            {
                "exc_type": "subprocess.check_output",
                "exc_args": ["exit", "1"],
                "exc_traceback": "",
            },
            {"exc_type": "True", "exc_args": [], "exc_traceback": ""},
            {"exc_type": "math.pi", "exc_args": [], "exc_traceback": ""},
            {"exc_type": __name__, "exc_args": [], "exc_traceback": ""},
            {
                "exc_type": utils.get_module_path(type(self)),
                "exc_args": [],
                "exc_traceback": "",
            },
            {
                "exc_type": utils.get_module_path(Mock),
                "exc_args": [],
                "exc_traceback": "",
            },
        ]

        for data in serialized_exceptions:
            with self.subTest(data):
                with self.assertRaises((TypeError, ImportError)):
                    utils.exception_from_dict(data)
