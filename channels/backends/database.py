import json
import datetime

from django.apps.registry import Apps
from django.db import models, connections, DEFAULT_DB_ALIAS, IntegrityError
from django.utils.functional import cached_property
from django.utils.timezone import now

from .base import BaseChannelBackend


class DatabaseChannelBackend(BaseChannelBackend):
    """
    ORM-backed channel environment. For development use only; it will span
    multiple processes fine, but it's going to be pretty bad at throughput.
    """

    def __init__(self, routing, expiry=60, db_alias=DEFAULT_DB_ALIAS):
        super(DatabaseChannelBackend, self).__init__(routing=routing, expiry=expiry)
        self.db_alias = db_alias

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

    @cached_property
    def lock_model(self):
        """
        Initialises a new model to store groups; not done as part of a
        models.py as we don't want to make it for most installs.
        """
        # Make the model class
        class Lock(models.Model):
            channel = models.CharField(max_length=200, unique=True)
            expiry = models.DateTimeField(db_index=True)

            class Meta:
                apps = Apps()
                app_label = "channels"
                db_table = "django_channel_locks"
        # Ensure its table exists
        if Lock._meta.db_table not in self.connection.introspection.table_names(self.connection.cursor()):
            with self.connection.schema_editor() as editor:
                editor.create_model(Lock)
        return Lock

    def send(self, channel, message):
        self.channel_model.objects.create(
            channel=channel,
            content=json.dumps(message),
            expiry=now() + datetime.timedelta(seconds=self.expiry)
        )

    def receive_many(self, channels):
        if not channels:
            raise ValueError("Cannot receive on empty channel list!")
        self._clean_expired()
        # Get a message from one of our channels
        message = self.channel_model.objects.filter(channel__in=channels).order_by("id").first()
        if message:
            self.channel_model.objects.filter(pk=message.pk).delete()
            return message.channel, json.loads(message.content)
        else:
            return None, None

    def _clean_expired(self):
        """
        Cleans out expired groups and messages.
        """
        # Include a 10-second grace period because that solves some clock sync
        self.channel_model.objects.filter(expiry__lt=now() - datetime.timedelta(seconds=10)).delete()
        self.group_model.objects.filter(expiry__lt=now() - datetime.timedelta(seconds=10)).delete()
        self.lock_model.objects.filter(expiry__lt=now() - datetime.timedelta(seconds=10)).delete()

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

    def group_channels(self, group):
        """
        Returns an iterable of all channels in the group.
        """
        self._clean_expired()
        return list(self.group_model.objects.filter(group=group).values_list("channel", flat=True))

    def lock_channel(self, channel, expiry=None):
        """
        Attempts to get a lock on the named channel. Returns True if lock
        obtained, False if lock not obtained.
        """
        # We rely on the UNIQUE constraint for only-one-thread-wins on locks
        try:
            self.lock_model.objects.create(
                channel=channel,
                expiry=now() + datetime.timedelta(seconds=expiry or self.expiry),
            )
        except IntegrityError:
            return False
        else:
            return True

    def unlock_channel(self, channel):
        """
        Unlocks the named channel. Always succeeds.
        """
        self.lock_model.objects.filter(channel=channel).delete()

    def __str__(self):
        return "%s(alias=%s)" % (self.__class__.__name__, self.connection.alias)

    def flush(self):
        pass
