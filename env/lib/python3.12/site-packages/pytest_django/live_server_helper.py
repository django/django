from __future__ import annotations

from typing import Any


class LiveServer:
    """The liveserver fixture

    This is the object that the ``live_server`` fixture returns.
    The ``live_server`` fixture handles creation and stopping.
    """

    def __init__(self, addr: str, *, start: bool = True) -> None:
        from django.db import connections
        from django.test.testcases import LiveServerThread
        from django.test.utils import modify_settings

        liveserver_kwargs: dict[str, Any] = {}

        connections_override = {}
        for conn in connections.all():
            # If using in-memory sqlite databases, pass the connections to
            # the server thread.
            if conn.vendor == "sqlite" and conn.is_in_memory_db():
                connections_override[conn.alias] = conn

        liveserver_kwargs["connections_override"] = connections_override
        from django.conf import settings

        if "django.contrib.staticfiles" in settings.INSTALLED_APPS:
            from django.contrib.staticfiles.handlers import StaticFilesHandler

            liveserver_kwargs["static_handler"] = StaticFilesHandler
        else:
            from django.test.testcases import _StaticFilesHandler

            liveserver_kwargs["static_handler"] = _StaticFilesHandler

        try:
            host, port = addr.split(":")
        except ValueError:
            host = addr
        else:
            liveserver_kwargs["port"] = int(port)
        self.thread = LiveServerThread(host, **liveserver_kwargs)

        self._live_server_modified_settings = modify_settings(
            ALLOWED_HOSTS={"append": host},
        )
        # `_live_server_modified_settings` is enabled and disabled by
        # `_live_server_helper`.

        self.thread.daemon = True

        if start:
            self.start()

    def start(self) -> None:
        """Start the server"""
        for conn in self.thread.connections_override.values():
            # Explicitly enable thread-shareability for this connection.
            conn.inc_thread_sharing()

        self.thread.start()
        self.thread.is_ready.wait()

        if self.thread.error:
            error = self.thread.error
            self.stop()
            raise error

    def stop(self) -> None:
        """Stop the server"""
        # Terminate the live server's thread.
        self.thread.terminate()
        # Restore shared connections' non-shareability.
        for conn in self.thread.connections_override.values():
            conn.dec_thread_sharing()

    @property
    def url(self) -> str:
        return f"http://{self.thread.host}:{self.thread.port}"

    def __str__(self) -> str:
        return self.url

    def __add__(self, other) -> str:
        return f"{self}{other}"

    def __repr__(self) -> str:
        return f"<LiveServer listening at {self.url}>"
