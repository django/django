from __future__ import unicode_literals

import fnmatch
import logging
import signal
import sys
import time
import multiprocessing
import threading

from .signals import consumer_started, consumer_finished
from .exceptions import ConsumeLater, DenyConnection
from .message import Message
from .utils import name_that_thing
from .signals import worker_ready

logger = logging.getLogger('django.channels')


class Worker(object):
    """
    A "worker" process that continually looks for available messages to run
    and runs their consumers.
    """

    def __init__(
        self,
        channel_layer,
        callback=None,
        message_retries=10,
        signal_handlers=True,
        only_channels=None,
        exclude_channels=None
    ):
        self.channel_layer = channel_layer
        self.callback = callback
        self.message_retries = message_retries
        self.signal_handlers = signal_handlers
        self.only_channels = only_channels
        self.exclude_channels = exclude_channels
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

    def apply_channel_filters(self, channels):
        """
        Applies our include and exclude filters to the channel list and returns it
        """
        if self.only_channels:
            channels = [
                channel for channel in channels
                if any(fnmatch.fnmatchcase(channel, pattern) for pattern in self.only_channels)
            ]
        if self.exclude_channels:
            channels = [
                channel for channel in channels
                if not any(fnmatch.fnmatchcase(channel, pattern) for pattern in self.exclude_channels)
            ]
        return channels

    def ready(self):
        """
        Called once worker setup is complete.
        """
        worker_ready.send(sender=self)

    def run(self):
        """
        Tries to continually dispatch messages to consumers.
        """
        if self.signal_handlers:
            self.install_signal_handler()
        channels = self.apply_channel_filters(self.channel_layer.router.channels)
        logger.info("Listening on channels %s", ", ".join(sorted(channels)))
        while not self.termed:
            self.in_job = False
            channel, content = self.channel_layer.receive_many(channels, block=True)
            self.in_job = True
            # If no message, stall a little to avoid busy-looping then continue
            if channel is None:
                time.sleep(0.01)
                continue
            # Create message wrapper
            logger.debug("Got message on %s (reply %s)", channel, content.get("reply_channel", "none"))
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
            match = self.channel_layer.router.match(message)
            if match is None:
                logger.error("Could not find match for message on %s! Check your routing.", channel)
                continue
            else:
                consumer, kwargs = match
            if self.callback:
                self.callback(channel, message)
            try:
                logger.debug("Dispatching message on %s to %s", channel, name_that_thing(consumer))
                # Send consumer started to manage lifecycle stuff
                consumer_started.send(sender=self.__class__, environ={})
                # Run consumer
                consumer(message, **kwargs)
            except DenyConnection:
                # They want to deny a WebSocket connection.
                if message.channel.name != "websocket.connect":
                    raise ValueError("You cannot DenyConnection from a non-websocket.connect handler.")
                message.reply_channel.send({"accept": False})
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
                # Try to re-insert it a few times then drop it
                for _ in range(10):
                    try:
                        self.channel_layer.send(channel, content)
                    except self.channel_layer.ChannelFull:
                        time.sleep(0.05)
                    else:
                        break
            except:
                logger.exception("Error processing message with consumer %s:", name_that_thing(consumer))
            else:
                # Send consumer finished so DB conns close etc.
                consumer_finished.send(sender=self.__class__)


class WorkerGroup(Worker):
    """
    Group several workers together in threads. Manages the sub-workers,
    terminating them if a signal is received.
    """

    def __init__(self, *args, **kwargs):
        n_threads = kwargs.pop('n_threads', multiprocessing.cpu_count()) - 1
        super(WorkerGroup, self).__init__(*args, **kwargs)
        kwargs['signal_handlers'] = False
        self.workers = [Worker(*args, **kwargs) for ii in range(n_threads)]

    def sigterm_handler(self, signo, stack_frame):
        self.termed = True
        for wkr in self.workers:
            wkr.termed = True
        logger.info("Shutdown signal received while busy, waiting for "
                    "loop termination")

    def ready(self):
        super(WorkerGroup, self).ready()
        for wkr in self.workers:
            wkr.ready()

    def run(self):
        """
        Launch sub-workers before running.
        """
        self.threads = [threading.Thread(target=self.workers[ii].run)
                        for ii in range(len(self.workers))]
        for t in self.threads:
            t.start()
        super(WorkerGroup, self).run()
        # Join threads once completed.
        for t in self.threads:
            t.join()
