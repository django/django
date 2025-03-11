import asyncio
import contextvars
import time

from .compatibility import guarantee_single_callable
from .timeout import timeout as async_timeout


class ApplicationCommunicator:
    """
    Runs an ASGI application in a test mode, allowing sending of
    messages to it and retrieval of messages it sends.
    """

    def __init__(self, application, scope):
        self.application = guarantee_single_callable(application)
        self.scope = scope
        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        # Clear context - this ensures that context vars set in the testing scope
        # are not "leaked" into the application which would normally begin with
        # an empty context. In Python >= 3.11 this could also be written as:
        # asyncio.create_task(..., context=contextvars.Context())
        self.future = contextvars.Context().run(
            asyncio.create_task,
            self.application(scope, self.input_queue.get, self.output_queue.put),
        )

    async def wait(self, timeout=1):
        """
        Waits for the application to stop itself and returns any exceptions.
        """
        try:
            async with async_timeout(timeout):
                try:
                    await self.future
                    self.future.result()
                except asyncio.CancelledError:
                    pass
        finally:
            if not self.future.done():
                self.future.cancel()
                try:
                    await self.future
                except asyncio.CancelledError:
                    pass

    def stop(self, exceptions=True):
        if not self.future.done():
            self.future.cancel()
        elif exceptions:
            # Give a chance to raise any exceptions
            self.future.result()

    def __del__(self):
        # Clean up on deletion
        try:
            self.stop(exceptions=False)
        except RuntimeError:
            # Event loop already stopped
            pass

    async def send_input(self, message):
        """
        Sends a single message to the application
        """
        # Give it the message
        await self.input_queue.put(message)

    async def receive_output(self, timeout=1):
        """
        Receives a single message from the application, with optional timeout.
        """
        # Make sure there's not an exception to raise from the task
        if self.future.done():
            self.future.result()
        # Wait and receive the message
        try:
            async with async_timeout(timeout):
                return await self.output_queue.get()
        except asyncio.TimeoutError as e:
            # See if we have another error to raise inside
            if self.future.done():
                self.future.result()
            else:
                self.future.cancel()
                try:
                    await self.future
                except asyncio.CancelledError:
                    pass
            raise e

    async def receive_nothing(self, timeout=0.1, interval=0.01):
        """
        Checks that there is no message to receive in the given time.
        """
        # `interval` has precedence over `timeout`
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if not self.output_queue.empty():
                return False
            await asyncio.sleep(interval)
        return self.output_queue.empty()
