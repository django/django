import json
from datetime import timedelta

from django.db import models
from django.utils import timezone

from channels import DEFAULT_CHANNEL_LAYER, Channel, channel_layers


class DelayedMessageQuerySet(models.QuerySet):

    def is_due(self):
        return self.filter(due_date__lte=timezone.now())


class DelayedMessage(models.Model):

    due_date = models.DateTimeField(db_index=True)
    channel_name = models.CharField(max_length=512)
    content = models.TextField()

    objects = DelayedMessageQuerySet.as_manager()

    @property
    def delay(self):
        return self._delay

    @delay.setter
    def delay(self, milliseconds):
        self._delay = milliseconds
        self.due_date = timezone.now() + timedelta(milliseconds=milliseconds)

    def send(self, channel_layer=None, requeue_delay=1000):
        """
        Sends the message on the configured channel with the stored content.

        Deletes the DelayedMessage record if successfully sent.

        Args:
            channel_layer: optional channel_layer to use
            requeue_delay: if the channel is full, milliseconds to wait before requeue
        """
        channel_layer = channel_layer or channel_layers[DEFAULT_CHANNEL_LAYER]
        try:
            Channel(self.channel_name, channel_layer=channel_layer).send(json.loads(self.content), immediately=True)
            self.delete()
        except channel_layer.ChannelFull:
            self.delay = requeue_delay
            self.save()
