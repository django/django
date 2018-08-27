import asyncio

from asgiref.server import StatelessServer


class Worker(StatelessServer):
    """
    ASGI protocol server that surfaces events sent to specific channels
    on the channel layer into a single application instance.
    """

    def __init__(self, application, channels, channel_layer, max_applications=1000):
        super().__init__(application, max_applications)
        self.channels = channels
        self.channel_layer = channel_layer
        if self.channel_layer is None:
            raise ValueError("Channel layer is not valid")

    async def handle(self):
        """
        Listens on all the provided channels and handles the messages.
        """
        # For each channel, launch its own listening coroutine
        listeners = []
        for channel in self.channels:
            listeners.append(asyncio.ensure_future(self.listener(channel)))
        # Wait for them all to exit
        await asyncio.wait(listeners)
        # See if any of the listeners had an error (e.g. channel layer error)
        [listener.result() for listener in listeners]

    async def listener(self, channel):
        """
        Single-channel listener
        """
        while True:
            message = await self.channel_layer.receive(channel)
            if not message.get("type", None):
                raise ValueError("Worker received message with no type.")
            # Make a scope and get an application instance for it
            scope = {"type": "channel", "channel": channel}
            instance_queue = self.get_or_create_application_instance(channel, scope)
            # Run the message into the app
            await instance_queue.put(message)
