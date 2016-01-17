import datetime
import json
import random
import string
import time

from django.apps.registry import Apps
from django.db import DEFAULT_DB_ALIAS, IntegrityError, connections, models
from django.utils import six
from django.utils.functional import cached_property
from django.utils.timezone import now


class DatabaseChannelLayer(object):
    """
    ORM-backed ASGI channel layer.

    For development use only; it will span multiple processes fine,
    but it's going to be pretty bad at throughput. If you're reading this and
    running it in production, PLEASE STOP.

    Also uses JSON for serialization, as we don't want to make Django depend
    on msgpack for the built-in backend. The JSON format uses \uffff as first
    character to signify a byte string rather than a text string.
    """

    def __init__(self, db_alias=DEFAULT_DB_ALIAS, expiry=60):
        self.expiry = expiry
        self.db_alias = db_alias

    ### ASGI API ###

    extensions = ["groups", "flush"]

    def send(self, channel, message):
        # Typecheck
        assert isinstance(message, dict), "message is not a dict"
        assert isinstance(channel, six.text_type), "%s is not unicode" % channel
        # Write message to messages table
        self.channel_model.objects.create(
            channel=channel,
            content=self.serialize(message),
            expiry=now() + datetime.timedelta(seconds=self.expiry)
        )

    def receive_many(self, channels, block=False):
        if not channels:
            return None, None
        assert all(isinstance(channel, six.text_type) for channel in channels)
        # Shuffle channels
        channels = list(channels)
        random.shuffle(channels)
        # Clean out expired messages
        self._clean_expired()
        # Get a message from one of our channels
        while True:
            message = self.channel_model.objects.filter(channel__in=channels).order_by("id").first()
            if message:
                self.channel_model.objects.filter(pk=message.pk).delete()
                return message.channel, self.deserialize(message.content)
            else:
                if block:
                    time.sleep(1)
                else:
                    return None, None

    def new_channel(self, pattern):
        assert isinstance(pattern, six.text_type)
        # Keep making channel names till one isn't present.
        while True:
            random_string = "".join(random.choice(string.ascii_letters) for i in range(8))
            new_name = pattern.replace(b"?", random_string)
            if not self.channel_model.objects.filter(channel=new_name).exists():
                return new_name

    ### ASGI Group extension ###

    def group_add(self, group, channel, expiry=None):
        """
        Adds the channel to the named group for at least 'expiry'
        seconds (expiry defaults to message expiry if not provided).
        """
        self.group_model.objects.update_or_create(
            group=group,
            channel=channel,
            defaults={"expiry": now() + datetime.timedelta(seconds=expiry or self.expiry)},
        )

    def group_discard(self, group, channel):
        """
        Removes the channel from the named group if it is in the group;
        does nothing otherwise (does not error)
        """
        self.group_model.objects.filter(group=group, channel=channel).delete()

    def send_group(self, group, message):
        """
        Sends a message to the entire group.
        """
        self._clean_expired()
        for channel in self.group_model.objects.filter(group=group).values_list("channel", flat=True):
            self.send(channel, message)

    ### ASGI Flush extension ###

    def flush(self):
        self.channel_model.objects.all().delete()
        self.group_model.objects.all().delete()

    ### Serialization ###

    def serialize(self, message):
        return json.dumps(message)

    def deserialize(self, message):
        return json.loads(message)

    ### Database state mgmt ###

    @property
    def connection(self):
        """
        Returns the correct connection for the current thread.
        """
        return connections[self.db_alias]

    @cached_property
    def channel_model(self):
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

    @cached_property
    def group_model(self):
        """
        Initialises a new model to store groups; not done as part of a
        models.py as we don't want to make it for most installs.
        """
        # Make the model class
        class Group(models.Model):
            group = models.CharField(max_length=200)
            channel = models.CharField(max_length=200)
            expiry = models.DateTimeField(db_index=True)

            class Meta:
                apps = Apps()
                app_label = "channels"
                db_table = "django_channel_groups"
                unique_together = [["group", "channel"]]
        # Ensure its table exists
        if Group._meta.db_table not in self.connection.introspection.table_names(self.connection.cursor()):
            with self.connection.schema_editor() as editor:
                editor.create_model(Group)
        return Group

    def _clean_expired(self):
        """
        Cleans out expired groups and messages.
        """
        # Include a 10-second grace period because that solves some clock sync
        self.channel_model.objects.filter(expiry__lt=now() - datetime.timedelta(seconds=10)).delete()
        self.group_model.objects.filter(expiry__lt=now() - datetime.timedelta(seconds=10)).delete()

    def __str__(self):
        return "%s(alias=%s)" % (self.__class__.__name__, self.connection.alias)
