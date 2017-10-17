import inspect
from concurrent.futures import ThreadPoolExecutor

from asgiref.applications import sync_to_async, async_to_sync


def get_handler_name(message):
    """
    Looks at a message, checks it has a sensible type, and returns the
    handler name for that type.
    """
    # Check message looks OK
    if "type" not in message:
        raise ValueError("Incoming message has no 'type' attribute")
    if message["type"].startswith("_"):
        raise ValueError("Malformed type in message (leading underscore)")
    # Extract type and replace . with _
    return message["type"].replace(".", "_")


class AsyncConsumer:
    """
    Base consumer class. Implements the ASGI application spec, and adds on
    channel layer management and routing of events to named methods based
    on their type.
    """

    def __init__(self, scope):
        self.scope = scope

    async def __call__(self, receive, send):
        """
        Dispatches incoming messages to type-based handlers asynchronously.
        """
        # Store send function
        self.base_send = send
        while True:
            # Get the next message
            message = await receive()
            # Get and execute the handler
            handler = getattr(self, get_handler_name(message), None)
            if handler:
                await handler(message)
            else:
                raise ValueError("No handler for message type %s" % message["type"])

    async def send(self, message):
        """
        Overrideable/callable-by-subclasses send method.
        """
        await self.base_send(message)


class SyncConsumer:
    """
    Synchronous version of the consumer, which is what we write most of the
    generic consumers against (for now). Calls handlers in a threadpool and
    uses CallBouncer to get the send method out to the main event loop.

    It would have been possible to have "mixed" consumers and auto-detect
    if a handler was awaitable or not, but that would have made the API
    for user-called methods very confusing as there'd be two types of each.
    """

    def __init__(self, scope):
        self.scope = scope

    async def __call__(self, receive, send):
        # Store send function as a sync version
        self.base_send = async_to_sync(send)
        while True:
            message = await receive()
            await self.sync_call(message)

    @sync_to_async
    def sync_call(self, message):
        """
        Dispatches incoming messages to type-based handlers asynchronously.
        """
        # Get and execute the handler
        handler = getattr(self, get_handler_name(message), None)
        if handler:
            handler(message)
        else:
            raise ValueError("No handler for message type %s" % message["type"])

    def send(self, message):
        """
        Overrideable/callable-by-subclasses send method.
        """
        self.base_send(message)
