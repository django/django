from __future__ import unicode_literals

import six

from django.apps import apps
from django.db.models.signals import post_save, post_delete, pre_save, pre_delete

from ..channel import Group
from ..auth import channel_session, channel_session_user


CREATE = 'create'
UPDATE = 'update'
DELETE = 'delete'


class BindingMetaclass(type):
    """
    Metaclass that tracks instantiations of its type.
    """

    register_immediately = False
    binding_classes = []

    def __new__(cls, name, bases, body):
        klass = type.__new__(cls, name, bases, body)
        if bases != (object, ):
            cls.binding_classes.append(klass)
            if cls.register_immediately:
                klass.register()
        return klass

    @classmethod
    def register_all(cls):
        for binding_class in cls.binding_classes:
            binding_class.register()
        cls.register_immediately = True


@six.add_metaclass(BindingMetaclass)
class Binding(object):
    """
    Represents a two-way data binding from channels/groups to a Django model.
    Outgoing binding sends model events to zero or more groups.
    Incoming binding takes messages and maybe applies the action based on perms.

    To implement outbound, implement:
     - group_names, which returns a list of group names to send to
     - serialize, which returns message contents from an instance + action

    To implement inbound, implement:
     - deserialize, which returns pk, data and action from message contents
     - has_permission, which says if the user can do the action on an instance
     - create, which takes the data and makes a model instance
     - update, which takes data and a model instance and applies one to the other

    Outbound will work once you implement the functions; inbound requires you
    to place one or more bindings inside a protocol-specific Demultiplexer
    and tie that in as a consumer.
    """

    # Model to serialize

    model = None

    # Only model fields that are listed in fields should be send by default
    # if you want to really send all fields, use fields = ['__all__']

    fields = None

    # Decorators
    channel_session_user = True
    channel_session = False

    @classmethod
    def register(cls):
        """
        Resolves models.
        """
        # Connect signals
        for model in cls.get_registered_models():
            pre_save.connect(cls.pre_save_receiver, sender=model)
            post_save.connect(cls.post_save_receiver, sender=model)
            pre_delete.connect(cls.pre_delete_receiver, sender=model)
            post_delete.connect(cls.post_delete_receiver, sender=model)

    @classmethod
    def get_registered_models(cls):
        """
        Resolves the class model attribute if it's a string and returns it.
        """
        # If model is None directly on the class, assume it's abstract.
        if cls.model is None:
            if "model" in cls.__dict__:
                return []
            else:
                raise ValueError("You must set the model attribute on Binding %r!" % cls)
        # If fields is not defined, raise an error
        if cls.fields is None:
            raise ValueError("You must set the fields attribute on Binding %r!" % cls)
        # Optionally resolve model strings
        if isinstance(cls.model, six.string_types):
            cls.model = apps.get_model(cls.model)
        cls.model_label = "%s.%s" % (
            cls.model._meta.app_label.lower(),
            cls.model._meta.object_name.lower(),
        )
        return [cls.model]

    # Outbound binding

    @classmethod
    def encode(cls, stream, payload):
        """
        Encodes stream + payload for outbound sending.
        """
        raise NotImplementedError()

    @classmethod
    def pre_save_receiver(cls, instance, **kwargs):
        cls.pre_change_receiver(instance, CREATE if instance.pk is None else UPDATE)

    @classmethod
    def post_save_receiver(cls, instance, created, **kwargs):
        cls.post_change_receiver(instance, CREATE if created else UPDATE)

    @classmethod
    def pre_delete_receiver(cls, instance, **kwargs):
        cls.pre_change_receiver(instance, DELETE)

    @classmethod
    def post_delete_receiver(cls, instance, **kwargs):
        cls.post_change_receiver(instance, DELETE)

    @classmethod
    def pre_change_receiver(cls, instance, action):
        """
        Entry point for triggering the binding from save signals.
        """
        if action == CREATE:
            group_names = set()
        else:
            group_names = set(cls.group_names(instance))

        if not hasattr(instance, '_binding_group_names'):
            instance._binding_group_names = {}
        instance._binding_group_names[cls] = group_names

    @classmethod
    def post_change_receiver(cls, instance, action):
        """
        Triggers the binding to possibly send to its group.
        """
        old_group_names = instance._binding_group_names[cls]
        if action == DELETE:
            new_group_names = set()
        else:
            new_group_names = set(cls.group_names(instance))

        # if post delete, new_group_names should be []
        self = cls()
        self.instance = instance

        # Django DDP had used the ordering of DELETE, UPDATE then CREATE for good reasons.
        self.send_messages(instance, old_group_names - new_group_names, DELETE)
        self.send_messages(instance, old_group_names & new_group_names, UPDATE)
        self.send_messages(instance, new_group_names - old_group_names, CREATE)

    def send_messages(self, instance, group_names, action):
        """
        Serializes the instance and sends it to all provided group names.
        """
        if not group_names:
            return  # no need to serialize, bail.
        payload = self.serialize(instance, action)
        if payload == {}:
            return  # nothing to send, bail.

        assert self.stream is not None
        message = self.encode(self.stream, payload)
        for group_name in group_names:
            group = Group(group_name)
            group.send(message)

    def group_names(self, instance, action):
        """
        Returns the iterable of group names to send the object to based on the
        instance and action performed on it.
        """
        raise NotImplementedError()

    def serialize(self, instance, action):
        """
        Should return a serialized version of the instance to send over the
        wire (e.g. {"pk": 12, "value": 42, "string": "some string"})
        """
        raise NotImplementedError()

    # Inbound binding

    @classmethod
    def trigger_inbound(cls, message, **kwargs):
        """
        Triggers the binding to see if it will do something.
        Also acts as a consumer.
        """
        # Late import as it touches models
        from django.contrib.auth.models import AnonymousUser
        self = cls()
        self.message = message
        # Deserialize message
        self.action, self.pk, self.data = self.deserialize(self.message)
        self.user = getattr(self.message, "user", AnonymousUser())
        # Run incoming action
        self.run_action(self.action, self.pk, self.data)

    @classmethod
    def get_handler(cls):
        """
        Adds decorators to trigger_inbound.
        """
        handler = cls.trigger_inbound
        if cls.channel_session_user:
            return channel_session_user(handler)
        elif cls.channel_session:
            return channel_session(handler)
        else:
            return handler

    @classmethod
    def consumer(cls, message, **kwargs):
        handler = cls.get_handler()
        handler(message, **kwargs)

    def deserialize(self, message):
        """
        Returns action, pk, data decoded from the message. pk should be None
        if action is create; data should be None if action is delete.
        """
        raise NotImplementedError()

    def has_permission(self, user, action, pk):
        """
        Return True if the user can do action to the pk, False if not.
        User may be AnonymousUser if no auth hooked up/they're not logged in.
        Action is one of "create", "delete", "update".
        """
        raise NotImplementedError()

    def run_action(self, action, pk, data):
        """
        Performs the requested action. This version dispatches to named
        functions by default for update/create, and handles delete itself.
        """
        # Check to see if we're allowed
        if self.has_permission(self.user, action, pk):
            if action == "create":
                self.create(data)
            elif action == "update":
                self.update(pk, data)
            elif action == "delete":
                self.delete(pk)
            else:
                raise ValueError("Bad action %r" % action)

    def create(self, data):
        """
        Creates a new instance of the model with the data.
        """
        raise NotImplementedError()

    def update(self, pk, data):
        """
        Updates the model with the data.
        """
        raise NotImplementedError()

    def delete(self, pk):
        """
        Deletes the model instance.
        """
        self.model.objects.filter(pk=pk).delete()
