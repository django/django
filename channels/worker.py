class Worker(object):
    """
    A "worker" process that continually looks for available messages to run
    and runs their consumers.
    """

    def __init__(self, consumer_registry, channel_class):
        self.consumer_registry = consumer_registry
        self.channel_class = channel_class

    def run(self):
        """
        Tries to continually dispatch messages to consumers.
        """
        channels = self.consumer_registry.all_channel_names()
        while True:
            channel, message = self.channel_class.receive_many(channels)
            consumer = self.consumer_registry.consumer_for_channel(channel)
            consumer(**message)
