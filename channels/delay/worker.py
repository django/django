from __future__ import unicode_literals

import json
import logging
import signal
import sys
import time

from django.core.exceptions import ValidationError

from .models import DelayedMessage

logger = logging.getLogger('django.channels')


class Worker(object):
    """Worker class that listens to channels.delay messages and dispatches messages"""

    def __init__(
            self,
            channel_layer,
            signal_handlers=True,
    ):
        self.channel_layer = channel_layer
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
        if self.signal_handlers:
            self.install_signal_handler()

        logger.info("Listening on asgi.delay")

        while not self.termed:
            self.in_job = False
            channel, content = self.channel_layer.receive_many(['asgi.delay'])
            self.in_job = True

            if channel is not None:
                logger.debug("Got message on asgi.delay")

                if 'channel' not in content or \
                   'content' not in content or \
                   'delay' not in content:
                    logger.error("Invalid message received, it must contain keys 'channel', 'content', "
                                 "and 'delay'.")
                    break

                message = DelayedMessage(
                    content=json.dumps(content['content']),
                    channel_name=content['channel'],
                    delay=content['delay']
                )

                try:
                    message.full_clean()
                except ValidationError as err:
                    logger.error("Invalid message received: %s:%s", err.error_dict.keys(), err.messages)
                    break
                message.save()
            # check for messages to send
            if not DelayedMessage.objects.is_due().count():
                logger.debug("No delayed messages waiting.")
                time.sleep(0.01)
                continue

            for message in DelayedMessage.objects.is_due().all():
                logger.info("Delayed message due. Sending message to channel %s", message.channel_name)
                message.send(channel_layer=self.channel_layer)
