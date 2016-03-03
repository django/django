from __future__ import unicode_literals

import logging
import signal
import sys
import time

from .exceptions import ConsumeLater
from .message import Message
from .utils import name_that_thing

logger = logging.getLogger('django.channels')


class Worker(object):
    """
    A "worker" process that continually looks for available messages to run
    and runs their consumers.
    """

    def __init__(self, channel_layer, callback=None, message_retries=10, signal_handlers=True):
        self.channel_layer = channel_layer
        self.callback = callback
        self.message_retries = message_retries
        self.signal_handlers = signal_handlers
        self.termed = False
        self.in_job = False

    def install_signal_handler(self):
        signal.signal(signal.SIGTERM, self.sigterm_handler)
        signal.signal(signal.SIGINT, self.sigterm_handler)

    def sigterm_handler(self, signo, stack_frame):
        self.termed = True
        if self.in_job:
            logger.info("Shutdown signal received while busy, waiting for loop termination")
        else:
            logger.info("Shutdown signal received while idle, terminating immediately")
            sys.exit(0)

    def run(self):
        """
        Tries to continually dispatch messages to consumers.
        """
        if self.signal_handlers:
            self.install_signal_handler()
        channels = self.channel_layer.registry.all_channel_names()
        while not self.termed:
            self.in_job = False
            channel, content = self.channel_layer.receive_many(channels, block=True)
            self.in_job = True
            # If no message, stall a little to avoid busy-looping then continue
            if channel is None:
                time.sleep(0.01)
                continue
            # Create message wrapper
            logger.debug("Worker got message on %s: repl %s", channel, content.get("reply_channel", "none"))
            message = Message(
                content=content,
                channel_name=channel,
                channel_layer=self.channel_layer,
            )
            # Add attribute to message if it's been retried almost too many times,
            # and would be thrown away this time if it's requeued. Used for helpful
            # warnings in decorators and such - don't rely on this as public API.
            if content.get("__retries__", 0) == self.message_retries:
                message.__doomed__ = True
            # Handle the message
            consumer = self.channel_layer.registry.consumer_for_channel(channel)
            if self.callback:
                self.callback(channel, message)
            try:
                consumer(message)
            except ConsumeLater:
                # They want to not handle it yet. Re-inject it with a number-of-tries marker.
                content['__retries__'] = content.get("__retries__", 0) + 1
                # If we retried too many times, quit and error rather than
                # spinning forever
                if content['__retries__'] > self.message_retries:
                    logger.warning(
                        "Exceeded number of retries for message on channel %s: %s",
                        channel,
                        repr(content)[:100],
                    )
                    continue
                self.channel_layer.send(channel, content)
            except:
                logger.exception("Error processing message with consumer %s:", name_that_thing(consumer))
