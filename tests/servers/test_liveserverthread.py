from django.db import DEFAULT_DB_ALIAS, connections
from django.test import LiveServerTestCase, TestCase


class LiveServerThreadTest(TestCase):

    def run_live_server_thread(self, connections_override=None):
        thread = LiveServerTestCase._create_server_thread(connections_override)
        thread.daemon = True
        thread.start()
        thread.is_ready.wait()
        thread.terminate()

    def test_closes_connections(self):
        conn = connections[DEFAULT_DB_ALIAS]
        if conn.vendor == 'sqlite' and conn.is_in_memory_db():
            self.skipTest("the sqlite backend's close() method is a no-op when using an in-memory database")
        # Pass a connection to the thread to check they are being closed.
        connections_override = {DEFAULT_DB_ALIAS: conn}

        saved_sharing = conn.allow_thread_sharing
        try:
            conn.allow_thread_sharing = True
            self.assertTrue(conn.is_usable())
            self.run_live_server_thread(connections_override)
            self.assertFalse(conn.is_usable())
        finally:
            conn.allow_thread_sharing = saved_sharing
