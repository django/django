class Worker(object):
    """
    A "worker" process that continually looks for available messages to run
    and runs their consumers.
    """

    def __init__(self, channel_layer):
        self.channel_layer = channel_layer

    def run(self):
        """
        Tries to continually dispatch messages to consumers.
        """

        channels = self.channel_layer.registry.all_channel_names()
        while True:
            channel, message = self.channel_layer.receive_many(channels)
            consumer = self.channel_layer.registry.consumer_for_channel(channel)
            consumer(channel=channel, **message)
