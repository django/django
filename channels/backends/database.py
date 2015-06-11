import time
import json
import datetime

from django.apps.registry import Apps
from django.db import models, connections, DEFAULT_DB_ALIAS
from django.utils.functional import cached_property
from django.utils.timezone import now

from .base import BaseChannelBackend

queues = {}

class DatabaseChannelBackend(BaseChannelBackend):
    """
    ORM-backed channel environment. For development use only; it will span
    multiple processes fine, but it's going to be pretty bad at throughput.
    """

    def __init__(self, expiry=60, db_alias=DEFAULT_DB_ALIAS):
        super(DatabaseChannelBackend, self).__init__(expiry)
        self.db_alias = db_alias

    @property
    def connection(self):
        """
        Returns the correct connection for the current thread.
        """
        return connections[self.db_alias]

    @property
    def model(self):
        """
        Initialises a new model to store messages; not done as part of a
        models.py as we don't want to make it for most installs.
        """
        # Make the model class
        class Message(models.Model):
            # We assume an autoincrementing PK for message order
            channel = models.CharField(max_length=200, db_index=True)
            content = models.TextField()
            expiry = models.DateTimeField(db_index=True)
            class Meta:
                apps = Apps()
                app_label = "channels"
                db_table = "django_channels"
        # Ensure its table exists
        if Message._meta.db_table not in self.connection.introspection.table_names(self.connection.cursor()):
            with self.connection.schema_editor() as editor:
                editor.create_model(Message)
        return Message

    def send(self, channel, message):
        self.model.objects.create(
            channel = channel,
            content = json.dumps(message),
            expiry = now() + datetime.timedelta(seconds=self.expiry)
        )

    def receive_many(self, channels):
        if not channels:
            raise ValueError("Cannot receive on empty channel list!")
        # Delete all expired messages (add 10 second grace period for clock sync)
        self.model.objects.filter(expiry__lt=now() - datetime.timedelta(seconds=10)).delete()
        # Get a message from one of our channels
        message = self.model.objects.filter(channel__in=channels).order_by("id").first()
        if message:
            self.model.objects.filter(pk=message.pk).delete()
            return message.channel, json.loads(message.content)
        else:
            return None, None

    def __str__(self):
        return "%s(alias=%s)" % (self.__class__.__name__, self.connection.alias)
