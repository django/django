# -*- coding: utf-8 -*-
"""
Tests for greenlet.

"""
import os
import sys
import sysconfig
import unittest

from gc import collect
from gc import get_objects
from threading import active_count as active_thread_count
from time import sleep
from time import time

import psutil

from greenlet import greenlet as RawGreenlet
from greenlet import getcurrent

from greenlet._greenlet import get_pending_cleanup_count
from greenlet._greenlet import get_total_main_greenlets

from . import leakcheck

PY312 = sys.version_info[:2] >= (3, 12)
PY313 = sys.version_info[:2] >= (3, 13)
# XXX: First tested on 3.14a7. Revisit all uses of this on later versions to ensure they
# are still valid.
PY314 = sys.version_info[:2] >= (3, 14)

WIN = sys.platform.startswith("win")
RUNNING_ON_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS')
RUNNING_ON_TRAVIS = os.environ.get('TRAVIS') or RUNNING_ON_GITHUB_ACTIONS
RUNNING_ON_APPVEYOR = os.environ.get('APPVEYOR')
RUNNING_ON_CI = RUNNING_ON_TRAVIS or RUNNING_ON_APPVEYOR
RUNNING_ON_MANYLINUX = os.environ.get('GREENLET_MANYLINUX')

# Is the current interpreter free-threaded?) Note that this
# isn't the same as whether the GIL is enabled, this is the build-time
# value. Certain CPython details, like the garbage collector,
# work very differently on potentially-free-threaded builds than
# standard builds.
RUNNING_ON_FREETHREAD_BUILD = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))

class TestCaseMetaClass(type):
    # wrap each test method with
    # a) leak checks
    def __new__(cls, classname, bases, classDict):
        # pylint and pep8 fight over what this should be called (mcs or cls).
        # pylint gets it right, but we can't scope disable pep8, so we go with
        # its convention.
        # pylint: disable=bad-mcs-classmethod-argument
        check_totalrefcount = True

        # Python 3: must copy, we mutate the classDict. Interestingly enough,
        # it doesn't actually error out, but under 3.6 we wind up wrapping
        # and re-wrapping the same items over and over and over.
        for key, value in list(classDict.items()):
            if key.startswith('test') and callable(value):
                classDict.pop(key)
                if check_totalrefcount:
                    value = leakcheck.wrap_refcount(value)
                classDict[key] = value
        return type.__new__(cls, classname, bases, classDict)


class TestCase(unittest.TestCase, metaclass=TestCaseMetaClass):

    cleanup_attempt_sleep_duration = 0.001
    cleanup_max_sleep_seconds = 1

    def wait_for_pending_cleanups(self,
                                  initial_active_threads=None,
                                  initial_main_greenlets=None):
        initial_active_threads = initial_active_threads or self.threads_before_test
        initial_main_greenlets = initial_main_greenlets or self.main_greenlets_before_test
        sleep_time = self.cleanup_attempt_sleep_duration
        # NOTE: This is racy! A Python-level thread object may be dead
        # and gone, but the C thread may not yet have fired its
        # destructors and added to the queue. There's no particular
        # way to know that's about to happen. We try to watch the
        # Python threads to make sure they, at least, have gone away.
        # Counting the main greenlets, which we can easily do deterministically,
        # also helps.

        # Always sleep at least once to let other threads run
        sleep(sleep_time)
        quit_after = time() + self.cleanup_max_sleep_seconds
        # TODO: We could add an API that calls us back when a particular main greenlet is deleted?
        # It would have to drop the GIL
        while (
                get_pending_cleanup_count()
                or active_thread_count() > initial_active_threads
                or (not self.expect_greenlet_leak
                    and get_total_main_greenlets() > initial_main_greenlets)):
            sleep(sleep_time)
            if time() > quit_after:
                print("Time limit exceeded.")
                print("Threads: Waiting for only", initial_active_threads,
                      "-->", active_thread_count())
                print("MGlets : Waiting for only", initial_main_greenlets,
                      "-->", get_total_main_greenlets())
                break
        collect()

    def count_objects(self, kind=list, exact_kind=True):
        # pylint:disable=unidiomatic-typecheck
        # Collect the garbage.
        for _ in range(3):
            collect()
        if exact_kind:
            return sum(
                1
                for x in get_objects()
                if type(x) is kind
            )
        # instances
        return sum(
            1
            for x in get_objects()
            if isinstance(x, kind)
        )

    greenlets_before_test = 0
    threads_before_test = 0
    main_greenlets_before_test = 0
    expect_greenlet_leak = False

    def count_greenlets(self):
        """
        Find all the greenlets and subclasses tracked by the GC.
        """
        return self.count_objects(RawGreenlet, False)

    def setUp(self):
        # Ensure the main greenlet exists, otherwise the first test
        # gets a false positive leak
        super().setUp()
        getcurrent()
        self.threads_before_test = active_thread_count()
        self.main_greenlets_before_test = get_total_main_greenlets()
        self.wait_for_pending_cleanups(self.threads_before_test, self.main_greenlets_before_test)
        self.greenlets_before_test = self.count_greenlets()

    def tearDown(self):
        if getattr(self, 'skipTearDown', False):
            return

        self.wait_for_pending_cleanups(self.threads_before_test, self.main_greenlets_before_test)
        super().tearDown()

    def get_expected_returncodes_for_aborted_process(self):
        import signal
        # The child should be aborted in an unusual way. On POSIX
        # platforms, this is done with abort() and signal.SIGABRT,
        # which is reflected in a negative return value; however, on
        # Windows, even though we observe the child print "Fatal
        # Python error: Aborted" and in older versions of the C
        # runtime "This application has requested the Runtime to
        # terminate it in an unusual way," it always has an exit code
        # of 3. This is interesting because 3 is the error code for
        # ERROR_PATH_NOT_FOUND; BUT: the C runtime abort() function
        # also uses this code.
        #
        # If we link to the static C library on Windows, the error
        # code changes to '0xc0000409' (hex(3221226505)), which
        # apparently is STATUS_STACK_BUFFER_OVERRUN; but "What this
        # means is that nowadays when you get a
        # STATUS_STACK_BUFFER_OVERRUN, it doesn’t actually mean that
        # there is a stack buffer overrun. It just means that the
        # application decided to terminate itself with great haste."
        #
        #
        # On windows, we've also seen '0xc0000005' (hex(3221225477)).
        # That's "Access Violation"
        #
        # See
        # https://devblogs.microsoft.com/oldnewthing/20110519-00/?p=10623
        # and
        # https://docs.microsoft.com/en-us/previous-versions/k089yyh0(v=vs.140)?redirectedfrom=MSDN
        # and
        # https://devblogs.microsoft.com/oldnewthing/20190108-00/?p=100655
        expected_exit = (
            -signal.SIGABRT,
            # But beginning on Python 3.11, the faulthandler
            # that prints the C backtraces sometimes segfaults after
            # reporting the exception but before printing the stack.
            # This has only been seen on linux/gcc.
            -signal.SIGSEGV,
        ) if not WIN else (
            3,
            0xc0000409,
            0xc0000005,
        )
        return expected_exit

    def get_process_uss(self):
        """
        Return the current process's USS in bytes.

        uss is available on Linux, macOS, Windows. Also known as
        "Unique Set Size", this is the memory which is unique to a
        process and which would be freed if the process was terminated
        right now.

        If this is not supported by ``psutil``, this raises the
        :exc:`unittest.SkipTest` exception.
        """
        try:
            return psutil.Process().memory_full_info().uss
        except AttributeError as e:
            raise unittest.SkipTest("uss not supported") from e

    def run_script(self, script_name, show_output=True):
        import subprocess
        script = os.path.join(
            os.path.dirname(__file__),
            script_name,
        )

        try:
            return subprocess.check_output([sys.executable, script],
                                           encoding='utf-8',
                                           stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as ex:
            if show_output:
                print('-----')
                print('Failed to run script', script)
                print('~~~~~')
                print(ex.output)
                print('------')
            raise


    def assertScriptRaises(self, script_name, exitcodes=None):
        import subprocess
        with self.assertRaises(subprocess.CalledProcessError) as exc:
            output = self.run_script(script_name, show_output=False)
            __traceback_info__ = output
            # We're going to fail the assertion if we get here, at least
            # preserve the output in the traceback.

        if exitcodes is None:
            exitcodes = self.get_expected_returncodes_for_aborted_process()
        self.assertIn(exc.exception.returncode, exitcodes)
        return exc.exception
