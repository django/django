# -*- coding: utf-8 -*-
"""
Tests for greenlet behavior during interpreter shutdown (Py_FinalizeEx).

Prior to the safe finalization fix, active greenlets being deallocated
during interpreter shutdown could trigger SIGSEGV or SIGABRT on Python
< 3.11, because green_dealloc attempted to throw GreenletExit via
g_switch() into a partially-torn-down interpreter.

The fix adds _Py_IsFinalizing() guards (on Python < 3.11 only) that
call murder_in_place() instead of g_switch() when the interpreter is
shutting down, avoiding the crash at the cost of not running cleanup
code inside the greenlet.

These tests verify:
  1. No crashes on ANY Python version (the core safety guarantee).
  2. GreenletExit cleanup code runs correctly during normal thread exit
     (the standard production path, e.g. uWSGI worker threads).
"""
import sys
import subprocess
import unittest
import textwrap

from greenlet.tests import TestCase


class TestInterpreterShutdown(TestCase):

    def _run_shutdown_script(self, script_body):
        """
        Run a Python script in a subprocess that exercises greenlet
        during interpreter shutdown. Returns (returncode, stdout, stderr).
        """
        full_script = textwrap.dedent(script_body)
        result = subprocess.run(
            [sys.executable, '-c', full_script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr

    # -----------------------------------------------------------------
    # Core safety tests: no crashes on any Python version
    # -----------------------------------------------------------------

    def test_active_greenlet_at_shutdown_no_crash(self):
        """
        An active (suspended) greenlet that is deallocated during
        interpreter shutdown should not crash the process.

        Before the fix, this would SIGSEGV on Python < 3.11 because
        _green_dealloc_kill_started_non_main_greenlet tried to call
        g_switch() during Py_FinalizeEx.
        """
        rc, stdout, stderr = self._run_shutdown_script("""\
            import greenlet

            def worker():
                greenlet.getcurrent().parent.switch("from worker")
                return "done"

            g = greenlet.greenlet(worker)
            result = g.switch()
            assert result == "from worker", result
            print("OK: exiting with active greenlet")
        """)
        self.assertEqual(rc, 0, f"Process crashed (rc={rc}):\n{stdout}{stderr}")
        self.assertIn("OK: exiting with active greenlet", stdout)

    def test_multiple_active_greenlets_at_shutdown(self):
        """
        Multiple suspended greenlets at shutdown should all be cleaned
        up without crashing.
        """
        rc, stdout, stderr = self._run_shutdown_script("""\
            import greenlet

            def worker(name):
                greenlet.getcurrent().parent.switch(f"hello from {name}")
                return "done"

            greenlets = []
            for i in range(10):
                g = greenlet.greenlet(worker)
                result = g.switch(f"g{i}")
                greenlets.append(g)

            print(f"OK: {len(greenlets)} active greenlets at shutdown")
        """)
        self.assertEqual(rc, 0, f"Process crashed (rc={rc}):\n{stdout}{stderr}")
        self.assertIn("OK: 10 active greenlets at shutdown", stdout)

    def test_nested_greenlets_at_shutdown(self):
        """
        Nested (chained parent) greenlets at shutdown should not crash.
        """
        rc, stdout, stderr = self._run_shutdown_script("""\
            import greenlet

            def inner():
                greenlet.getcurrent().parent.switch("inner done")

            def outer():
                g_inner = greenlet.greenlet(inner)
                g_inner.switch()
                greenlet.getcurrent().parent.switch("outer done")

            g = greenlet.greenlet(outer)
            result = g.switch()
            assert result == "outer done", result
            print("OK: nested greenlets at shutdown")
        """)
        self.assertEqual(rc, 0, f"Process crashed (rc={rc}):\n{stdout}{stderr}")
        self.assertIn("OK: nested greenlets at shutdown", stdout)

    def test_threaded_greenlets_at_shutdown(self):
        """
        Greenlets in worker threads that are still referenced at
        shutdown should not crash.
        """
        rc, stdout, stderr = self._run_shutdown_script("""\
            import greenlet
            import threading

            results = []

            def thread_worker():
                def greenlet_func():
                    greenlet.getcurrent().parent.switch("from thread greenlet")
                    return "done"

                g = greenlet.greenlet(greenlet_func)
                val = g.switch()
                results.append((g, val))

            threads = []
            for _ in range(3):
                t = threading.Thread(target=thread_worker)
                t.start()
                threads.append(t)

            for t in threads:
                t.join()

            print(f"OK: {len(results)} threaded greenlets at shutdown")
        """)
        self.assertEqual(rc, 0, f"Process crashed (rc={rc}):\n{stdout}{stderr}")
        self.assertIn("OK: 3 threaded greenlets at shutdown", stdout)

    # -----------------------------------------------------------------
    # Cleanup semantics tests
    # -----------------------------------------------------------------
    #
    # Note on behavioral testing during interpreter shutdown:
    #
    # During Py_FinalizeEx, sys.stdout is set to None early, making
    # print() a no-op.  More importantly, an active greenlet in the
    # module-level scope interferes with module dict clearing — the
    # greenlet's dealloc path (which temporarily resurrects the object
    # and performs a stack switch via g_switch) prevents reliable
    # observation of cleanup behavior.
    #
    # The production crash (SIGSEGV/SIGABRT) occurs during thread-state
    # cleanup in Py_FinalizeEx, not during module dict clearing.  Our
    # _Py_IsFinalizing() guard in _green_dealloc_kill_started_non_main_
    # greenlet targets that path.  The safety tests above verify that no
    # crashes occur; the tests below verify that greenlet cleanup works
    # correctly during normal thread exit (the most common code path).

    def test_greenlet_cleanup_during_thread_exit(self):
        """
        When a thread exits normally while holding active greenlets,
        GreenletExit IS thrown and cleanup code runs.  This is the
        standard cleanup path used in production (e.g. uWSGI worker
        threads finishing a request).
        """
        rc, stdout, stderr = self._run_shutdown_script("""\
            import os
            import threading
            import greenlet

            _write = os.write

            def thread_func():
                def worker(_w=_write,
                           _GreenletExit=greenlet.GreenletExit):
                    try:
                        greenlet.getcurrent().parent.switch("suspended")
                    except _GreenletExit:
                        _w(1, b"CLEANUP: GreenletExit caught\\n")
                        raise

                g = greenlet.greenlet(worker)
                g.switch()
                # Thread exits with active greenlet -> thread-state
                # cleanup triggers GreenletExit

            t = threading.Thread(target=thread_func)
            t.start()
            t.join()
            print("OK: thread cleanup done")
        """)
        self.assertEqual(rc, 0, f"Process crashed (rc={rc}):\n{stdout}{stderr}")
        self.assertIn("OK: thread cleanup done", stdout)
        self.assertIn("CLEANUP: GreenletExit caught", stdout)

    def test_finally_block_during_thread_exit(self):
        """
        try/finally blocks in active greenlets run correctly when the
        owning thread exits.
        """
        rc, stdout, stderr = self._run_shutdown_script("""\
            import os
            import threading
            import greenlet

            _write = os.write

            def thread_func():
                def worker(_w=_write):
                    try:
                        greenlet.getcurrent().parent.switch("suspended")
                    finally:
                        _w(1, b"FINALLY: cleanup executed\\n")

                g = greenlet.greenlet(worker)
                g.switch()

            t = threading.Thread(target=thread_func)
            t.start()
            t.join()
            print("OK: thread cleanup done")
        """)
        self.assertEqual(rc, 0, f"Process crashed (rc={rc}):\n{stdout}{stderr}")
        self.assertIn("OK: thread cleanup done", stdout)
        self.assertIn("FINALLY: cleanup executed", stdout)

    def test_many_greenlets_with_cleanup_at_shutdown(self):
        """
        Stress test: many active greenlets with cleanup code at shutdown.
        Ensures no crashes regardless of deallocation order.
        """
        rc, stdout, stderr = self._run_shutdown_script("""\
            import sys
            import greenlet

            cleanup_count = 0

            def worker(idx):
                global cleanup_count
                try:
                    greenlet.getcurrent().parent.switch(f"ready-{idx}")
                except greenlet.GreenletExit:
                    cleanup_count += 1
                    raise

            greenlets = []
            for i in range(50):
                g = greenlet.greenlet(worker)
                result = g.switch(i)
                greenlets.append(g)

            print(f"OK: {len(greenlets)} greenlets about to shut down")
            # Note: we can't easily print cleanup_count during shutdown
            # since it happens after the main module's code runs.
        """)
        self.assertEqual(rc, 0, f"Process crashed (rc={rc}):\n{stdout}{stderr}")
        self.assertIn("OK: 50 greenlets about to shut down", stdout)

    def test_deeply_nested_greenlets_at_shutdown(self):
        """
        Deeply nested greenlet parent chains at shutdown.
        Tests that the deallocation order doesn't cause issues.
        """
        rc, stdout, stderr = self._run_shutdown_script("""\
            import greenlet

            def level(depth, max_depth):
                if depth < max_depth:
                    g = greenlet.greenlet(level)
                    g.switch(depth + 1, max_depth)
                greenlet.getcurrent().parent.switch(f"depth-{depth}")

            g = greenlet.greenlet(level)
            result = g.switch(0, 10)
            print(f"OK: nested to depth 10, got {result}")
        """)
        self.assertEqual(rc, 0, f"Process crashed (rc={rc}):\n{stdout}{stderr}")
        self.assertIn("OK: nested to depth 10", stdout)

    def test_greenlet_with_traceback_at_shutdown(self):
        """
        A greenlet that has an active exception context when it's
        suspended should not crash during shutdown cleanup.
        """
        rc, stdout, stderr = self._run_shutdown_script("""\
            import greenlet

            def worker():
                try:
                    raise ValueError("test error")
                except ValueError:
                    # Suspend while an exception is active on the stack
                    greenlet.getcurrent().parent.switch("suspended with exc")
                return "done"

            g = greenlet.greenlet(worker)
            result = g.switch()
            assert result == "suspended with exc"
            print("OK: greenlet with active exception at shutdown")
        """)
        self.assertEqual(rc, 0, f"Process crashed (rc={rc}):\n{stdout}{stderr}")
        self.assertIn("OK: greenlet with active exception at shutdown", stdout)


if __name__ == '__main__':
    unittest.main()
