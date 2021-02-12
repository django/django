from django.db import DEFAULT_DB_ALIAS, connections
from django.test import LiveServerTestCase, TestCase
from django.test.testcases import LiveServerThread


class LiveServerThreadTest(TestCase):

    def run_live_server_thread(self, connections_override=None):
        thread = LiveServerTestCase._create_server_thread(connections_override)
        thread.daemon = True
        thread.start()
        thread.is_ready.wait()
        thread.terminate()

    def test_closes_connections(self):
        conn = connections[DEFAULT_DB_ALIAS]
        # Pass a connection to the thread to check they are being closed.
        connections_override = {DEFAULT_DB_ALIAS: conn}

        conn.inc_thread_sharing()
        try:
            self.assertTrue(conn.is_usable())
            self.run_live_server_thread(connections_override)
            self.assertFalse(conn.is_usable())
        finally:
            conn.dec_thread_sharing()

    def test_server_class(self):
        class FakeServer:
            def __init__(*args, **kwargs):
                pass

        class MyServerThread(LiveServerThread):
            server_class = FakeServer

        class MyServerTestCase(LiveServerTestCase):
            server_thread_class = MyServerThread

        thread = MyServerTestCase._create_server_thread(None)
        server = thread._create_server()
        self.assertIs(type(server), FakeServer)
