import time
import datetime

from django.apps.registry import Apps
from django.db import models, connections, DEFAULT_DB_ALIAS

from .base import BaseChannelBackend

queues = {}

class ORMChannelBackend(BaseChannelBackend):
    """
    ORM-backed channel environment. For development use only; it will span
    multiple processes fine, but it's going to be pretty bad at throughput.
    """

    def __init__(self, expiry, db_alias=DEFAULT_DB_ALIAS):
        super(ORMChannelBackend, self).__init__(expiry)
        self.connection = connections[db_alias]
        self.model = self.make_model()
        self.ensure_schema()

    def make_model(self):
        """
        Initialises a new model to store messages; not done as part of a
        models.py as we don't want to make it for most installs.
        """
        class Message(models.Model):
            # We assume an autoincrementing PK for message order
            channel = models.CharField(max_length=200, db_index=True)
            content = models.TextField()
            expiry = models.DateTimeField(db_index=True)
            class Meta:
                apps = Apps()
                app_label = "channels"
                db_table = "django_channels"
        return Message

    def ensure_schema(self):
        """
        Ensures the table exists and has the correct schema.
        """
        # If the table's there, that's fine - we've never changed its schema
        # in the codebase.
        if self.model._meta.db_table in self.connection.introspection.table_names(self.connection.cursor()):
            return
        # Make the table
        with self.connection.schema_editor() as editor:
            editor.create_model(self.model)

    def send(self, channel, message):
        self.model.objects.create(
            channel = channel,
            message = json.dumps(message),
            expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=self.expiry)
        )

    def receive_many(self, channels):
        while True:
            # Delete all expired messages (add 10 second grace period for clock sync)
            self.model.objects.filter(expiry__lt=datetime.datetime.utcnow() - datetime.timedelta(seconds=10)).delete()
            # Get a message from one of our channels
            message = self.model.objects.filter(channel__in=channels).order_by("id").first()
            if message:
                return message.channel, json.loads(message.content)
            # If all empty, sleep for a little bit
            time.sleep(0.2)

