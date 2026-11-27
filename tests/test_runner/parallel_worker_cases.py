import os
import signal
import time
import unittest
from multiprocessing.pool import MaybeEncodingError

from django.test.runner import ParallelTestSuite


class WorkerExitCase(unittest.TestCase):
    def __setstate__(self, state):
        if state["_testMethodName"] == "exit_on_decode":
            os._exit(17)
        self.__dict__.update(state)

    def exit_on_decode(self):
        self.fail("The worker should exit before running the test.")

    def exit_during_test(self):
        os._exit(17)

    def succeed(self):
        pass

    def interrupt_parent(self):
        # Give the parent time to enter its wait for the worker's result.
        time.sleep(0.2)
        os.kill(self.parent_pid, signal.SIGINT)
        time.sleep(2)
        self.fail("The parent should stop waiting after SIGINT.")


class UnencodableTestSuite(ParallelTestSuite):
    def run_subsuite(args):
        return args[1], [lambda: None]


def make_suite(subsuites, suite_class=ParallelTestSuite):
    suite = suite_class(subsuites, processes=2)
    suite.serialized_aliases = set()
    suite.used_aliases = set()
    return suite


def run_worker_exit_scenario(method):
    interrupted = WorkerExitCase(method)
    subsuites = [unittest.TestSuite([interrupted])]
    subsuites.extend(unittest.TestSuite([WorkerExitCase("succeed")]) for _ in range(3))
    suite = make_suite(subsuites)
    result = suite.run(unittest.TestResult())
    [(test, error)] = result.errors
    if test is not interrupted or result.testsRun != 4:
        raise AssertionError((test, result.testsRun))
    if "exited before reporting results" not in error:
        raise AssertionError(error)


def run_interrupt_scenario():
    test = WorkerExitCase("interrupt_parent")
    test.parent_pid = os.getpid()
    suite = make_suite([unittest.TestSuite([test])])
    unittest.installHandler()
    result = unittest.TestResult()
    unittest.registerResult(result)
    suite.run(result)
    if not result.shouldStop or result.testsRun:
        raise AssertionError((result.shouldStop, result.testsRun))


def run_encoding_error_scenario():
    test = WorkerExitCase("succeed")
    suite = make_suite([unittest.TestSuite([test])], UnencodableTestSuite)
    try:
        suite.run(unittest.TestResult())
    except MaybeEncodingError:
        pass
    else:
        raise AssertionError("Expected a result encoding error.")
