class Worker(object):
    """
    A "worker" process that continually looks for available messages to run
    and runs their consumers.
    """

    def __init__(self, channel_backend, callback=None):
        self.channel_backend = channel_backend
        self.callback = callback

    def run(self):
        """
        Tries to continually dispatch messages to consumers.
        """

        channels = self.channel_backend.registry.all_channel_names()
        while True:
            channel, message = self.channel_backend.receive_many(channels)
            consumer = self.channel_backend.registry.consumer_for_channel(channel)
            if self.callback:
                self.callback(channel, message)
            consumer(channel=channel, **message)
